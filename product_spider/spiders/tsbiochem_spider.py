import re
from urllib.parse import urljoin

import scrapy
from product_spider.items import ProductPackage, RawData
from product_spider.utils.spider_mixin import BaseSpider


class TsbiochemSpider(BaseSpider):
    """陶术"""
    name = "tsbiochem"
    start_urls = ["https://www.tsbiochem.com/"]
    base_url = "https://www.tsbiochem.com/"

    def parse(self, response, **kwargs):
        rows = response.xpath("//div[@class='column']/a")
        for row in rows:
            url = row.xpath("./@href").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        # catalog list
        rows = response.xpath("//div[@class='lbylist-new-container']")
        for row in rows:
            url = row.xpath("./a/@href").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail
            )

        # product list
        nodes = response.xpath("//table[@class='table-cpd-list']//tbody/tr")
        for node in nodes:
            url = node.xpath("./td[position()=1]/a/@href").get()
            cat_no = node.xpath("./td[position()=1]/a/text()").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail_v2,
                meta={
                    "cat_no": cat_no,
                }
            )
        # product list paginator
        next_url = response.xpath("//div[@class='block-pager']/a[last()]/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        parent = response.xpath("//div[@class='block-title-page ts2']/h1/text()").get()
        cat_no = re.search(r'(?<=产品编号 ).*', response.xpath("//div[@class='bottom']/div/text()").get()).group()
        img_url = urljoin(self.base_url, response.xpath("//img[@class='product-top-image']/@src").get())
        en_name = response.xpath("//div[@class='block-title-page ts2']/div/text()").get()
        chs_name = response.xpath("//div[@class='block-title-page ts2']/h1/text()").get()
        rows = response.xpath("//table[@class='prices type2']//tbody/tr")
        for row in rows:
            package = row.xpath("./td[position()=1]/text()").get().strip()
            price = rows.xpath("./td[position()=2]/text()").get().strip()
            d = {
                "parent": parent,
                "brand": self.name,
                "cat_no": cat_no,
                "img_url": img_url,
                "prd_url": response.url,
                "chs_name": chs_name,
                "en_name": en_name
            }
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "cost": price,
                "currency": "RMB",
            }
            yield RawData(**d)
            yield ProductPackage(**dd)

    def parse_detail_v2(self, response):
        cat_no = response.meta.get("cat_no")
        parent = response.xpath("//div[@class='block-breadcrumb style2 zh']/a[last()]/text()").get()
        en_name = response.xpath("//div[@class='block-title-page ts2']/h1/text()").get()
        purity = response.xpath(
            "//table[@class='table-cpd-info']//td[contains(text(), '纯度')]/following-sibling::td/span/text()"
        ).get()
        mw = response.xpath(
            "//table[@class='table-cpd-info']//td[contains(text(), '分子量')]/following-sibling::td/text()"
        ).get().strip()
        mf = response.xpath(
            "//table[@class='table-cpd-info']//td[contains(text(), '分子式')]/following-sibling::td/text()"
        ).get()
        cas = response.xpath(
            "//table[@class='table-cpd-info']//td[contains(text(), 'CAS No.')]/following-sibling::td/text()"
        ).get()
        img_url = urljoin(self.base_url, response.xpath("//div[@class='img-box']/img/@src").get()) \
                  or response.xpath("//div[@class='img-box']/div/text()").get()
        if parent == '首页':
            parent = None
        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": parent,
            "en_name": en_name,
            "purity": purity,
            "mw": mw,
            "mf": mf,
            "cas": cas,
            "prd_url": response.url,
            "img_url": img_url,
        }
        nodes = response.xpath("//tr[@class='line-item']")
        for node in nodes:
            package = node.xpath("./td[position()=1]/text()").get()
            delivery_time = node.xpath("./td[position()=2]/text()").get().strip()
            price = node.xpath("./td[position()=3]/text()").get().strip()
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "delivery_time": delivery_time,
                "cost": price,
                "currency": "RMB",
            }
            yield RawData(**d)
            yield ProductPackage(**dd)
