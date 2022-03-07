import json
from urllib.parse import urljoin

import scrapy
import re
from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class HerbpurifySpider(BaseSpider):
    """成都瑞芬思"""
    name = "herbpurify"
    allow_domain = ["herbpurify.com"]
    start_urls = ["http://www.herbpurify.com/"]
    base_url = "http://www.herbpurify.com/"

    def parse(self, response):
        rows = response.xpath("//div[@class='indexprolist_cont'][last()]//li")
        for row in rows:
            url = row.xpath(".//@href").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        rows = response.xpath("//div[@class='prolist_casinfor_img']")
        for row in rows:
            url = row.xpath(".//@href").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail
            )
        next_url = response.xpath("//a[contains(text(), '下一页')]/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        brand = self.name
        parent = response.xpath("//div[@class='position']//a[last()]/text()").get()
        cat_no = response.xpath("//td[contains(text(), '产品编号：')]//following-sibling::td/text()").get()
        cas = response.xpath("//td[contains(text(), 'CAS号：')]//following-sibling::td/text()").get()
        mf = ''.join(response.xpath("//td[text()='分子式：']/following-sibling::td[1]//text()").getall())
        mw = response.xpath("//td[contains(text(), '分子量：')]//following-sibling::td/text()").get()
        chs_name = response.xpath("//td[@align='center']//h1/text()").get()
        en_name = response.xpath("//td[@align='center']//h2/text()").get()
        img_url = response.xpath("//div[@class='proinforimg']//img/@src").get()
        value = response.xpath("//dd[@class='formcolumn-item-ct']//input[@id='ORDERINDEXID']/@value").get()
        d = {
            "brand": brand,
            "parent": parent,
            "cat_no": cat_no,
            "cas": cas,
            "mw": mw,
            "mf": mf,
            "en_name": en_name,
            "chs_name": chs_name,
            "prd_url": response.url,
            "img_url": img_url,
        }

        yield scrapy.FormRequest(
            url="http://www.herbpurify.com/ajaxpro/Web960.Web.index,Web960.Web.ashx",
            method='POST',
            body=json.dumps({"pd_id": value}),
            meta={
                'product': d,
            },
            callback=self.parse_package,
            headers={'x-ajaxpro-method': 'LoadGoods'}
        )

    def parse_package(self, response):
        d = response.meta.get('product', {})
        j_obj = json.loads(response.text.strip(';/*'))
        ret = json.loads(j_obj['ObjResult'])
        if ret:
            packages, = ret.values()
            for package in packages:
                price = package["Goods_Price"]
                if price == 0.0:
                    price = None
                package_info = json.loads(package["Goods_info"]).get('goodsinfo')
                package = package_info['packaging']
                purity = package_info['purity']

                dd = {
                    "brand": self.name,
                    "cat_no": d["cat_no"],
                    "currency": 'RMB',
                    "price": price,
                    "package": package
                }
                d['purity'] = purity
                yield RawData(**d)
                yield ProductPackage(**dd)
