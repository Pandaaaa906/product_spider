import json
import os
from urllib.parse import urljoin
import re

from product_spider.items import RawData, ProductPackage

if os.name == 'nt':
    import subprocess
    from functools import partial
    subprocess.Popen = partial(subprocess.Popen, encoding="utf-8")

import execjs
import scrapy

from product_spider.utils.spider_mixin import BaseSpider


def is_biopurify(brand: str):
    if not brand:
        return False
    elif brand.lower() == 'biopurify':
        return True


class BiopurifySpider(BaseSpider):
    """普瑞法Biopurify"""
    name = "biopurify"
    allow_domain = ["biopurify.cn"]
    start_urls = ["http://www.biopurify.cn/products/1035.html"]
    base_url = "http://www.biopurify.cn/"
    other_brands = set()

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS_PER_IP': 2,
    }

    def parse(self, response, **kwargs):
        rows = response.xpath("//div[@class='cpfl_cont']//li")
        for row in rows:
            url = urljoin(self.base_url, row.xpath(".//a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        rows = response.xpath("//div[@class='pro_casinfor']")
        for row in rows:
            url = row.xpath(".//div[@class='prolist_casinforimg']/a/@href").get()
            value = row.xpath(".//td[@class='blue']/input[@name='productitem']/@value").get()
            yield scrapy.Request(
                url=url,
                meta={"value": value},
                callback=self.parse_detail
            )
        next_url = urljoin(self.base_url, response.xpath("//a[contains(text(), '下一页')]//@href").get())
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        value = response.meta.get("value", None)
        cat_no = response.xpath("//td[contains(text(), '产品编号：')]//following-sibling::td//text()").get()
        cas = response.xpath("//h2[@class='proennametitle']//text()").get()
        cas = (m := re.search(r'\d+-\d{2}-\d\b', cas)) and m.group()
        en_name = response.xpath("//td[contains(text(), '英文名称：')]//following-sibling::td//text()").get()
        mw = response.xpath("//td[contains(text(), '分 子 量：')]/following-sibling::td//text()").get()
        mf = ''.join(response.xpath("//td[contains(text(), '分 子 式：')]/following-sibling::td//text()").getall())
        img_url = response.xpath("//div[@class='proinfimage']//img/@src").get()
        parent = response.xpath("//div[@class='width mar right_tit']//a[last()]//text()").get()

        d = {
            "cat_no": cat_no,
            "cas": cas,
            "en_name": en_name,
            "mw": mw,
            "mf": mf,
            "img_url": img_url,
            "prd_url": response.url,
            "parent": parent,
        }
        yield scrapy.FormRequest(
            url="http://www.biopurify.cn/ajaxpro/Web960.Web.index,Web960.Web.ashx",
            method='POST',
            body=json.dumps({"pd_id": value}),
            meta={
                'product': d,
            },
            callback=self.parse_package,
            headers={'x-ajaxpro-method': 'LoadGoods'}
        )

    def parse_package(self, response):
        d = response.meta.get("product", {})
        j_obj = execjs.eval(response.text.strip(';/*'))
        datas = j_obj['ObjResult']
        for data in datas:
            price = data["Goods_Price"]
            if price == 0:
                price = None
            cat_no = data["Goods_no"]
            package_info = json.loads(data["Goods_info"]).get("goodsinfo")
            package = package_info.get("packaging")
            purity = package_info.get("purity")
            brand = package_info.get("brand").lower()

            d["purity"] = purity
            d["brand"] = brand

            dd = {
                "cat_no": cat_no,
                "package": package,
                "cost": price,
                "brand": brand,
                "currency": "RMB",
            }
            if not is_biopurify(brand):
                self.other_brands.add(brand)
                # TODO yield SupplierProduct
                return
            yield RawData(**d)
            yield ProductPackage(**dd)

    def closed(self, reason):
        self.logger.info(f'其他品牌: {self.other_brands}')


