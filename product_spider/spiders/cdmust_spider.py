import time
from urllib.parse import urljoin
import scrapy
from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class CdmustSpider(BaseSpider):
    """曼思特"""
    name = "cdmust"
    allow_domain = ["cdmust.com"]
    start_urls = ["http://www.cdmust.com/goods/list.aspx"]
    base_url = 'http://www.cdmust.com/goods/list.aspx'

    def parse(self, response):
        time.sleep(25)
        rows = response.xpath("//li[@class='on']//ul//following-sibling::li")
        for row in rows:
            url = urljoin(self.base_url, row.xpath(".//a/@href").get())
            parent = row.xpath(".//a/text()").get()
            yield scrapy.Request(
                url=url,
                meta={'parent': parent},
                callback=self.parse_list
            )

    def parse_list(self, response):
        time.sleep(40)
        parent = response.meta.get("parent", {})

        rows = response.xpath("//th[contains(text(), '编号')]//ancestor::table/tbody/tr")

        for row in rows:
            cat_no = row.xpath(".//td[last()-8]/text()").get()
            cas = row.xpath(".//td[last()-5]/text()").get()
            purity = row.xpath(".//td[last()-4]/text()").get()
            package = row.xpath(".//td[last()-3]/text()").get()
            mf = row.xpath(".//td[last()-1]/text()").get()
            mw = row.xpath(".//td[last()]/text()").get()

            d = {
                "brand": self.name,
                "cat_no": cat_no,
                "cas": cas,
                "purity": purity,
                "mf": mf,
                "mw": mw,
                "parent": parent,
            }
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
            }
            url = urljoin(self.base_url, row.xpath(".//a/@href").get())
            yield scrapy.Request(
                url=url,
                meta={"product": d, "package": dd},
                callback=self.parse_detail
            )

    def parse_detail(self, response):
        time.sleep(30)
        d = response.meta.get("product", {})
        dd = response.meta.get("package", {})
        en_name = response.xpath("//td[contains(text(), '英文名')]//following-sibling::td/text()").get()
        chs_name = response.xpath("//td[contains(text(), '中文名称')]//following-sibling::td/text()").get()
        appearance = response.xpath(
            "//td[contains(text(), '外观')]//parent::tr//tr[position()=1]//td[last()-1]/text()").get()
        img_url = urljoin(self.base_url, response.xpath(
            "//td[contains(text(), '外观')]//parent::tr//tr[position()=1]//td[last()]//img/@src").get())

        d["en_name"] = en_name.strip()
        d["chs_name"] = chs_name.strip()
        d["appearance"] = appearance.strip()
        d["img_url"] = img_url
        d["prd_url"] = response.url

        yield RawData(**d)
        yield ProductPackage(**dd)
