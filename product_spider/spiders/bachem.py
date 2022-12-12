import json
import re

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class BachemSpider(BaseSpider):
    name = "bachem"
    base_url = "https://shop.bachem.com/"
    currency_url = 'https://shop.bachem.com/storeselect/index/forward/country/CN/'
    start_urls = [
        "https://shop.bachem.com/application.html",
        "https://shop.bachem.com/inhibitors-and-substrates.html",
        "https://shop.bachem.com/amino-acids-and-biochemicals.html",
        "https://shop.bachem.com/peptides.html",
        "https://shop.bachem.com/new-products.html",
    ]
    cookies = {
        'store_country': 'US',
        'store': 'us',
        'storeselect': 'US%2Fus'
    }

    def start_requests(self):
        yield Request(
            url="https://shop.bachem.com/catalog/all-products/",
            callback=self.parse,
        )

    def parse(self, response, **kwargs):
        urls = response.xpath("//a[contains(text(), 'More info ')]/@href").getall()
        for url in urls:
            yield Request(url, callback=self.parse_detail, cookies=self.cookies)

        next_page = response.xpath("//a[contains(text(), 'Next »')]/@href").get()
        if next_page:
            yield Request(next_page, callback=self.parse, cookies=self.cookies)

    def parse_detail(self, response):

        tmp_xpath = "//span[contains(text(), {!r})]/parent::p/text()"
        cat_no = response.xpath(tmp_xpath.format("Product Number")).get()
        mw = response.xpath(tmp_xpath.format("Molecular weight")).get()
        info2 = response.xpath(tmp_xpath.format("Storage Temperature")).get()
        cas = response.xpath(tmp_xpath.format("CAS Number")).get()
        synonyms = response.xpath(tmp_xpath.format("Synonyms")).get()
        mf1 = formula_trans(response.xpath(tmp_xpath.format("Chemical Formula")).get())
        mf2 = formula_trans(response.xpath(tmp_xpath.format("Sum Formula")).get())
        parent = response.xpath("//nav[@class='woocommerce-breadcrumb']//a[last()]/text()").get()
        en_name = response.xpath("//div[@class='et_pb_module_inner']/h1/text()").get()
        img_url = response.xpath("//div[@class='et_pb_module_inner']/img/@src").get()

        prd_attrs = json.dumps({
            "synonyms": synonyms
        })

        d = {
            'brand': 'bachem',
            'parent': parent,
            'cat_no': cat_no,
            'cas': cas,
            "en_name": en_name,
            'mf': mf1 or mf2,
            'mw': mw,
            'info2': info2,
            'img_url': img_url,
            'prd_url': response.url,
            'attrs': prd_attrs,
        }
        yield RawData(**d)

        rows = response.xpath("//select[@id='pa_pack-weight']/option[@value!='']")
        for row in rows:
            row_data = row.xpath("./text()").get()
            if not row_data:
                continue
            package = row_data.split(" ")[0]
            raw_cost = row_data.split(" ")[-1]
            cost = re.search(r'(?<=\(\$\xa0)\d+(?=\))', raw_cost)
            if cost:
                cost = cost.group()
            dd = {
                'brand': 'bachem',
                'cat_no': cat_no,
                'package': package,
                "cost": cost,
                "currency": "USD",
            }
            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id": f'{self.name}_{cat_no}_{package}',
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
            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)
            yield RawSupplierQuotation(**dddd)
