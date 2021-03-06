from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class WitegaSpider(BaseSpider):
    name = "witega"
    base_url = "https://auftragssynthese.com/"
    start_urls = ["https://auftragssynthese.com/en/nitrofuran-metabolites/", ]

    def parse(self, response):
        rel_urls = response.xpath('//ul[@id="menu-kategorie"]//a/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.list_parse)

    def list_parse(self, response):
        rel_urls = response.xpath('//div[@class="the_excerpt"]/a/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail)

    def parse_detail(self, response):
        tmp = '//li[contains(@class, {!r})]/span[@class="attribute-value"]/text()'
        d = {
            "brand": "witega",
            "cat_no": response.xpath('//span[@class="sku"]/text()').get(),
            "en_name": ''.join(response.xpath('//div[@class="summary entry-summary"]/h2//text()').getall()),
            "cas": response.xpath(tmp.format("cas-number")).get(),
            'info1': ''.join(response.xpath('//h5//text()').getall()) or None,
            'prd_url': response.url,
            'img_url': response.xpath('//a/img/@data-src').get(),
        }
        yield RawData(**d)

