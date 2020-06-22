from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class SteraloidsSpider(BaseSpider):
    name = "steraloids"
    base_url = "https://www.steraloids.com/"
    start_urls = ["https://www.steraloids.com/catalogue", ]

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="sqs-block-button-container--center"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_based_list)

    def parse_based_list(self, response):
        rel_urls = response.xpath('//div[@class="sqs-block-button-container--center"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_prd_list)

    def parse_prd_list(self, response):
        nodes = response.xpath('//div[@id="productList"]/a')
        for node in nodes:
            rel_url = node.xpath('./@href').get()
            img_url = node.xpath('.//img/@data-src').get()
            yield Request(
                urljoin(self.base_url, rel_url),
                callback=self.parse_detail,
                meta={'img_url': img_url}
            )

    def parse_detail(self, response):
        tmp = '//strong[contains(text(), {!r})]/../text()'
        cas = response.xpath(tmp.format("CAS")).get('')
        cas = cas if cas!='No' else None
        d = {
            'brand': 'Steraloids',
            'parent': None,
            'cat_no': response.xpath(tmp.format("Catalogue ID")).get(),
            'en_name': response.xpath('//h1[@class="product-title"]/text()').get(),
            'cas': cas,
            'mf': response.xpath(tmp.format("Formula")).get('').replace(' ', '') or None,
            'mw': response.xpath(tmp.format("Molecular Weight")).get(),
            'stock_info': response.xpath('//meta[@property="product:availability"]/@content').get(),
            'img_url': response.meta.get('img_url'),
            'info1': response.xpath('//h1[@class="product-title"]/text()').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
