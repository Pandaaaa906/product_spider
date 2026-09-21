import json
import re
from urllib.parse import urlencode, urljoin

import scrapy

from product_spider.items import (
    ProductPackage,
    RawData,
    RawSupplierQuotation,
    SupplierProduct,
)
from product_spider.utils.items_translate import (
    product_package_to_raw_supplier_quotation,
    rawdata_to_supplier_product,
)
from product_spider.utils.spider_mixin import BaseSpider

BASE_URL = "https://sunwaypharm.cn"
CATEGORIES = list(range(570, 619))  # ponytail: 首页旧分类 437/446/449/468/471/480/483/548 均 404，已剔除


def is_sunwaypharm(brand: str):
    return brand in {"相辉", "sunwaypharm"}


class SunwaypharmSpider(BaseSpider):
    """上海相辉医药 https://sunwaypharm.cn/"""

    name = "sunwaypharm"
    allowed_domains = ["sunwaypharm.cn"]
    start_urls = [f"{BASE_URL}/products/{c}/" for c in CATEGORIES]
    other_brands = set()

    def parse(self, response):
        for url in response.xpath("//a[@class='name']/@href").getall():
            m = re.search(r"sunwaypharm\.cn/product/(\d+)\.html", url)
            if not m:
                continue
            yield scrapy.Request(
                url=urljoin(BASE_URL, url),
                callback=self.parse_detail,
                meta={"pd_id": m.group(1)},
            )
        next_page = response.xpath(
            '//ul[contains(@class, "pagination")]/li[@class="active"]'
            "/following-sibling::li[1]/a/text()"
        ).get()
        if next_page and next_page.strip().isdigit():
            yield scrapy.Request(url=self._page_url(response.url, next_page.strip()), callback=self.parse)

    @staticmethod
    def _page_url(url: str, page: str) -> str:
        base = url.split("?")[0]
        if base.endswith("search.do"):
            return f"{base}?a=is&psize=18&page={page}"
        if not base.endswith(".html"):
            base = base.rstrip("/") + ".html"
        return f"{base}?page={page}&prop_filter=%7b%7d"

    def parse_detail(self, response):
        pd_id = response.meta["pd_id"]

        def cell(label: str):
            v = "".join(
                response.xpath(
                    f"//th[contains(text(), '{label}')]/following-sibling::td[1]//text()"
                ).getall()
            ).strip()
            return v or None

        parent = response.xpath("//ol[@class='breadcrumb']/li[last()]/a/text()").get()
        if parent == "产品分类":
            parent = None
        style = response.xpath("//div[contains(@class, 'image')]//div[@class='img']/@style").get("")
        m = re.search(r"url\((//[^)]+)\)", style)
        img_url = f"https:{m.group(1)}" if m and "noimage" not in m.group(1) else None
        d = {
            "chs_name": cell("中文名称"),
            "en_name": cell("英文名称"),
            "cas": cell("CAS"),
            "mf": cell("分子式"),
            "mw": cell("分子量"),
            "parent": parent,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield scrapy.Request(
            url=f"{BASE_URL}/index.aspx?a=ajaxpro_ajax&method=LoadGoods",
            method="POST",
            body=urlencode({"pd_id": pd_id}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            callback=self.parse_package,
            meta={"product": d, "pd_id": pd_id},
        )

    def parse_package(self, response):
        d = response.meta["product"]
        pd_id = response.meta["pd_id"]
        try:
            obj = json.loads(response.json()["ObjResult"])
        except (ValueError, TypeError, KeyError):
            self.logger.warning(f"LoadGoods 响应解析失败: {pd_id}")
            return
        for result in obj.get(f"p_{pd_id}") or []:
            for inv in result.get("Inventores") or []:
                goods_info = json.loads(inv.get("Goods_Info") or "{}").get("goodsinfo", {})
                brand = goods_info.get("brand")
                if brand == "促销无折扣":
                    brand = self.name
                cat_no = (inv.get("Goods_no") or "").rsplit("-", 1)[0] or None
                price = inv.get("Price")
                stock_num = inv.get("Amount", 0)
                if isinstance(stock_num, float):
                    stock_num = int(stock_num)
                delivery_time = goods_info.get("goodshuoqi") or None
                if not delivery_time and isinstance(stock_num, int) and stock_num > 0:
                    delivery_time = "现货"

                d["brand"] = brand
                d["cat_no"] = cat_no
                d["purity"] = goods_info.get("purity")
                dd = {
                    "brand": brand,
                    "cat_no": cat_no,
                    "cost": price,
                    "currency": "CNY",
                    "package": goods_info.get("packaging"),
                    "stock_num": stock_num,
                    "delivery_time": delivery_time,
                }
                yield SupplierProduct(**rawdata_to_supplier_product(d, self.name, self.name))
                if is_sunwaypharm(brand):
                    yield RawData(**d)
                    yield ProductPackage(**dd)
                else:
                    self.other_brands.add(brand)
                if dd["cost"]:
                    yield RawSupplierQuotation(
                        **product_package_to_raw_supplier_quotation(d, dd, self.name, self.name)
                    )

    def closed(self, reason):
        self.logger.info(f"其他品牌: {self.other_brands}")

    def keyword_search(self, keyword: str, search_params: dict = None):
        yield scrapy.Request(
            url=f"{BASE_URL}/search.do?a=is&psize=18&kw={keyword}&searchtmp=",
            callback=self.parse,
        )
