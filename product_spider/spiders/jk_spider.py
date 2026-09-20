import json
import re
from urllib.parse import urlencode, quote

from jsonpath_ng import parse
from scrapy import Request

from product_spider.items import (
    RawData,
    SupplierProduct,
    ProductPackage,
    RawSupplierQuotation,
)
from product_spider.utils.functions import dumps
from product_spider.utils.items_translate import (
    rawdata_to_supplier_product,
    product_package_to_raw_supplier_quotation,
)
from product_spider.utils.spider_mixin import BaseSpider

jk_brands = {"jk"}
brand_mapping = {
    "J&K Scientific": "jk",
    "J&K": "jk",
    "J&K-Abel": "jk",
    "Agilent(安捷伦)": "agilent",
    "Dr. Ehrenstorfer": "dre",
    "EDQM(EP)": "ep",
    "Cambridge Isotope Laboratories（CIL）": "cil",
    "Life Chemicals": "life_chemicals",
    "Rieke Metals": "rieke_metals",
    "Key Organics": "key_organics",
    "Alfa Aesar": "alfa",
    "Polymer Source": "polymer_source",
    "Chem Service": "chemservice",
    "Acanthus Research": "acanthus",
    "NATIONAL INSTITUTE OF STANDARDS AND TECHNOLOGY": "nist",
    "Nu-Chek": "nuchek",
    "Sigma-Aldrich": "sigma",
    "Spectrum Quality Standards": "sqs",
    "Taiwan Algal Science(台湾藻研)": "tas",
}


def parse_brand(brand: str):
    if not brand:
        return
    if brand not in brand_mapping:
        return brand.lower()
    return brand_mapping[brand]


class JkPrdSpider(BaseSpider):
    name = "jk"
    allowed_domains = ["jkchemical.com"]
    base_url = "http://www.jkchemical.com"
    home_url = "https://www.jkchemical.com/"
    seed_catalog_id = 1013  # 任意存在的分类，其 JSON 内嵌完整目录树
    product_url = (
        "https://www.jkchemical.com/_next/data/{build_id}/search/{catalog}.json"
    )
    catalog_url = "https://www.jkchemical.com/_next/data/{build_id}/product-catalog/{catalog_id}.json"

    custom_settings = {
        "PROXY_POOL_REFRESH_STATUS_CODES": [503, 504, 429],
        "RETRY_TIMES": 10,
        "CONCURRENT_REQUESTS": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "CONCURRENT_REQUESTS_PER_IP": 2,
        "DOWNLOAD_DELAY": 2,
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) "
            "AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8",
        },
    }

    def _start_requests(self):
        yield Request(self.home_url, callback=self.parse_home)

    def parse_home(self, response):
        """从首页提取 Next.js buildId，再请求目录树 JSON"""
        m = re.search(r'"buildId":"([^"]+)"', response.text)
        if not m:
            raise ValueError("无法从首页提取 buildId，网站可能再次改版")
        self.build_id = m.group(1)
        yield Request(
            self.catalog_url.format(
                build_id=self.build_id, catalog_id=self.seed_catalog_id
            ),
            callback=self.parse_catalogs,
        )

    def parse_catalogs(self, response):
        """目录树内嵌在任意 catalog JSON 的 rootProductCatalogs，遍历叶子节点"""
        obj = response.json()
        seen = set()

        def walk(node):
            catalog_id = node.get("id")
            children = node.get("children") or []
            if node.get("isLeaf") or not children:
                if catalog_id not in seen:
                    seen.add(catalog_id)
                    yield self.make_request(catalog_id, node.get("name"))
            else:
                for child in children:
                    yield from walk(child)

        for m in parse("$.pageProps.rootProductCatalogs[*]").find(obj):
            yield from walk(m.value)

    def make_request(self, catalog_id, catalog_name, page: int = 1):
        d = {
            "key": catalog_name,
            "type": 3,
            "page": page,
            "categoryId": catalog_id,
        }
        return Request(
            f"{self.product_url.format(build_id=self.build_id, catalog=quote(catalog_name))}?{urlencode(d)}",
            meta={"page": page, "catalog_id": catalog_id, "catalog_name": catalog_name},
            callback=self.parse_list,
        )

    def parse_list(self, response):
        obj = response.json()
        page_props = obj.get("pageProps") or {}
        prds = page_props.get("productlist") or []
        for prd in prds:
            mf = prd.get("molecularFomula")
            cas = prd.get("cas")
            d = {
                "brand": parse_brand(prd.get("brandName")),
                "cat_no": prd.get("origin"),
                "en_name": prd.get("englishName"),
                "chs_name": prd.get("chineseName"),
                "cas": None if cas == "0" else cas,
                "purity": prd.get("purity"),
                "mf": mf.replace(" ", "") if mf else None,
                "mw": prd.get("molecularWeight"),
                "img_url": (img_url_id := prd.get("imageUrl"))
                and f"https://static.jkchemical.com/Structure/{img_url_id[:3]}/{img_url_id}.png",
                "prd_url": (tmp := prd.get("id"))
                and f"https://www.jkchemical.com/product/{tmp}",
            }

            yield SupplierProduct(
                **rawdata_to_supplier_product(
                    d,
                    platform="jk",
                    vendor="jk",
                )
            )
            if not (prd_url := d["prd_url"]):
                continue
            yield Request(prd_url, callback=self.parse_package, meta={"prd": d})

        total = page_props.get("total") or 0
        page_index = page_props.get("pageIndex") or response.meta.get("page", 1)
        page_size = page_props.get("pageSize") or 20
        if page_index * page_size < total:
            yield self.make_request(
                response.meta.get("catalog_id"),
                response.meta.get("catalog_name"),
                page_index + 1,
            )

    def parse_package(self, response):
        d = response.meta.get("prd", {})
        raw_json = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        j_obj = json.loads(raw_json) if raw_json else None

        categories = []
        if j_obj:
            categories = [
                "__".join(node.get("name") or "" for node in m.value)
                for m in parse("$.props.pageProps.product.productCrumbs[*]").find(j_obj)
            ]
        attrs = {}
        if categories:
            attrs["categories"] = categories
            d["parent"] = categories[0]
        d["attrs"] = dumps(attrs)
        # JSON 缺失时仍保留产品记录（无分类）
        if d.get("brand") in jk_brands:
            yield RawData(**d)
        if not j_obj:
            return
        for m in parse("$.props.pageProps.product.packages[*]").find(j_obj):
            pkg = m.value
            package = f"{pkg.get('radioY')}{pkg.get('unit')}"
            stock_num = 0
            if l_inv := pkg.get("inventories"):
                for inv in l_inv:
                    stock_num += inv.get("quantity", 0)
            delivery_time = "现货" if stock_num > 0 else None

            dd = {
                "brand": d.get("brand"),
                "cat_no": d.get("cat_no"),
                "package": package,
                "cost": pkg.get("salesPrice"),
                "price": pkg.get("price"),
                "currency": pkg.get("currency"),
                "stock_num": stock_num,
                "delivery_time": delivery_time,
                "attrs": dumps({"inventories": pkg.get("inventories")}),
            }
            if dd["brand"] in jk_brands:
                yield ProductPackage(**dd)
            if dd["cost"]:
                yield RawSupplierQuotation(
                    **product_package_to_raw_supplier_quotation(
                        d,
                        dd,
                        self.name,
                        self.name,
                    )
                )
