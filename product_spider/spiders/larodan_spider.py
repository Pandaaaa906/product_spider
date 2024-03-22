import json

import scrapy

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class LarodanPrdSpider(BaseSpider):
    """larodan"""
    name = 'larodan'
    start_urls = ["https://www.larodan.com/products/", ]

    def parse(self, response, **kwargs):
        rows = response.xpath("//*[@class='product-categories']//a")
        for row in rows:
            url = row.xpath("./@href").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        rows = response.xpath("//li[@class='product-category product first']")
        if rows:
            for row in rows:
                url = row.xpath("./a/@href").get()
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_list
                )
        else:
            rels = response.xpath("//*[@class='woocommerce-LoopProduct-link woocommerce-loop-product__link']")
            for rel in rels:
                url = rel.xpath("./@href").get()
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                )
            next_url = response.xpath("//ul[@class='page-numbers']//li[last()]/a/@href").get()
            if next_url:
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_list,
                )

    def parse_detail(self, response):
        en_name = response.xpath("//h1[@class='h1']/text()").get()
        parent = response.xpath("//*[@class='woocommerce-breadcrumb']/a[last()]/text()").get()
        cat_no = response.xpath("//*[contains(text(), 'Product number: ')]/following-sibling::span/text()").get()
        cas = response.xpath("//*[contains(text(), 'CAS number: ')]/parent::div/text()").get()
        purity = ''.join(response.xpath("//*[contains(text(), 'Purity: ')]/parent::div/text()").getall()).strip()
        info2 = ''.join(response.xpath("//*[contains(text(), 'Storage: ')]/parent::div/text()").getall()).strip()
        smiles = ''.join(response.xpath("//*[contains(text(), 'Smiles: ')]/parent::div/text()").getall()).strip()
        mf = ''.join(response.xpath("//*[contains(text(), 'Molecular formula: ')]/parent::div/text()").getall()).strip()
        mw = ''.join(response.xpath("//*[contains(text(), 'Molecular weight: ')]/parent::div/text()").getall()).strip()
        img_url = response.xpath("//div[@class='prod-structure']/img/@src").get()
        coa_url = response.xpath("//*[contains(text(), 'Download')]/@href").get()  # 证书地址

        prd_attrs = json.dumps({
            "coa_url": coa_url,
        })

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "en_name": en_name,
            "purity": purity,
            "info2": info2,
            "smiles": smiles,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "parent": parent,
            "img_url": img_url,
            "prd_url": response.url,
            "attrs": prd_attrs,
        }
        yield RawData(**d)
