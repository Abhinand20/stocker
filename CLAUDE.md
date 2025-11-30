# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based financial filing scraper that extracts Senate financial disclosure reports from the official Electronic Financial Disclosure (EFD) system at `efdsearch.senate.gov`. The scraper focuses on periodic transaction reports and annual reports from senators.

## Architecture

The project consists of three main modules:

- **`constants.py`**: Configuration constants including filing type enums, HTTP headers, search parameters, and field mappings for the Senate filing search API
- **`scraper.py`**: Core scraping logic with abstract base classes for filing scrapers and concrete implementation for Senate filings
- **`parser.py`**: Empty placeholder for future filing parsing functionality

### Key Components

- `FilingResult`: Dataclass representing a parsed filing with senator information, dates, and URLs
- `FilingSearchFilters`: Configurable filters for date ranges and filing types
- `SenateFilingScraper`: Main scraper that handles CSRF tokens, pagination, and API communication
- `FilingHTML`/`FilingPDF`: Abstract filing types for different document formats

## Running the Scraper

**Execute the main scraper:**
```bash
python3 scraper.py
```

The default configuration scrapes periodic transaction reports from October 2025. Modify the `main()` function in `scraper.py` to adjust date ranges or filing types.

**Dependencies:**
The project uses standard Python libraries: `requests`, `beautifulsoup4`, `datetime`, `logging`, `re`, `dataclasses`, `typing`, `abc`, `enum`

## Development Notes

- No formal testing framework is configured
- No linting or code formatting tools are set up
- The scraper implements rate limiting through single-threaded execution
- CSRF token handling is implemented for the Senate EFD system
- The `parser.py` module is currently empty and intended for future filing content extraction