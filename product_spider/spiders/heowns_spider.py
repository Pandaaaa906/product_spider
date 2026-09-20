import json
from urllib.parse import urlencode

import scrapy
from product_spider.items import (
    RawData,
    ProductPackage,
    SupplierProduct,
    RawSupplierQuotation,
)
from product_spider.utils.items_translate import (
    product_package_to_raw_supplier_quotation,
    rawdata_to_supplier_product,
)
from product_spider.utils.spider_mixin import BaseSpider


def is_heowns(brand: str):
    return brand == "希恩思"


class HeownsSpider(BaseSpider):
    """希恩思"""

    """其他品牌: {'TCI', 'Solarbio', '南京飞虎', '福来兹', '进口分装', 'CIL'}"""
    name = "heowns"
    start_urls = ["http://www.heowns.com/products/258.html"]
    other_brands = set()

    def start_requests(self):
        yield scrapy.Request(
            "https://www.heowns.com/index.aspx?a=checkuserlogin",
            callback=self.parse_cookies,
        )

    def parse_cookies(self, response):
        yield from super().start_requests()

    def parse(self, response, **kwargs):
        rows = response.xpath(
            "//div[@class='kj-product-item']//div[@class='kj-proitembox']"
        )
        for row in rows:
            url = row.xpath(
                ".//div[@class='col-lg-3  col-md-3  col-xs-4  col-sm-4 kj-product-list']/a/@href"
            ).get()
            pd_id = row.xpath(".//input[@name='productitem']/@value").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={
                    "pd_id": pd_id,
                },
            )
        # 翻页
        next_page = response.xpath(
            '//ul[contains(@class, "pagination")]/li[@class="active"]/following-sibling::li[1]/a/text()'
        ).get()
        if next_page:
            yield scrapy.Request(
                url=f"http://www.heowns.com/products/258.html?page={next_page}&prop_filter=%7b%7d",
                callback=self.parse,
            )

    def parse_detail(self, response):
        pd_id = response.meta.get("pd_id")
        chs_name = response.xpath(
            "//th[contains(text(), '中文名称:')]/following-sibling::td/text()"
        ).get()
        en_name = response.xpath(
            "//th[contains(text(), '英文名称:')]/following-sibling::td/text()"
        ).get()
        cas = response.xpath(
            "//th[contains(text(), 'CAS.No:')]/following-sibling::td/text()"
        ).get()
        mf = "".join(
            response.xpath(
                "//th[contains(text(), '分子式:')]/following-sibling::td//text()"
            ).getall()
        )
        mw = response.xpath(
            "//th[contains(text(), '分子量:')]/following-sibling::td/text()"
        ).get()
        parent = response.xpath("//ol[@class='breadcrumb']/li[last()]/a/text()").get()
        if parent == "产品分类":
            parent = None
        img_url = response.xpath("//div[@class='item active']/img/@src").get()
        d = {
            "chs_name": chs_name,
            "en_name": en_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "parent": parent,
            "img_url": img_url,
            "prd_url": response.url,
        }
        query = {
            "a": "loadgoodbyajax",
            "pd_id": pd_id,
        }
        yield scrapy.Request(
            url=f"http://www.heowns.com/index.aspx?{urlencode(query)}",
            callback=self.parse_package,
            method="POST",
            meta={
                "product": d,
                "pd_id": pd_id,
            },
        )

    def parse_package(self, response):
        d = response.meta.get("product")
        pd_id = response.meta.get("pd_id")
        j_obj = json.loads(response.text)
        results = json.loads(j_obj["value"].get("ObjResult")).get(f"p_{pd_id}")
        for result in results:
            package_info = json.loads(result.get("Goods_info")).get("goodsinfo")
            package = package_info.get("packaging")
            purity = package_info.get("purity")
            brand = package_info.get("brand")
            if brand == "促销无折扣":
                brand = "heowns"
            for i in result.get("Inventores"):
                cat_no = i.get("Goods_no")
                cat_no, *_ = cat_no.split("+")
                price = i.get("Price")

                stock_num = i.get("Amount", 0)
                delivery_time = None
                if isinstance(stock_num, float):
                    stock_num = int(stock_num)
                if isinstance(stock_num, int) and stock_num > 0:
                    delivery_time = "现货"

                d["brand"] = brand
                d["cat_no"] = cat_no
                d["purity"] = purity
                dd = {
                    "brand": brand,
                    "cat_no": cat_no,
                    "cost": price,
                    "currency": "CNY",
                    "package": package,
                    "stock_num": stock_num,
                    "delivery_time": delivery_time,
                }

                if is_heowns(brand):
                    yield RawData(**d)
                    yield ProductPackage(**dd)
                else:
                    self.other_brands.add(brand)
                yield SupplierProduct(
                    **rawdata_to_supplier_product(d, self.name, self.name)
                )
                if not dd["cost"]:
                    continue
                yield RawSupplierQuotation(
                    **product_package_to_raw_supplier_quotation(
                        d, dd, self.name, self.name
                    )
                )

    def closed(self, reason):
        self.logger.info(f"其他品牌: {self.other_brands}")
