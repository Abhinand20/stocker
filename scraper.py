"""Senate financial filing scraper.

A two-step scraper that:
1. Fetches filing URLs from the Senate EFD system
2. Downloads and processes the filing content
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

import constants

class FilingFormat(Enum):
    HTML = "html"
    PDF = "pdf"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class FilingResult:
    first_name: str
    last_name: str
    office_name: str
    filing_date: datetime
    filing_type: constants.FilingType
    filing_url: str
    filing_format: FilingFormat

@dataclass
class FilingSearchFilters:
    filing_types: Optional[list[constants.FilingType]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    def to_search_params(self) -> dict:
        search_params = {}
        if self.filing_types:
            report_types = [str(constants.REPORT_TYPE_TO_ID[filing_type]) for filing_type in self.filing_types if filing_type != constants.FilingType.UNKNOWN]
            if report_types:
                search_params['report_types'] = f"[{', '.join(report_types)}]"
        if self.start_date:
            search_params['submitted_start_date'] = self.start_date.strftime("%m/%d/%Y %H:%M:%S")
        if self.end_date:
            search_params['submitted_end_date'] = self.end_date.strftime("%m/%d/%Y %H:%M:%S")
        return search_params

def parse_filing_format(filing_url: str) -> FilingFormat:
    if "ptr" in filing_url.lower() or "annual" in filing_url.lower():
        return FilingFormat.HTML
    elif "paper" in filing_url.lower():
        return FilingFormat.PDF
    else:
        logging.warning(f"Unknown filing format: {filing_url}")
        return FilingFormat.UNKNOWN

def parse_filing_type(type_str: str) -> constants.FilingType:
    if "annual report" in type_str.lower():
        return constants.FilingType.ANNUAL_REPORT
    elif "periodic transaction report" in type_str.lower():
        return constants.FilingType.PERIODIC_TRANSACTION_REPORT
    else:
        logging.warning(f"Unknown filing type: {type_str}")
        return constants.FilingType.UNKNOWN

# Compiled regex pattern for parsing filing URLs
FILING_URL_PATTERN = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>')

# Constants for row indices
FIRST_NAME_IDX = 0
LAST_NAME_IDX = 1
OFFICE_NAME_IDX = 2
FILING_LINK_IDX = 3
FILING_DATE_IDX = 4


def parse_filing_results(results: List[List[str]]) -> List[FilingResult]:
    """Parse raw filing results from Senate API into FilingResult objects.
    
    Args:
        results: List of rows from the Senate filing search API
        
    Returns:
        List of parsed FilingResult objects
    """
    parsed_filings = []
    
    for row in results:
        if len(row) <= FILING_DATE_IDX:
            logging.warning(f"Skipping malformed row: {row}")
            continue
            
        match = FILING_URL_PATTERN.search(row[FILING_LINK_IDX])
        if not match:
            logging.warning(f"Failed to parse filing URL from row: {row}")
            continue
            
        filing_url = match.group(1)
        filing_type_text = match.group(2)
        
        try:
            filing_date = datetime.strptime(row[FILING_DATE_IDX], "%m/%d/%Y")
        except ValueError as e:
            logging.warning(f"Failed to parse filing date '{row[FILING_DATE_IDX]}': {e}")
            continue
            
        filing_result = FilingResult(
            first_name=row[FIRST_NAME_IDX].strip(),
            last_name=row[LAST_NAME_IDX].strip(),
            office_name=row[OFFICE_NAME_IDX].strip(),
            filing_date=filing_date,
            filing_type=parse_filing_type(filing_type_text),
            filing_url=constants.BASE_URL + filing_url,
            filing_format=parse_filing_format(filing_url),
        )
        parsed_filings.append(filing_result)
        
    return parsed_filings

class Filing(ABC):
    @abstractmethod
    def get_url(self) -> str:
        pass

    @abstractmethod
    def get_content(self, session: requests.Session) -> bytes:
        pass

    @classmethod
    def from_result(cls, filing_result: FilingResult) -> 'Filing':
        """Create appropriate Filing subclass based on filing format.
        
        Args:
            filing_result: The FilingResult to wrap
            
        Returns:
            FilingHTML or FilingPDF instance based on filing format
        """
        if filing_result.filing_format == FilingFormat.HTML:
            return FilingHTML(filing_result)
        elif filing_result.filing_format == FilingFormat.PDF:
            return FilingPDF(filing_result)
        else:
            logging.warning(f"Unknown filing format for URL: {filing_result.filing_url}, defaulting to HTML")
            return FilingHTML(filing_result)

class FilingScraper(ABC):
    @abstractmethod
    def scrape_filing_urls(self, filters: Optional[FilingSearchFilters] = None) -> List[FilingResult]:
        pass

    @abstractmethod
    def download_filing(self, filing: FilingResult) -> bytes:
        pass

class FilingHTML(Filing):
    """HTML filing handler for structured electronic filings."""
    
    def __init__(self, filing_result: FilingResult):
        self.filing_result = filing_result

    def get_url(self) -> str:
        return self.filing_result.filing_url

    def get_content(self, session: requests.Session) -> bytes:
        """Download HTML filing content.
        
        Args:
            session: Requests session with authentication
            
        Returns:
            Raw HTML content as bytes
            
        Raises:
            requests.RequestException: If download fails
        """
        logging.info(f"Downloading HTML filing: {self.get_url()}")
        
        try:
            response = session.get(self.get_url())
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            logging.error(f"Failed to download filing from {self.get_url()}: {e}")
            raise

# These types of filings may need to be parsed using OCR.
class FilingPDF(Filing):
    def __init__(self, filing_result: FilingResult):
        self.filing_result = filing_result

    def get_url(self) -> str:
        return self.filing_result.filing_url

    def get_content(self, session: requests.Session) -> bytes:
        return b""


class SenateFilingScraper(FilingScraper):
    """Scraper for Senate Electronic Financial Disclosure system."""
    
    PAGINATION_SIZE = 25
    
    def __init__(self, session: requests.Session):
        self.session = session
        self.root_url = constants.ROOT_URL
        self.search_url = constants.SEARCH_URL
        self.search_params = constants.SENATE_FILING_SEARCH_PARAMS.copy()
        self.search_headers = constants.SENATE_FILING_SEARCH_REQUEST_HEADERS.copy()
        self.csrf_token = None

    def scrape_filing_urls(self, filters: Optional[FilingSearchFilters] = None) -> List[FilingResult]:
        # Fetch the ack token from the root page.
        self.session.headers.update(self.search_headers)
        if filters:
            self.search_params.update(filters.to_search_params())
        response = self.session.get(self.root_url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch root page: {response.status_code}")
        soup = BeautifulSoup(response.content, "html.parser")
        self.csrf_token = soup.select_one('[name="csrfmiddlewaretoken"]')["value"]
        soup = BeautifulSoup(
        self.session.post(
            self.root_url,
            data={"prohibition_agreement": "1", "csrfmiddlewaretoken": self.csrf_token},
            ).content,
            "html.parser",
        )
        self.csrf_token = soup.select_one('[name="csrfmiddlewaretoken"]')["value"]
        self.session.headers.update({"X-CSRFToken": self.csrf_token})
        logging.info(f"Fetched Root page and CSRF token successfully!")
        all_data = []
        while True:
            response = self.session.post(self.search_url, data=self.search_params)
            if response.status_code != 200:
                raise Exception(f"Failed to search filings: {response.status_code}")
            d = response.json()
            if not d["data"]:
                break
            all_data.extend(parse_filing_results(d["data"]))
            self.search_params["draw"] += 1
            self.search_params["start"] += self.PAGINATION_SIZE
        logging.info(f"Fetched {len(all_data)} filings successfully!")
        return all_data

    def download_filing(self, filing_result: FilingResult) -> bytes:
        """Download content for a specific filing.
        
        Args:
            filing_result: The filing to download
            
        Returns:
            Raw filing content as bytes
            
        Raises:
            requests.RequestException: If download fails
        """
        filing = Filing.from_result(filing_result)
        return filing.get_content(self.session)


def main():
    """Example usage of the Senate filing scraper."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    session = requests.Session()
    scraper = SenateFilingScraper(session)
    
    # Search for periodic transaction reports from October 2025
    filters = FilingSearchFilters(
        filing_types=[constants.FilingType.PERIODIC_TRANSACTION_REPORT],
        start_date=datetime(2025, 10, 1),
        end_date=datetime(2025, 10, 31)
    )
    
    try:
        filings = scraper.scrape_filing_urls(filters)
        logging.info(f"Found {len(filings)} filings")
        
        for filing in filings:
            print(f"Filing: {filing.first_name} {filing.last_name} - {filing.filing_date}")
            
            # Download HTML filings as examples
            if filing.filing_format == FilingFormat.HTML:
                try:
                    content = scraper.download_filing(filing)
                    print(f"Downloaded {len(content)} bytes")
                except Exception as e:
                    logging.error(f"Failed to download filing: {e}")
                    
    except Exception as e:
        logging.error(f"Scraping failed: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()