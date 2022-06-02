from string import ascii_lowercase
from urllib.parse import urljoin

import scrapy

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class VenKaTaSaiLifeSciencesSpider(BaseSpider):
    name = "venkatasai"
    start_urls = ["https://www.venkatasailifesciences.com/category/a"]
    base_url = "https://www.venkatasailifesciences.com/"

    def start_requests(self):
        for char in ascii_lowercase:
            yield scrapy.Request(
                url=f"https://www.venkatasailifesciences.com/category/{char}",
                callback=self.parse
            )

    def parse(self, response, **kwargs):
        rows = response.xpath("//*[@class='col-md-3 clsDivMaincat']/a")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./@href").get())
            parent = row.xpath("./text()").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                meta={"parent": parent},
            )

    def parse_list(self, response):
        parent = response.meta.get("parent", None)
        rows = response.xpath("//*[@class='image']/a")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={"parent": parent},
            )

    def parse_detail(self, response):
        parent = response.meta.get("parent", None)
        en_name = response.xpath("//h1[@class='home-title']/text()").get()
        cat_no = response.xpath("//*[contains(text(), 'CAT No')]/following-sibling::td/text()").get()
        cas = response.xpath("//*[contains(text(), 'CAS No')]/following-sibling::td/text()").get()
        mf = response.xpath("//*[contains(text(), 'Mol.F.')]/following-sibling::td/text()").get()
        mw = response.xpath("//*[contains(text(), 'Mol.Wt.')]/following-sibling::td/text()").get().strip()
        info1 = ''.join(response.xpath("//*[contains(text(), 'Chemical Name:')]/parent::div/text()").getall()).strip()
        img_url = response.xpath("//*[@class='picture']/img/@src").get()
        d = {
            "parent": parent,
            "brand": self.name,
            "en_name": en_name,
            "cat_no": cat_no,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "info1": info1,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)
