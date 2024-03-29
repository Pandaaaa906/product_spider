from urllib.parse import urljoin

import scrapy
import re

from more_itertools import first

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.spider_mixin import BaseSpider

space_trans = str.maketrans('', '', '\xa0')


class LemeitianSpider(BaseSpider):
    """乐美天医药"""
    name = "lemeitian"
    allow_domain = ["lemeitian.cn"]
    start_urls = ["http://www.lemeitian.cn/SubCategory", ]
    base_url = "http://www.lemeitian.cn/SubCategory"

    def parse(self, response, **kwargs):
        rows = response.xpath("//div[@class='category_list']//div")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        rows = response.xpath("//div[@class='goods-list-row']//dl")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./dt[last()-7]/a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail
            )
        next_url = urljoin(self.base_url, response.xpath("//a[contains(text(), '下一页')]/@href").get(""))
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        p = re.compile(r'(?<=:).+')
        parent = response.xpath("//div[@class='nav_info']/a[last()]/text()").get()

        cat_no = response.xpath("//div[contains(text(), '产品编号:')]/text()").get('').translate(space_trans)
        cat_no = (m := p.search(cat_no)) and m.group()

        cas = response.xpath("//div[contains(text(), 'CAS NO:')]/text()").get('').translate(space_trans)
        cas = (m := p.search(cas)) and m.group()

        package = response.xpath("//div[contains(text(), '规 格:')]/text()").get('').translate(space_trans)
        package = (m := p.search(package)) and m.group()

        en_name = response.xpath("//div[contains(text(), '英文名称:')]/text()").get('').translate(space_trans)
        en_name = (m := p.search(en_name)) and m.group()

        chs_name = response.xpath("//div[@id = 'bfdProductTitle']/text()").get('').split()
        chs_name = first(chs_name, '')

        mf = response.xpath("//div[contains(text(), '分子式:')]/text()").get('').translate(space_trans)
        mf = (m := p.search(mf)) and m.group()

        mw = response.xpath("//div[contains(text(), '分子量:')]/text()").get('').translate(space_trans)
        mw = (m := p.search(mw)) and m.group()

        purity = response.xpath("//td[contains(text(), '纯  度:')]/text()").get('').translate(space_trans)
        purity = (m := p.search(purity)) and m.group()

        img_url = response.xpath("//a[@id='zoom1']/@href").get()

        price = response.xpath("//span[@id = 'lblBuyPrice']/text()").get()
        if price == 0.00:
            price = None

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": parent,
            "cas": cas,
            "en_name": en_name,
            "chs_name": chs_name,
            "mf": mf,
            "mw": mw,
            "purity": purity,
            "prd_url": response.url,
            "img_url": img_url,
        }

        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "package": package,
            "cost": price,
            "currency": "RMB",
        }

        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "parent": d["parent"],
            "en_name": d["en_name"],
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

        yield RawData(**d)
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
