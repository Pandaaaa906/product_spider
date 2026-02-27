# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a sophisticated web scraping system for chemical product data collection, featuring 177 spiders for different chemical suppliers. The project uses Scrapy framework with Playwright for stealth browsing, PostgreSQL for data storage, and containerized deployment.

## Common Development Commands

### Build and Deploy
```bash
# Production deployment
docker-compose up -d --build

# Test deployment (uses separate test environment)
docker-compose -f docker-compose-test.yaml up -d --build

# Deploy specific services
docker-compose up -d scrapyd
```

### UV Dependency Management
```bash
# Install dependencies
uv sync

# Install development dependencies
uv sync --dev

# Create and activate virtual environment
uv venv
. .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate  # Windows

# Run with uv
uv run scrapy crawl spider_name
uv run python product_spider/async_runner.py spider_name
```

### Running Spiders
```bash
# Using async_runner (recommended for production)
python product_spider/async_runner.py spider_name

# Using Scrapy CLI (for local development)
scrapy crawl spider_name

# With environment variables
DATABASE_NAME=dev scrapy crawl spider_name
```

### Development Setup
```bash
# Initialize uv project (first time)
uv init
uv sync

# Create and activate virtual environment
uv venv
. .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate  # Windows

# Install Playwright browsers
.venv/bin/playwright install chrome  # Linux/Mac
.venv\Scripts\playwright install chrome  # Windows

# Run with test environment
uv run scrapy crawl spider_name
```

## Architecture Overview

### Core Components
1. **Spiders** (`product_spider/spiders/`): 177 spider implementations, each extending `BaseSpider` or `JsonSpider`
2. **Items** (`product_spider/items/`): Data structures for scraped products
3. **Pipelines** (`product_spider/pipelines.py`): Data processing pipeline
4. **Settings** (`product_spider/settings.py`): Core configuration with PostgreSQL, Redis, proxy settings

### Data Flow
1. Spider extracts raw data from supplier websites
2. Pipeline processes data through multiple stages:
   - StripPipeline: Cleans string values
   - DropNullCatNoPipeline: Removes items without catalog numbers
   - FilterNAValue: Filters invalid CAS numbers
   - ParseCostPipeline: Parses pricing
   - ParseRawSupplierQuotationPipeline: Processes quotations
   - AutoDBPipeline: Saves to PostgreSQL

### Key Features
- **Stealth Browsing**: Uses Playwright with custom `StealthScrapyPlaywrightDownloadHandler`
- **Proxy Support**: Configurable proxy pool for rotation
- **Database**: PostgreSQL with `scrapyautodb` for automatic data insertion
- **Web Management**: ScrapydWeb UI at port 6799
- **Redis Integration**: For queuing and duplicate filtering (configurable)

### Environment Configuration
- Production: Uses `.env` with `chemhost` database
- Test: Uses `test.env` with `dev` database
- Environment variables control database connections, Redis, proxy pools, and API keys

### Deployment Architecture
- **Scrapyd**: Service for running spiders (port 6800)
- **ScrapydWeb**: Web UI for spider management (port 6799)
- **Log Parser**: Automated log processing service
- **Dockerized**: Full containerized deployment with volume mounting

## Important Notes

1. **No Unit Tests**: Project relies on integration testing through deployment
2. **GitLab CI/CD**: Automated deployment pipeline (dev branch → dev environment, master → prod)
3. **Playwright Required**: Must install browsers via `playwright install`
4. **Chinese Dependencies**: Uses PyPI mirror (Tsinghua) for faster downloads
5. **ROBOTS.TXT**: Disabled (`ROBOTSTXT_OBEY = False`) as this is an authorized scraping system

## File Structure Highlights

- `product_spider/spiders/`: Individual spider implementations (177 files)
- `product_spider/items/`: Product data structures
- `data/`: Storage for scraped data
- `dbs/`: Database schema and migration files
- `scrapy.cfg`: Scrapy deployment configuration
- `docker-compose*.yaml`: Production and test configurations
- `pyproject.toml`: Project configuration and dependencies (managed by uv)
- `uv.lock`: Dependency lock file (committed to ensure reproducible builds)
- `Makefile`: Common development tasks
- `.dockerignore`: Docker build exclusions

### UV Integration
- Project now uses `uv` for fast dependency management
- Virtual environment created at `.venv/`
- Dependencies defined in `pyproject.toml` with proper project metadata
- Git-based dependencies (ScrapyAutoDb, scrapydweb) properly configured in uv sources