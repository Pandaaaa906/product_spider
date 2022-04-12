from urllib.parse import urljoin
import scrapy
from product_spider.items import RawData
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class PlxPrdSpider(BaseSpider):
    """博泰尔"""
    name = 'plx'
    base_url = 'http://plcchemical.com/'
    start_urls = ["http://plcchemical.com/products.php", ]

    def parse(self, response, **kwargs):
        rows = response.xpath("//*[contains(text(), 'Details')]")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )
        next_url = response.xpath("//div[@class='page_list']/a[last()-1]/@href").get()
        if next_url == "javascript:;":
            return
        next_page = urljoin(self.base_url, next_url)
        if next_page:
            yield scrapy.Request(
                url=next_page,
                callback=self.parse,
            )

    def parse_detail(self, response):
        cat_no = response.xpath("//*[contains(text(), 'Cat. Number:')]/parent::p/text()").get()
        en_name = response.xpath("//*[contains(text(), 'Compound Name:')]/parent::p/text()").get()
        cas = response.xpath("//*[contains(text(), 'CAS Number:')]/parent::p/text()").get()
        mf = formula_trans(response.xpath("//*[contains(text(), 'Molecular Formula:')]/parent::p/text()").get())
        mw = response.xpath("//*[contains(text(), 'Molecular Weight:')]/parent::p/text()").get()
        img_url = urljoin(self.base_url, response.xpath("//div[@class='float-left pro_details_img']/img/@src").get())

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "en_name": en_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)
