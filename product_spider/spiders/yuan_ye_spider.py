import re
from urllib.parse import urljoin

import scrapy

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class YuanYeSpider(BaseSpider):
    """上海源叶"""
    name = "yuan_ye"
    start_urls = ["http://www.shyuanye.com/"]
    base_url = "http://www.shyuanye.com/"

    def parse(self, response, **kwargs):
        urls = response.xpath("//a[@class='over_2']/@href").getall()
        for url in urls:
            url = urljoin(self.base_url, url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        rows = response.xpath("//div[@class='goodsList']//tr/td[last()-4]//a")
        for row in rows:
            cat_no = row.xpath("./text()").get()
            url = urljoin(self.base_url, row.xpath("./@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={"cat_no": cat_no},
            )
        next_url = response.xpath("//a[contains(text(), '下一页')]/@href").get()
        if next_url:
            yield scrapy.Request(
                url=urljoin(self.base_url, next_url),
                callback=self.parse_list
            )

    def parse_detail(self, response):
        cat_no = response.meta.get("cat_no", None)
        parent = response.xpath("//div[@id='ur_here']/a[last()]/text()").get()
        chs_name = response.xpath("//div[@class='titleInfo']//td[last()]/h1/text()").get()
        purity = response.xpath("//div[@class='titleInfo']//td[last()]/text()").get()
        tmp_xpath = "//li[contains(text(), {!r})]/following-sibling::li//text()"

        en_name = strip(response.xpath(tmp_xpath.format("英文名：")).get())
        cas = strip(response.xpath(tmp_xpath.format("CAS号：")).get())
        mf = strip(''.join(response.xpath(tmp_xpath.format("分子式：")).getall()))
        mw = strip(response.xpath(tmp_xpath.format("分子量：")).get())
        mdl = strip(response.xpath(tmp_xpath.format("MDL：")).get())

        img_url = response.xpath("//div[@class='imgInfo']//img/@src").get()
        if img_url == "./images/no_picture.jpg":
            img_url = None
        else:
            img_url = urljoin(self.base_url, img_url)

        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": cat_no,
            "chs_name": chs_name,
            "purity": purity,
            "en_name": en_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "mdl": mdl,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)
        rows = response.xpath("//form[@name='form1 ']//tr")
        for row in rows:
            res = re.search(r'(?<=-).*', row.xpath("./td[last()-10]/text()").get())
            if not res:
                continue
            package = res.group()
            cost = parse_cost(row.xpath("./td[last()-7]/text()").get())
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "cost": cost,
                "currency": "RMB"
            }
            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "parent": d["parent"],
                "en_name": d["en_name"],
                "chs_name": d["chs_name"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
                "img_url": d["img_url"],
                "prd_url": d["prd_url"],
            }
            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)
