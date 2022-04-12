import scrapy

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class SynzestPrdSpider(BaseSpider):
    """世洲"""
    name = 'synzest'
    start_urls = ["http://www.synzest.com/products/2/", ]

    def parse(self, response, **kwargs):
        rows = response.xpath("//div[@class='col-md-4 col-sm-6 col-xs-12']")
        for row in rows:
            url = '{}{}'.format("http:", row.xpath(".//h2/a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )
        max_page = response.xpath("//div[@class='text-center kj_pronav']/input/@pagecount").get()
        for i in range(2, int(max_page) + 1):
            yield scrapy.Request(
                url=f"http://www.synzest.com/products/2.html?page={i}&prop_filter=%7b%7d",
                callback=self.parse,
            )

    def parse_detail(self, response):
        cat_no = response.xpath("//*[contains(text(), '产品编号：')]/following-sibling::td/text()").get()
        en_name = response.xpath("//*[contains(text(), '英文名称：')]/following-sibling::td/text()").get()
        cas = response.xpath("//*[contains(text(), 'CAS号：')]/following-sibling::td/text()").get()
        mf = response.xpath("//*[contains(text(), '分子式：')]/following-sibling::td/text()").get()
        mw = response.xpath("//*[contains(text(), '分子量：')]/following-sibling::td/text()").get()
        chs_name = response.xpath("//*[contains(text(), '中文名称：')]/following-sibling::td/text()").get()
        parent = response.xpath("//*[@class='breadcrumb']/li[last()]/a/text()").get()
        img_url = response.xpath("//div[@class='item active text-center']/img/@src").get()

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "en_name": en_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "chs_name": chs_name,
            "parent": parent,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)
