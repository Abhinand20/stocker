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

def parse_filing_results(results: list[list[str]]) -> list[FilingResult]:
    all_results = []
    url_pattern = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>')
    for row in results:
        match = url_pattern.search(row[3])
        if not match:
            logging.warning(f"Failed to parse filing URL from {row}")
            continue
        filing_url = match.group(1)
        filing_type = parse_filing_type(match.group(2))
        filing_format = parse_filing_format(filing_url)
        filing_result = FilingResult(
            first_name=row[0].strip(),
            last_name=row[1].strip(),
            office_name=row[2].strip(),
            filing_date=datetime.strptime(row[4], "%m/%d/%Y"),
            filing_type=filing_type,
            filing_url=constants.BASE_URL + filing_url,
            filing_format=filing_format,
        )
        all_results.append(filing_result)
    return all_results

class Filing(ABC):
    @abstractmethod
    def get_url(self) -> str:
        pass

    @abstractmethod
    def get_content(self, session: requests.Session) -> bytes:
        pass

    @classmethod
    def from_result(cls, filing_result: FilingResult) -> 'Filing':
        """
        Factory method to create FilingHTML or FilingPDF based on the filing_url extension. The URL contains "page" for paper filings and "ptr" for e-filings in HTML format.
        
        Args:
            filing_result: The FilingResult containing the filing URL
            
        Returns:
            FilingHTML or FilingPDF based on filing_url.
        """
        url = filing_result.filing_url.lower()
        if filing_result.filing_format == FilingFormat.HTML:
            return FilingHTML(filing_result)
        elif filing_result.filing_format == FilingFormat.PDF:
            return FilingPDF(filing_result)
        else:
            # Default to HTML for unknown extensions
            logging.warning(f"Unknown file extension in URL: {filing_result.filing_url}, defaulting to HTML")
            return FilingHTML(filing_result)

class FilingScraper(ABC):
    @abstractmethod
    def scrape_filing_urls(self, filters: Optional[FilingSearchFilters] = None) -> List[FilingResult]:
        pass

    @abstractmethod
    def download_filing(self, filing: FilingResult) -> bytes:
        pass

# These types of filings are simpler to parse because they are already in a structured format.
class FilingHTML(Filing):
    def __init__(self, filing_result: FilingResult):
        self.filing_result = filing_result

    def get_url(self) -> str:
        return self.filing_result.filing_url

    def get_content(self, session: requests.Session) -> bytes:
        # Fetch the context from the URL, download the HTML.
        response = session.get(self.get_url())
        print("Fetching filing URL: ", self.get_url())
        if response.status_code != 200:
            raise Exception(f"Failed to fetch filing: {response.status_code}")
        soup = BeautifulSoup(response.content, "html.parser")
        print(response.text.strip())
        print(soup.prettify())
        return response.content

# These types of filings may need to be parsed using OCR.
class FilingPDF(Filing):
    def __init__(self, filing_result: FilingResult):
        self.filing_result = filing_result

    def get_url(self) -> str:
        return self.filing_result.filing_url

    def get_content(self, session: requests.Session) -> bytes:
        return b""


class SenateFilingScraper(FilingScraper):
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
            self.search_params["start"] += 25
            break
        logging.info(f"Fetched {len(all_data)} filings successfully!")
        return all_data

    def download_filing(self, filing: FilingResult) -> bytes:
        filing = Filing.from_result(filing)
        logging.info(f"Downloading filing: {filing.get_url()}")
        c = filing.get_content(self.session)
        return c


def main():
    logging.basicConfig(level=logging.INFO)
    session = requests.Session()
    scraper = SenateFilingScraper(session)
    filters = FilingSearchFilters(filing_types=[constants.FilingType.PERIODIC_TRANSACTION_REPORT], start_date=datetime(2025, 10, 1), end_date=datetime(2025, 10, 31))
    try:
        filings = scraper.scrape_filing_urls(filters)
        for filing in filings:
            print(filing)
            if filing.filing_format == FilingFormat.HTML:
                c = scraper.download_filing(filing)
                print(c)
        
        # print(f)
    except Exception as e:
        logging.error(f"Failed to scrape filings: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()