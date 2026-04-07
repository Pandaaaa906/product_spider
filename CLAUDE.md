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
- **API Service**: FastAPI service for spider management via HTTP API (port 8000)
- **Log Parser**: Automated log processing service
- **Dockerized**: Full containerized deployment with volume mounting

## Important Notes

1. **NEVER Auto-Commit**: Before committing code changes, always summarize the changes and wait for explicit user approval (e.g., "ok, commit", "commit it"). Never run `git commit` without user confirmation.
2. **No Unit Tests**: Project relies on integration testing through deployment
3. **GitLab CI/CD**: Automated deployment pipeline (dev branch → dev environment, master → prod)
4. **Playwright Required**: Must install browsers via `playwright install`
5. **Chinese Dependencies**: Uses PyPI mirror (Tsinghua) for faster downloads
6. **ROBOTS.TXT**: Disabled (`ROBOTSTXT_OBEY = False`) as this is an authorized scraping system

## File Structure Highlights

- `product_spider/spiders/`: Individual spider implementations (177 files)
- `product_spider/items/`: Product data structures
- `product_spider/pipelines/redis_pipeline.py`: Redis result storage pipeline
- `product_spider/utils/spider_mixin.py`: BaseSpider with keyword search support
- `api_service/main.py`: FastAPI service for spider management
- `data/`: Storage for scraped data
- `dbs/`: Database schema and migration files
- `tests/`: Test scripts with pytest
  - `conftest.py`: Shared pytest fixtures
  - `test_keyword_search.py`: Keyword search functionality tests
  - `test_redis_connection.py`: Redis connectivity tests
  - `test_scrapyd_keyword_search.py`: Scrapyd integration tests
  - `test_allmpus_keyword.py`: Allmpus spider keyword search tests
  - `test_api_service.py`: API Service deployment tests
  - `service_manager.py`: Service management utilities for tests
  - `test_api_service_integration.py`: API Service integration tests
- `test.local.env`: Local testing environment variables
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

## Keyword Search Feature

### Overview
The keyword search feature allows spiders to be triggered via Scrapyd API or CLI with a search query, storing results in Redis for quick retrieval.

### Architecture
- **BaseSpider** (`product_spider/utils/spider_mixin.py`): Validates `task_id` when `cmd_keyword_search=True`
- **Spider Implementation**: Each spider implements `keyword_search()` method for site-specific search logic
- **Redis Pipeline** (`product_spider/pipelines/redis_pipeline.py`): Stores keyword search results with task-based organization
  - Keys: `CMD_KEYWORD_SEARCH:{task_id}:results:product`, `CMD_KEYWORD_SEARCH:{task_id}:results:package`
  - TTL configurable via `REDIS_CACHE_TTL` (default: 24 hours)
- **Test Suite** (`tests/`): Pytest-based tests with shared fixtures in `conftest.py`

### Usage

#### Via Scrapyd API
```bash
# Schedule keyword search via Scrapyd API
curl -X POST http://127.0.0.1:6800/schedule.json \
  -d project=product_spider \
  -d spider=allmpus \
  -d cmd_keyword_search=True \
  -d keyword=acetone \
  -d task_id=unique-task-id

# Check results in Redis
redis-cli -h 192.168.4.246 -p 6380 -n 2 zrange 'task:unique-task-id:results' 0 -1
```

#### Via Scrapy CLI (with env-file)
```bash
# Run keyword search with environment file
uv run --env-file ./test.local.env scrapy crawl allmpus \
  -a cmd_keyword_search=true \
  -a keyword=acetone \
  -a task_id=unique-task-id
```

### Testing

#### Automated Testing

#### Pytest (Recommended)

Tests are now organized using pytest with shared fixtures in `conftest.py`:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_redis_connection.py -v
pytest tests/test_keyword_search.py -v
pytest tests/test_scrapyd_keyword_search.py -v
pytest tests/test_api_service.py -v    # API Service tests with auto-start

# Run by markers
pytest tests/ -m redis -v              # Only Redis tests
pytest tests/ -m spider -v             # Only spider tests
pytest tests/ -m api_service -v        # Only API Service tests
pytest tests/ -m "not slow" -v         # Exclude slow tests
pytest tests/ -m integration -v        # Only integration tests

# Run with custom parameters
pytest tests/test_keyword_search.py -v --spider=allmpus --keyword=ethanol

# Skip auto-starting services (if already running)
pytest tests/test_api_service.py -v --skip-service-start

# Direct execution (backward compatible)
python tests/test_redis_connection.py
python tests/test_keyword_search.py allmpus biosynth
python tests/test_scrapyd_keyword_search.py --spider=allmpus
python tests/test_api_service.py
```

#### Service Manager

The `tests/service_manager.py` module provides utilities for managing test services:

```python
from tests.service_manager import ScrapydServiceManager, ApiServiceManager, ServiceManager

# Manage single service
with ScrapydServiceManager() as scrapyd:
    if scrapyd.is_running:
        # Run tests
        pass

with ApiServiceManager() as api:
    if api.is_running:
        # Run tests
        pass

# Manage multiple services
with ServiceManager() as services:
    if services.all_running:
        # Both api_service and scrapyd are ready
        pass
