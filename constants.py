from enum import Enum

BASE_URL = "https://efdsearch.senate.gov"
ROOT_URL = "https://efdsearch.senate.gov/search/home/"
SEARCH_URL = "https://efdsearch.senate.gov/search/report/data/"


class FilingType(Enum):
    UNKNOWN = "unknown"
    ANNUAL_REPORT = "annual_report"
    PERIODIC_TRANSACTION_REPORT = "periodic_transaction_report"

SENATE_FILING_SEARCH_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Referer": "https://efdsearch.senate.gov/search/home/",
    "Origin": "https://efdsearch.senate.gov",
}

REPORT_TYPE_TO_ID = {
    FilingType.ANNUAL_REPORT: 7,
    FilingType.PERIODIC_TRANSACTION_REPORT: 11,
}

SENATE_FILING_SEARCH_PARAMS = {
    "draw": 1,
    "columns[0][data]": "0",
    "columns[0][name]": "",
    "columns[0][searchable]": "true",
    "columns[0][orderable]": "true",
    "columns[0][search][value]": "",
    "columns[0][search][regex]": "false",
    "columns[1][data]": "1",
    "columns[1][name]": "",
    "columns[1][searchable]": "true",
    "columns[1][orderable]": "true",
    "columns[1][search][value]": "",
    "columns[1][search][regex]": "false",
    "columns[2][data]": "2",
    "columns[2][name]": "",
    "columns[2][searchable]": "true",
    "columns[2][orderable]": "true",
    "columns[2][search][value]": "",
    "columns[2][search][regex]": "false",
    "columns[3][data]": "3",
    "columns[3][name]": "",
    "columns[3][searchable]": "true",
    "columns[3][orderable]": "true",
    "columns[3][search][value]": "",
    "columns[3][search][regex]": "false",
    "columns[4][data]": "4",
    "columns[4][name]": "",
    "columns[4][searchable]": "true",
    "columns[4][orderable]": "true",
    "columns[4][search][value]": "",
    "columns[4][search][regex]": "false",
    "order[0][column]": "1",
    "order[0][dir]": "asc",
    "order[1][column]": "0",
    "order[1][dir]": "asc",
    "start": 0,
    "length": "25",
    "search[value]": "",
    "search[regex]": "false",
    "report_types": f"[{', '.join([str(REPORT_TYPE_TO_ID[filing_type]) for filing_type in FilingType if filing_type != FilingType.UNKNOWN])}]",
    "filer_types": "[1]",
    "submitted_start_date": "01/01/2012 00:00:00",
    "submitted_end_date": "12/31/2023 23:59:59",
    "candidate_state": "",
    "senator_state": "",
    "office_id": "",
    "first_name": "",
    "last_name": "",
}