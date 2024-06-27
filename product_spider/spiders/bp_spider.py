import time
from urllib.parse import urljoin
import json
from scrapy import Request
import re
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.spider_mixin import BaseSpider


class BPSpider(BaseSpider):
    name = "bp"
    start_urls = ["https://www.pharmacopoeia.com/shop/products", ]
    base_url = "https://www.pharmacopoeia.com/"

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//ul[@class="spl-list"]//div/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

        next_page = response.xpath('//div[@class="pagination"]//li[@class="selected"]/following-sibling::li/a/@href') \
            .get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse)

    def parse_detail(self, response):
        tmp = '//div[@class="col spd-col" and contains(text(), {!r})]/following-sibling::div//text()'
        cat_no = response.xpath(tmp.format('Catalogue number')).get()
        batch_num = response.xpath(tmp.format('Batch number')).get()  # 批号
        shipping_info = response.xpath(tmp.format('Shipping conditions')).get()  # 运输条件
        controlled_drug = response.xpath(tmp.format('Controlled drug')).get()  # 管控产品
        expiry_date = response.xpath(tmp.format('Expiry date')).get()  # 有效期

        attrs = json.dumps({
            'controlled_drug': controlled_drug,
        })

        package_attrs = json.dumps({
            'batch_num': batch_num,
            'expiry_date': expiry_date,
        })

        package = response.xpath(tmp.format('Pack size')).get()
        if package:
            package = package.replace(' ', '')
        cost = response.xpath(tmp.format('Price')).get()
        if cost:
            cost = re.search(r'(?<=£)\d+', cost).group()

        d = {
            'brand': self.name,
            'cat_no': cat_no,
            'en_name': ''.join(response.xpath('//h1//text()').getall()),
            "cas": response.xpath(tmp.format('CAS number')).get(),
            "info2": ''.join(response.xpath(tmp.format('Long term storage conditions')).getall()),
            "stock_info": response.xpath(tmp.format('Availability')).get(),
            "prd_url": response.url,
            "shipping_info": shipping_info,
            "attrs": attrs
        }

        dd = {
            "brand": self.name,
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
            "source_id": f'{self.name}_{cat_no}_{package}',
            "en_name": d["en_name"],
            "cas": d["cas"],
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'cost': dd['cost'],
            "currency": dd["currency"],
            "prd_url": d["prd_url"],
        }
        dddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id": f'{self.name}_{d["cat_no"]}',
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'discount_price': dd['cost'],
            'price': dd['cost'],
            'cas': d["cas"],
            'currency': dd["currency"],
        }
        yield RawData(**d)
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)
