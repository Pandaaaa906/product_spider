from string import ascii_uppercase
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class VeeprhoSpider(BaseSpider):
    name = "veeprho"
    base_url = "https://www.eshop-veeprho.com/"
    start_urls = (f"https://www.eshop-veeprho.com/en/products?char={char}" for char in ascii_uppercase)

    def parse(self, response):
        nodes = response.xpath('//div[@class="category-container"]')
        for node in nodes:
            rel_url = node.xpath('./../@href').get()
            parent = first(node.xpath('.//p/text()').get('').split(' '), None)
            yield Request(urljoin(self.base_url, rel_url), self.list_parse, meta={'parent': parent})

    def list_parse(self, response):
        rel_urls = response.xpath('//div[@class="text"]/a/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse, meta=response.meta)

    def detail_parse(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td/text()'
        tmp2 = '//strong[text()={!r}]/following-sibling::text()'
        rel_img = response.xpath('//div[@class="image"]/img/@data-src').get()
        img_url = urljoin(self.base_url, rel_img) if rel_img else None
        d = {
            "brand": "Veeprho",
            "parent": response.meta.get('parent'),
            "cat_no": response.xpath(tmp2.format("Catalogue No.:")).get('').strip() or None,
            "en_name": response.xpath('//div[@class="container"]/h1/text()').get(),
            "img_url": img_url,
            "cas": response.xpath(tmp2.format("CAS No.:")).get('').strip() or None,
            "prd_url": response.url,
            'mf': response.xpath(tmp.format('Molecular Formula')).get(),
            'mw': response.xpath(tmp.format('Molecular Weight')).get(),
            'stock_info': response.xpath(tmp.format('Status')).get(),
            'info1': response.xpath(tmp.format('IUPAC Name')).get(),
        }
        yield RawData(**d)
