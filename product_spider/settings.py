# -*- coding: utf-8 -*-

# Scrapy settings for product_spider project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
from os import getenv, name

LOG_LEVEL = 'INFO'
if not getenv('PYTHONUNBUFFERED'):
    LOG_FILE = 'scrapy.log'
BOT_NAME = 'product_spider'


if name != 'nt':
    TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
    DOWNLOAD_HANDLERS = {
        "http": "product_spider.utils.handler.StealthScrapyPlaywrightDownloadHandler",
        "https": "product_spider.utils.handler.StealthScrapyPlaywrightDownloadHandler",
    }


SPIDER_MODULES = ['product_spider.spiders']
NEWSPIDER_MODULE = 'product_spider.spiders'

DATABASE_ENGINE = getenv('DATABASE_ENGINE', 'postgresql')
DATABASE_NAME = getenv('DATABASE_NAME', 'chemhost')
DATABASE_USER = getenv('DATABASE_USER', 'postgres')
DATABASE_PWD = getenv('DATABASE_PWD', 'catochem')
DATABASE_HOST = getenv('DATABASE_HOST', '192.168.5.249')
DATABASE_PORT = int(getenv('DATABASE_PORT', '5432'))

DATABASE = {"engine": DATABASE_ENGINE,
            "params": {
                "database": DATABASE_NAME,
                "user": DATABASE_USER,
                "password": DATABASE_PWD,
                "host": DATABASE_HOST,
                "port": DATABASE_PORT,
                "application_name": BOT_NAME,
            }
            }

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = 'product_spider (+http://www.yourdomain.com)'
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
             "AppleWebKit/537.36 (KHTML, like Gecko) " \
             "Chrome/88.0.4324.146 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 16

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'product_spider.middlewares.JkSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    'product_spider.middlewares.MyCustomDownloaderMiddleware': 543,
# }

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'product_spider.pipelines.StripPipeline': 50,
    'product_spider.pipelines.DropNullCatNoPipeline': 100,
    'product_spider.pipelines.FilterNAValue': 200,
    'product_spider.pipelines.ParseCostPipeline': 245,
    'scrapyautodb.pipelines.AutoDBPipeline': 300,
}


# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
