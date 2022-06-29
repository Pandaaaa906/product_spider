import time
from urllib.parse import urljoin
import json
from scrapy import Request
import re
from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.spider_mixin import BaseSpider

class BPSpider(BaseSpider):
    name = "bp"
    start_urls = ["https://www.pharmacopoeia.com/Catalogue/Products", ]
    base_url = "https://www.pharmacopoeia.com/"

    def parse(self, response, **kwargs):
        for url in self.start_urls:
            yield Request(url, callback=self.dummy_parse)

    def dummy_parse(self, response):
        time.sleep(3)
        rel_urls = response.xpath('//table[@class="product-table"]/tbody/tr/td[3]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail)

        next_page = response.xpath('//div[@class="pagination"]//li[@class="active"]/following-sibling::li[1]/a/@href') \
            .get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.dummy_parse)

    def parse_detail(self, response):
        time.sleep(3)
        tmp = '//th[contains(text(), {!r})]/following-sibling::td//text()'
        cat_no = response.xpath(tmp.format('Catalogue Number:')).get()
        batch_num = response.xpath(tmp.format('Batch Number:')).get()  # 批号
        shipping_info = response.xpath(tmp.format('Shipping Conditions:')).get()  # 运输条件
        controlled_drug = response.xpath(tmp.format('Controlled Drug:')).get()  # 管控产品
        expiry_date = response.xpath(tmp.format('Expiry Date:')).get()  # 有效期

        attrs = json.dumps({
            'controlled_drug': controlled_drug,
        })

        package_attrs = json.dumps({
            'batch_num': batch_num,
            'expiry_date': expiry_date,
        })

        package = response.xpath(tmp.format('Pack Size:')).get()
        if package:
            package = package.replace(' ', '')
        cost = response.xpath(tmp.format('Price:')).get()
        if cost:
            cost = re.search(r'(?<=£)\d+', cost).group()

        d = {
            'brand': 'bp',
            'cat_no': cat_no,
            'en_name': ''.join(response.xpath('//header/h1//text()').getall()),
            "cas": response.xpath(tmp.format('CAS Number:')).get(),
            "info2": ''.join(response.xpath(tmp.format('Long-Term Storage')).getall()),
            "stock_info": response.xpath(tmp.format('Availability:')).get(),
            "prd_url": response.url,
            "shipping_info": shipping_info,
            "attrs": attrs
        }

        dd = {
            "brand": 'bp',
            "cat_no": cat_no,
            "package": package,
            "cost": cost,
            "currency": "GBP",
            "attrs": package_attrs,
        }

        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "en_name": d["en_name"],
            "cas": d["cas"],
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'cost': dd['cost'],
            "currency": dd["currency"],
            "prd_url": d["prd_url"],
        }

        yield RawData(**d)
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
