import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.functions import strip
from product_spider.items import RawData, ProductPackage


class InorganicSpider(BaseSpider):
    name = "inorganic"
    start_urls = ["https://www.inorganicventures.com/products", ]
    base_url = "https://www.inorganicventures.com/"
    brand = 'inorganic'

    def parse(self, response):
        cat_urls = response.xpath('//div[contains(@class, "block-category-link")]/a/@href').getall()
        for url in cat_urls:
            yield Request(url, callback=self.parse)