```

### Configuration
- `REDIS_URL`: Redis connection string (e.g., `redis://192.168.4.246:6380/2`)
- `REDIS_CACHE_TTL`: Result expiration time in seconds (default: 86400 = 24 hours)
- `KEYWORD_SEARCH_SPIDERS`: Environment variable to specify spiders for testing (comma-separated)

### Environment Variable Passing

When running spiders via `uv run`, use `--env-file` to pass environment variables:

```bash
# Recommended approach - use env file
uv run --env-file ./test.local.env scrapy crawl spider_name

# The env file should contain:
# REDIS_URL=redis://192.168.4.246:6380/2
# DATABASE_NAME=dev
# etc.
```

**Note**: Direct environment variable passing to subprocess may not work reliably with `uv run` due to process isolation. Always use `--env-file` for consistent behavior.

### Test Environment Setup

Create `test.local.env` for local testing:

```bash
# Redis Configuration
REDIS_URL=redis://192.168.4.246:6380/2
REDIS_HOST=192.168.4.246
REDIS_PORT=6380
REDIS_DB=2

# Database Configuration
DATABASE_ENGINE=postgresql
DATABASE_NAME=dev
DATABASE_USER=postgres
DATABASE_PWD=your_password
DATABASE_HOST=192.168.5.247
DATABASE_PORT=5432

# Proxy Pool (optional)
PROXY_POOL_URL=http://192.168.5.246:5555/random

# Playwright
PLAYWRIGHT_SKIP_BROWSER_GC=1
```

### Known Issues & Lessons Learned

1. **Spider XPath Consistency**: When implementing `keyword_search`, ensure the search results page structure matches existing parsers. The `parse_prd_list` method was reused for both category browsing and search results, requiring careful XPath design.

2. **CAT No Extraction**: Products may have CAT No in list view but not in detail view. Store CAT No in `meta` during list parsing and fallback to it in `parse_detail`.

3. **Windows Event Loop**: `async_runner.py` must set `asyncio.WindowsSelectorEventLoopPolicy()` on Windows before installing the reactor to avoid `ProtractorEventLoop` incompatibility.

4. **Scrapyd Deploy URL**: `scrapy.cfg` deploy URL should use `0.0.0.0:6800` for deployment, but tests should connect via `127.0.0.1:6800`.

5. **Log Cleanup**: Always clear logs before testing to avoid confusion from previous runs. Use `rm -rf logs/product_spider/**/*.log` to clean up.

6. **Redis Pipeline TTL**: Cache expiration should be configurable via environment variable. Default changed from 30 days to 24 hours to prevent storage bloat.

7. **Dynamic Spider Discovery**: Test scripts automatically detect spiders that implement `keyword_search` method, eliminating the need to manually maintain spider lists.

## API Service

### Overview
FastAPI-based service providing HTTP API for spider management. Runs alongside Scrapyd to enable external systems to schedule and monitor spider tasks.

### Architecture
- **AsyncScrapydClient** (`api_service/async_scrapyd_client.py`): Async HTTP client for Scrapyd API
- **ScrapydClient** (`api_service/scrapyd_client.py`): Extends AsyncScrapydClient with async Redis operations
- **Main API** (`api_service/main.py`): FastAPI application with endpoints

### Endpoints
- `POST /api/spiders/run` - Start a spider task (async, returns task_id immediately)
- `POST /api/spiders/run/sync` - Start a spider task (sync, waits for results)
- `GET /api/spiders/status/{task_id}` - Get task status from Redis
- `GET /api/spiders/result/{task_id}` - Get task results from Redis (structured Product format)
- `GET /api/spiders/list` - List available spiders
- `GET /api/scrapyd/status` - Get Scrapyd daemon status
- `POST /api/spiders/cancel/{job_id}` - Cancel a running job

### Response Format
Task results are returned as structured `Product` objects with nested `packages`:
```json
{
  "task_id": "...",
  "results": [
    {
      "brand": "...",
      "cat_no": "...",
      "en_name": "...",
      "cas": "...",
      "packages": [
        {
          "package": "...",
          "price": "...",
          "currency": "..."
        }
      ]
    }
  ],
  "total": 10,
  "message": "Results retrieved successfully"
}
```

### Configuration
Environment variables:
- `SCRAPYD_URLS`: Comma-separated Scrapyd URLs (default: `http://localhost:6800`)
- `REDIS_URL`: Redis connection URL for results (e.g., `redis://localhost:6379/0`)
- `SCRAPYD_PROJECT`: Default project name (default: `default`)

### Testing
```bash
# Run all API Service tests (auto-starts scrapyd and api_service)
pytest tests/test_api_service.py -v

# Run with services already running
pytest tests/test_api_service.py -v --skip-service-start

# Deploy via docker-compose
docker-compose up -d api_service scrapyd redis
```

### Key Implementation Details
- Uses `redis.asyncio.Redis` for non-blocking Redis operations
- Results are assembled by matching `Product.brand == ProductPackage.brand` AND `Product.cat_no == ProductPackage.cat_no`
- Task completion is determined by checking Redis status only (not Scrapyd job status)
- No in-memory task cache; all state is stored in Redis