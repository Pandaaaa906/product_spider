# TODO Get Blocked
import re

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


playwright_page_goto_kwargs = {
    'wait_until': 'domcontentloaded',
}


class ChemServicePrdSpider(BaseSpider):
    name = "chemservice"
    base_url = "https://www.chemservice.com/"
    start_urls = ["https://www.chemservice.com/store.html?limit=100", ]

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS_PER_IP': 2,
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 60000,
        'PLAYWRIGHT_CONTEXT_ARGS': {
            'java_script_enabled': True
        },
    }

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url=url, callback=self.parse, headers=self.headers,
                meta={"playwright": True, "playwright_page_goto_kwargs": playwright_page_goto_kwargs}
            )

    def parse(self, response, **kwargs):
        urls = response.xpath('//h2[@class="product-name"]/a/@href').getall()
        # self.headers['referer'] = response.url
        for url in urls:
            yield Request(
                url, callback=self.prd_parse, headers=self.headers,
                meta={"playwright": True, "playwright_page_goto_kwargs": playwright_page_goto_kwargs}
            )

        next_page = response.xpath('//li[@class="current"]/following-sibling::li/a/@href').get()
        if next_page:
            yield Request(
                next_page, callback=self.parse, headers=self.headers,
                meta={"playwright": True, "playwright_page_goto_kwargs": playwright_page_goto_kwargs}
            )

    def prd_parse(self, response):
        tmp_x = '//table[@id="product-attribute-specs-table"]//th[contains(text(),{!r})]/following-sibling::td/text()'
        raw_cat_no = response.xpath('//div[@itemprop="name"]/div[@class="product-sku"]/span/text()').get()
        cat_no = (m := re.match(r'(?P<cat_no>.+)(?:-[^-]+$)', raw_cat_no)) and m['cat_no']
        tmp_d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": response.xpath(tmp_x.format("Classification")).get(),
            "en_name": response.xpath('//div[@itemprop="name"]/h1/text()').get(),
            "cas": response.xpath('//div[@itemprop="name"]/div[@class="product-cas"]/span/text()').get(),
            "mf": response.xpath(tmp_x.format('Molecular Formula')).get(),
            "mw": response.xpath(tmp_x.format('Molecular Weight')).get(),
            "info1": response.xpath(tmp_x.format("Alternate")).get(),
            "img_url": response.xpath(
                '//img[contains(@id, "product-collection-image") and not(contains(@src, "placeholder.png"))]/@src'
            ).get(),
            "prd_url": response.url
        }
        yield RawData(**tmp_d)
        raw_price = response.xpath('//div[@class="add-to-cart-wrapper"]//span[@class="price"]/text()').get('')
        price = (m := re.match(r'', raw_price)) and m.group()
        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "package": response.xpath('//span[@class="size"]/text()').get('').lower(),
            "cost": price,
            "currency": 'USD',
            "delivery_time": response.xpath('//p[contains(@class, "availability")]/span/text()').get(),
            "stock_num": response.xpath('//p[@class="avail-count"]/span/text()').get(),
        }
        yield ProductPackage(**dd)
