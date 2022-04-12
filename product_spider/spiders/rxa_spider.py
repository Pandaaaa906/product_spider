from urllib.parse import urljoin

import scrapy

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class RxaPrdSpider(BaseSpider):
    """RXA"""
    name = 'rxa'
    base_url = "http://www.rxachemical.com/"
    start_urls = ["http://www.rxachemical.com/pr.jsp", ]

    def parse(self, response, **kwargs):
        rows = response.xpath("//table [@class='g_foldContainerPanel fk_navClickContent']")
        for row in rows:
            url = urljoin(self.base_url, row.xpath(".//a/@href").get())
            parent = row.xpath(".//a/text()").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                meta={
                    "parent": parent,
                },
            )

    def parse_list(self, response):
        parent = response.meta.get("parent")
        rows = response.xpath("//div[@class='propDiv productName productNameWordWrap    ']")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={
                    "parent": parent,
                },
            )
        next_url = urljoin(self.base_url, response.xpath("//*[contains(text(), 'Next')]/parent::a/@href").get())
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        parent = response.meta.get("parent")
        en_name = response.xpath("//div[@class='J_productTitle title g_minor']/span/text()").get()
        cat_no = response.xpath("//*[contains(text(), 'RXA NO：')]/following-sibling::td/span/text()").get()
        mf = response.xpath("//*[contains(text(), 'MF：')]/following-sibling::td/span/text()").get()
        mw = response.xpath("//*[contains(text(), 'MW：')]/following-sibling::td/span/text()").get()
        cas = response.xpath("//*[contains(text(), 'CAS NO：')]/following-sibling::td/span/text()").get()
        img_url = '{}{}'.format("http:", response.xpath("//div[@class='imgContainer imgContainer_J']//img/@src").get())

        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": cat_no,
            "en_name": en_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)
