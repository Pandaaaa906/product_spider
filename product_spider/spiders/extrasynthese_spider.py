import re

import scrapy

from product_spider.items import RawData, ProductPackage
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class ExtrasyntheseSpider(BaseSpider):
    """法国中草药"""
    name = "extrasynthese"
    allow_domain = ["extrasynthese.com"]
    start_urls = ["https://www.extrasynthese.com/4-chemical-families"]

    def parse(self, response):
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
        img_url = response.meta.get("img_url", None)
        en_name = response.xpath("//div[@class='col col-xl-10 offset-xl-1']//li[last()]//span/text()").get()
        cas = response.xpath("//div[@data-title='Cas']/text()").get('').strip()
        cas = (m := re.search(r'\d+-\d{2}-\d\b', cas)) and m.group()
        cat_no = response.xpath("//div[@data-title='Code #']/text()").get('').strip()
        mf = formula_trans(response.xpath("//div[@data-title='Formula']/text()").get('').strip())
        mw = response.xpath("//div[@data-title='MW']/text()").get('').strip()
        smiles = response.xpath("//div[@data-title='Smiles']/text()").get('').strip()
        parent = response.xpath("//div[@data-title='Family']//a/text()").get()
        package = response.xpath(
            "//div[@class='cntnt my-2']//label/following-sibling::input[(@disabled)]/@value"
        ).get().replace(' ', '')
        price = response.xpath("//span[@id='prix_produit']//@content").get()

        d = {
            "prd_url": response.url,
            "img_url": img_url,
            "brand": self.name,
            "cat_no": cat_no,
            "cas": cas,
            "en_name": en_name,
            "mf": mf,
            "mw": mw,
            "smiles": smiles,
            "parent": parent,
        }
        yield RawData(**d)

        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "package": package,
            "price": price,
            "currency": '€',
        }
        yield ProductPackage(**dd)
