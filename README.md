## Standardized data store for congressional financial disclosure data useful for LLM agents.

- Periodically scrapes and stores financial disclosure data.
- Handles both paper and electronic filings.
- Normaizes the data into a consistent schema used for dashboards, LLM agent MCP server and other downstream applications.

### Goals:

- Productionized workflow running periodically, in a containerized environment on the cloud, storing data in a PostgreSQL database.
- Easy discoverablity of data through API endpoints.
- LLM agent MCP server allowing NL2SQL queries to the data store.
- Dashboards and visualizations of the data.
- Trend analysis with LLM agents and live stock price tracking.

### Architecture:

#### Scraper:

- Scrapes financial disclosure data from the [Senate EFD system](https://efdsearch.senate.gov/).
- Scrapes both paper and electronic filings.
- Only on-demand processing is implemented for now without storing any raw filing data.

#### Parser:

- Parses the raw filing data into a consistent schema.
- Fetches the raw filing data on demand, and urls are provided by the scraper.
- Stores the data in a PostgreSQL database.
- Electronic filings are parsed directly into the database.
- Paper filings are run through OCR and a prompted LLM model to extract the relevant data into the database. (https://github.com/deepseek-ai/DeepSeek-OCR)

#### Data Store:

- Stores the data in a PostgreSQL database.
- Provides API endpoints to query the data.
- Provides a MCP server to allow NL2SQL queries to the data store.

#### LLM Agent MCP Server (coming soon)

#### Dashboard (coming soon)

#### Telegram Bot with LLM powered updates (coming soon)

#### Stock Price Tracking (coming soon)