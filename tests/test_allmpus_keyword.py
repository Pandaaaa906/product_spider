#!/usr/bin/env python3
"""
Allmpus spider keyword search tests.

This module tests the AllmpusSpider keyword search functionality
using Scrapy's CrawlerProcess for direct testing.

Run with:
    pytest tests/test_allmpus_keyword.py -v
    python tests/test_allmpus_keyword.py

Note: These tests run actual spiders and may take some time.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if TYPE_CHECKING:
    from scrapy.crawler import CrawlerProcess
    from scrapy.settings import Settings


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def allmpus_spider_class():
    """Import and return the AllmpusSpider class.

    Returns:
        AllmpusSpider class
    """
    from product_spider.spiders.allmpus_spider import AllmpusSpider
    return AllmpusSpider


@pytest.fixture(scope="function")
def crawler_settings():
    """Create Scrapy settings for testing.

    Returns:
        Scrapy Settings instance configured for testing
    """
    from scrapy.utils.project import get_project_settings

    settings = get_project_settings()
    settings.set(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0.36 "
        "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.0.36"
    )
    settings.set("LOG_LEVEL", "INFO")
    settings.set("ITEM_PIPELINES", {
        "product_spider.pipelines.RawDataPipeline": 300,
    })

    return settings


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.spider
@pytest.mark.slow
@pytest.mark.integration
class TestAllmpusKeywordSearch:
    """Tests for AllmpusSpider keyword search functionality."""

    def test_spider_class_import(self, allmpus_spider_class) -> None:
        """Test that AllmpusSpider class can be imported.

        Verifies the spider module is accessible and the class exists.
        """
        assert allmpus_spider_class is not None
        assert hasattr(allmpus_spider_class, "name")
        assert hasattr(allmpus_spider_class, "keyword_search")

    def test_spider_instance_creation(
        self,
        allmpus_spider_class,
    ) -> None:
        """Test spider instance creation with keyword search parameters.

        Verifies that a spider instance can be created with the required
        keyword search arguments.
        """
        spider = allmpus_spider_class(
            cmd_keyword_search=True,
            keyword="acetone",
            task_id="test-task-123"
        )

        assert spider.cmd_keyword_search is True
        assert spider.keyword == "acetone"
        assert spider.task_id == "test-task-123"

    def test_spider_normal_mode(self, allmpus_spider_class) -> None:
        """Test spider instance creation in normal mode.

        Verifies that a spider instance can be created for normal crawling
        (without keyword search).
        """
        spider = allmpus_spider_class(cmd_keyword_search=False)

        assert spider.cmd_keyword_search is False

    def test_spider_has_required_attributes(self, allmpus_spider_class) -> None:
        """Test that spider has all required attributes.

        Verifies the spider class has the necessary attributes for
        keyword search functionality.
        """
        required_attrs = [
            "name",
            "base_url",
            "start_urls",
            "keyword_search",
            "parse",
            "parse_prd_list",
            "parse_detail",
        ]

        for attr in required_attrs:
            assert hasattr(allmpus_spider_class, attr), (
                f"Missing required attribute: {attr}"
            )

    @pytest.mark.skip(reason="Runs actual spider - enable for manual testing")
    def test_keyword_search_execution(
        self,
        allmpus_spider_class,
        crawler_settings: "Settings",
    ) -> None:
        """Test actual keyword search execution.

        This test runs the actual spider and should be enabled manually
        when you want to test the full execution.

        Args:
            allmpus_spider_class: AllmpusSpider class fixture
            crawler_settings: Scrapy settings fixture
        """
        from scrapy.crawler import CrawlerProcess

        spider = allmpus_spider_class(
            cmd_keyword_search=True,
            keyword="acetone",
            task_id="test-task-execution"
        )

        process = CrawlerProcess(crawler_settings)
        process.crawl(spider)
        process.start()

        print("Keyword search test completed!")

    @pytest.mark.skip(reason="Runs actual spider - enable for manual testing")
    def test_normal_crawl_execution(
        self,
        allmpus_spider_class,
        crawler_settings: "Settings",
    ) -> None:
        """Test normal crawl execution.

        This test runs the spider in normal mode and should be enabled
        manually when you want to test the full execution.

        Args:
            allmpus_spider_class: AllmpusSpider class fixture
            crawler_settings: Scrapy settings fixture
        """
        from scrapy.crawler import CrawlerProcess

        spider = allmpus_spider_class(cmd_keyword_search=False)

        process = CrawlerProcess(crawler_settings)
        process.crawl(spider)
        process.start()

        print("Normal crawl test completed!")


# =============================================================================
# Legacy Functions (Backward Compatibility)
# =============================================================================

def test_keyword_search() -> None:
    """Legacy function for backward compatibility.

    Runs keyword search test using CrawlerProcess.
    """
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    from product_spider.spiders.allmpus_spider import AllmpusSpider

    settings = get_project_settings()
    settings.set(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0.36 "
        "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.0.36"
    )
    settings.set("LOG_LEVEL", "INFO")
    settings.set("ITEM_PIPELINES", {
        "product_spider.pipelines.RawDataPipeline": 300,
    })

    spider = AllmpusSpider(
        cmd_keyword_search=True,
        keyword="acetone",
        task_id="test-task-123"
    )

    process = CrawlerProcess(settings)
    process.crawl(spider)
    process.start()

    print("Test completed!")


def test_normal_crawl() -> None:
    """Legacy function for backward compatibility.

    Runs normal crawl test using CrawlerProcess.
    """
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    from product_spider.spiders.allmpus_spider import AllmpusSpider

    settings = get_project_settings()
    settings.set(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0.36 "
        "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.0.36"
    )
    settings.set("LOG_LEVEL", "INFO")

    spider = AllmpusSpider(cmd_keyword_search=False)

    process = CrawlerProcess(settings)
    process.crawl(spider)
    process.start()

    print("Normal crawl test completed!")


def main() -> int:
    """Main entry point for backward compatibility.

    Returns:
        Exit code (0 for success)
    """
    print("Starting allmpus_spider tests...")

    # Test keyword search
    print("\n=== Testing Keyword Search ===")
    test_keyword_search()

    # Test normal crawl (commented out by default)
    # print("\n=== Testing Normal Crawl ===")
    # test_normal_crawl()

    return 0


# =============================================================================
# Main Entry Point (Backward Compatibility)
# =============================================================================

if __name__ == "__main__":
    """Allow running tests directly with: python test_allmpus_keyword.py"""
    if len(sys.argv) > 1 and sys.argv[1] in ("-v", "--verbose", "-h", "--help", "-k"):
        # Running with pytest arguments
        sys.exit(pytest.main([__file__] + sys.argv[1:]))
    else:
        # Running directly
        sys.exit(main())
