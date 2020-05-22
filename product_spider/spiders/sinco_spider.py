from itertools import chain
from string import ascii_uppercase
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class SincoSpider(BaseSpider):
    name = "sinco_prds"
    start_urls = (f"http://www.sincopharmachem.com/category.asp?c={c}" for c in chain(ascii_uppercase, ('OTHER',)))
    base_url = "http://www.sincopharmachem.com"

    def parse(self, response):
        a_nodes = response.xpath('//li[@class="product-category-item"]/a')
        for a in a_nodes:
            url = urljoin(self.base_url, a.xpath('./@href').get())
            parent = a.xpath('./@title').get()
            yield Request(url, meta={"parent": parent}, callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//li[@class="product-item"]/div[1]/a/@href').extract()
        for url in urls:
            yield Request(url, meta=response.meta, callback=self.detail_parse)

    def detail_parse(self, response):
        tmp_xpath = '//*[contains(text(), {!r})]/ancestor::td/following-sibling::td//text()'
        d = {
            "brand": "Sinco",
            "parent": response.meta.get('parent'),
            "cat_no": "".join(response.xpath(tmp_xpath.format("CAT#:")).extract()),
            "cas": "".join(response.xpath(tmp_xpath.format("CAS#:")).extract()),
            "en_name": response.xpath('//div[@class="right pro_det_nr"]/h1/text()').get(),
            "mf": "".join(response.xpath(tmp_xpath.format("M.F.:")).extract()),
            "mw": "".join(response.xpath(tmp_xpath.format("M.W.:")).extract()),
            "img_url": response.xpath('//img[@class="smallImg"]/@src').get(),
            "prd_url": response.url,
        }
        yield RawData(**d)

