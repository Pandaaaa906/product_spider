import re
from string import ascii_uppercase
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class SynzealSpider(BaseSpider):
    name = "synzeal"
    allowd_domains = ["synzeal.com"]
    base_url = "https://www.synzeal.com"
    start_urls = map(lambda x: f"https://www.synzeal.com/category/{x}", ascii_uppercase)

    def parse(self, response):
        a_nodes = response.xpath('//a[@class="clsMaincatdiv"]')
        for a in a_nodes:
            parent = a.xpath('./text()').get('').strip() or None
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url),
                          meta={'parent': parent},
                          callback=self.list_parse,
                          headers=self.headers)

    def list_parse(self, response):
        urls = response.xpath('//h4[@class="product_name"]/a/@href').extract()
        for rel_url in urls:
            yield Request(urljoin(self.base_url, rel_url),
                          callback=self.detail_parse,
                          meta=response.meta,
                          headers=self.headers)

    def detail_parse(self, response):
        en_name = response.xpath('//h1[@class="product-detail-title"]/text()').get(default="")
        en_name = re.sub(r'\r?\n', "", en_name)
        tmp = '//td[contains(text(),{!r})]/following-sibling::td/text()'
        d = {
            'brand': "SynZeal",
            'en_name': en_name.strip(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': response.xpath(tmp.format('SZ CAT No')).get(),
            'cas': response.xpath(tmp.format('CAS No')).get(default=""),
            'stock_info': response.xpath(tmp.format('Inv. Status')).get(),
            'mf': response.xpath(tmp.format('Mol.F.')).get(),
            'mw': response.xpath(tmp.format('Mol.Wt.')).get(),
            'info1': response.xpath('//b[text()="Synonym: "]/../text()').get(default="").strip(),
            'parent': response.meta.get('parent'),
            'img_url': response.xpath('//div[@class="product-details-tab"]//img/@src').get(),
        }
        yield RawData(**d)

