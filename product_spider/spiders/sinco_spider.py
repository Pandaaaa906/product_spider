import re
from itertools import chain
from string import ascii_uppercase
from urllib.parse import urljoin
from scrapy import Request
from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class SincoSpider(BaseSpider):
    name = "sinco"
    start_urls = (f"http://www.sincopharmachem.com/category.asp?c={c}" for c in chain(ascii_uppercase, ('OTHER',)))
    base_url = "http://www.sincopharmachem.com"

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//li[@class="product-category-item"]/a')
        for a in a_nodes:
            url = urljoin(self.base_url, a.xpath('./@href').get())
            parent = a.xpath('./@title').get()
            yield Request(url, meta={"parent": parent}, callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//div[@class="rm"]/a/@href').extract()
        for url in urls:
            yield Request(url, meta=response.meta, callback=self.detail_parse)
        next_page = response.xpath("//li[@class='pro_fyq_next']/a/@href").get()
        if next_page and next_page != "javascript:":
            yield Request(urljoin(self.base_url, next_page), meta=response.meta, callback=self.list_parse)

    def detail_parse(self, response):
        tmp_xpath = '//*[contains(text(), {!r})]/ancestor::td/following-sibling::td//text()'
        tmp_cat_no = response.xpath('//*[contains(text(), "CAT#:")]/text()').get()
        cat_no = "".join(response.xpath(tmp_xpath.format("CAT#:")).extract()) \
                 or response.xpath("//*[contains(text(), 'CAT#:')]/following-sibling::td/text()").get() \
                 or tmp_cat_no.replace('CAT#:', '') \
                 or re.search(r"(?<=\t)\w\d{5}",
                              ''.join(response.xpath("//div[@class='pro_det_jj']/p[position()=1]/text()").get()))

        d = {
            "brand": "sinco",
            "parent": response.meta.get('parent'),
            "cat_no": cat_no,
            "cas": "".join(response.xpath(tmp_xpath.format("CAS#:")).extract()),
            "en_name": response.xpath('//div[@class="right pro_det_nr"]/h1/text()').get(),
            "mf": "".join(response.xpath(tmp_xpath.format("M.F")).extract()),
            "mw": "".join(response.xpath(tmp_xpath.format("M.W")).extract()),
            "img_url": response.xpath('//img[@class="smallImg"]/@src').get(),
            "prd_url": response.url,
        }
        yield RawData(**d)
        packages = response.xpath(tmp_xpath.format("Specification: ")).get() or \
                   response.xpath(
                       "//strong[contains(text(), 'Specification: ')]/ancestor::td/following-sibling::td//span/text()").get()
        if packages:
            packages = packages.split(',')
            for package in packages:
                dd = {
                    "brand": "sinco",
                    "cat_no": cat_no,
                    "package": package
                }
                yield ProductPackage(**dd)
