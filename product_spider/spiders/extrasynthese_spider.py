import re

import scrapy

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.functions import strip


class ExtrasyntheseSpider(BaseSpider):
    """法国中草药"""
    name = "extrasynthese"
    allow_domain = ["extrasynthese.com"]
    start_urls = ["https://www.extrasynthese.com/4-chemical-families"]

    def parse(self, response, **kwargs):
        rows = response.xpath("//a[contains(text(), 'See all products')]")
        for row in rows:
            url = row.xpath(".//@href").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        rows = response.xpath("//div[@class='col col-md-4 col-lg-3']")
        for row in rows:
            url = row.xpath(".//div[@class='thumbnail-container']//a/@href").get()
            img_url = row.xpath("///div[@class='thumbnail-container']//img/@data-src").get()

            yield scrapy.Request(
                url=url,
                meta={"img_url": img_url},
                callback=self.parse_detail
            )
        next_url = response.xpath("//ul[@class='page-list clearfix text-center']//li[last()]//a/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        cas = strip(response.xpath("//div[@data-title='Cas']/text()").get())
        if cas:
            cas = (m := re.search(r'\d+-\d{2}-\d\b', cas)) and m.group()

        d = {
            "brand": self.name,
            "parent": response.xpath('//div[@data-title="Family"]//a/text()').get(),
            "cat_no": response.xpath("//div[@data-title='Code #']/text()").get('').strip(),
            "en_name": response.xpath("//div[@class='col col-xl-10 offset-xl-1']//li[last()]//span/text()").get(),
            "cas": cas,
            "mf": formula_trans(response.xpath("//div[@data-title='Formula']/text()").get()),
            "mw": response.xpath("//div[@data-title='MW']/text()").get(),
            "smiles": response.xpath('//div[@data-title="Smiles"]//div[@class="_rest"]/text()').get(),

            "prd_url": response.url,
            "img_url": response.meta.get("img_url", None),
        }
        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id": f'{self.name}_{d["cat_no"]}',
            "parent": d["parent"],
            "en_name": d["en_name"],
            "cas": d["cas"],
            "mf": d["mf"],
            "mw": d["mw"],
            'cat_no': d["cat_no"],
            "img_url": d["img_url"],
            "prd_url": d["prd_url"],
        }
        yield RawData(**d)
        yield SupplierProduct(**ddd)

        pkg_qty = response.xpath('//input[@id="valcata_origin"]/@value').get()
        pkg_unit = response.xpath('//input[@id="condition_cata"]/@value').get()
        price = response.xpath("//span[@id='prix_produit']//@content").get()
        dd = {
            "brand": self.name,
            "cat_no": d['cat_no'],
            "package": f"{pkg_qty}{pkg_unit}",
            "cost": price,
            "currency": 'EUR',
        }
        dddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id":  f'{self.name}_{d["cat_no"]}',
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'discount_price': dd['cost'],
            'price': dd['cost'],
            'currency': dd["currency"],
        }
        yield ProductPackage(**dd)
        yield RawSupplierQuotation(**dddd)
