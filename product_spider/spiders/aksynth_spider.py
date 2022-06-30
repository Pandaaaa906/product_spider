from urllib.parse import urljoin

import scrapy

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class AksynthSpider(BaseSpider):
    name = "aksynth"
    base_url = "https://www.aksynth.com/"
    start_urls = ["https://www.aksynth.com/aksynth-prod-cat"]

    def parse(self, response, **kwargs):
        rows = response.xpath("//div[@class='fadeInLeft']//a/@href").getall()
        for row in rows:
            url = f"https://www.aksynth.com/{row}"
            yield scrapy.Request(
                url=url,
                callback=self.parse_category_list
            )

    def parse_category_list(self, response):
        rows = response.xpath("//div[@class='row']/a")
        for row in rows:
            href = row.xpath("./@href").get()
            parent = strip(row.xpath(".//li/b/text()").get())
            url = f"https://www.aksynth.com/{href}"
            yield scrapy.Request(
                url=url,
                callback=self.parse_prd_list,
                meta={"parent": parent}
            )

    def parse_prd_list(self, response):
        parent = response.meta.get("parent", None)
        rows = response.xpath("//div[@class='panel-heading']/a/@href").getall()
        for row in rows:
            url = f"https://www.aksynth.com/{row}"
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={"parent": parent}
            )

    def parse_detail(self, response):
        parent = response.meta.get("parent", None)
        tmp_xpath = "//td[contains(text(), {!r})]/following-sibling::td/text()"
        cat_no = response.xpath(tmp_xpath.format("CAT No :")).get()
        mf = response.xpath(tmp_xpath.format("Molecular Formula :")).get()
        mw = response.xpath(tmp_xpath.format("Molecular Weight :")).get()
        cas = response.xpath(tmp_xpath.format("CAS Number :")).get()
        en_name = response.xpath("//div[@class='panel-heading']/h1/text()").get()
        img_url = urljoin(self.base_url, response.xpath("//div[@align='center']/img/@src").get())

        d = {
            "brand": self.name,
            "parent": parent,
            "en_name": en_name,
            "cat_no": cat_no,
            "mf": mf,
            "mw": mw,
            "cas": cas,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)
