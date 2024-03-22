import json
from hashlib import md5
from time import time
from urllib.parse import urlencode, parse_qsl, urlparse

from scrapy.http import JsonRequest

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


# Blocked by captcha
class MacklinSpider(BaseSpider):
    name = "macklin"
    brand = "麦克林"
    products_url = "https://api.macklin.cn/api/list/category_goods"
    catalog_url = "https://api.macklin.cn/api/index/header"
    package_url = "https://api.macklin.cn/api/product/list"

    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
    }

    @staticmethod
    def _get_sign(l, d):
        salt = "ndksyr9834@#$32ndsfu"
        return md5(f"{urlencode(l)}&salt={salt}".lower().encode()).hexdigest() \
               + md5(f"{urlencode(d)}&salt={salt}".lower().encode()).hexdigest()

    def make_request(self, url, params: dict = None, **kwargs):
        if params is None:
            params = {}
        t = time()
        l = {
            "x-agent": "web",
            "x-device-id": "3E4EA6360886A0CF",
            "x-language": "cn",
            "x-timestamp": int(t),
        }
        d = dict(**params, timestamp=int(t * 10 ** 38))
        headers = {
            'sign': self._get_sign(l, d),
            **l
        }
        return JsonRequest(
            url=f"{url}?{urlencode(d)}",
            headers=headers,
            **kwargs
        )

    def _make_catalogs_request(self):
        return self.make_request(
            url=self.catalog_url,
            method='POST',
            callback=self.parse
        )

    def _make_products_request(self, _id: int, page: int = 1, per_page: int = 50, meta=None, **kwargs):
        if meta is None:
            meta = {}
        params = {
            "id": _id,
            "offset": per_page,
            "page": page,
        }
        return self.make_request(
            url=self.products_url,
            params=params,
            callback=self.parse_list,
            meta={"catalog_id": _id, **meta},
            **kwargs
        )

    def _make_package_request(self, cat_no: str, meta: dict = None, **kwargs):
        if meta is None:
            meta = {}
        return self.make_request(
            url=self.package_url,
            params={"code": cat_no},
            callback=self.parse_package,
            meta={"cat_no": cat_no, **meta},
            **kwargs
        )

    def start_requests(self):
        yield self._make_catalogs_request()

    def _iter_category_id(self, category_tree):
        for c in category_tree:
            if tree_id := c.get('tree_id'):
                yield tree_id, c.get('tree_name'), c.get('tree_en_name')
            if sub_tree := c.get('sub_category', []):
                yield from self._iter_category_id(sub_tree)

    def parse(self, response, **kwargs):
        j = json.loads(response.text)
        if not (data := j.get('data', {}).get('category_nav_tree', [])):
            return
        for _id, cat_cn_name, cat_en_name in self._iter_category_id(data):
            yield self._make_products_request(
                _id=_id, meta={"catalog_id": _id, "parent": cat_cn_name}
            )

    def parse_list(self, response, **kwargs):
        catalog_id = response.meta.get("catalog_id")
        parent = response.meta.get("parent")
        j = json.loads(response.text)
        if j.get('code') != 200:
            query = urlparse(response.url).query
            params = dict(parse_qsl(query))
            yield self._make_products_request(
                _id=params['id'],
                per_page=params['offset'],
                page=params['page'],
                meta={**response.meta}
            )
            return
        if isinstance(j.get('data'), list):
            return
        if not (data := j.get('data', {}).get('goods_list')):
            return
        for product in (products := data.get('data', [])):
            attrs = {
                "melting_point": product.get('item_melting'),
                "boiling_point": product.get('item_boiling'),
                "flash_point": product.get('item_flash'),
                "density": product.get('item_density'),
            }
            cat_no = product.get('item_code')
            d = {
                "brand": self.brand,
                "cat_no": cat_no,
                "parent": parent,
                "en_name": product.get('item_en_name'),
                "chs_name": product.get('item_name'),
                "cas": product.get('chem_cas'),
                "mf": product.get('chem_mf'),
                "info2": product.get('item_en_storage'),
                "appearance": product.get('item_color'),
                "purity": product.get('item_specification'),
                "img_url": product.get('up_img'),
                "prd_url": f"http://www.macklin.cn/products/{cat_no}",
                "attrs": json.dumps(attrs),
            }
            yield RawData(**d)
            yield self._make_package_request(cat_no=cat_no)
        if not products:
            return
        yield self._make_products_request(
            _id=catalog_id,
            page=data.get('current_page') + 1,
            meta={**response.meta}
        )

    def parse_package(self, response):
        j = json.loads(response.text)
        if not (data := j.get('data', {}).get('list', [])):
            return
        cat_no = response.meta.get('cat_no')
        for pkg in data:
            dd = {
                "brand": self.brand,
                "cat_no": cat_no,
                "package": f'{pkg.get("product_pack")}{pkg.get("product_unit")}',
                "cost": pkg.get("product_sales_price"),
                "price": pkg.get("product_price"),
                "delivery_time": f"{pkg.get('delivery_days')} days",
                "stock_num": pkg.get('product_stock'),
                "purity": pkg.get('item_en_specification'),
                "currency": "RMB",
            }
            yield ProductPackage(**dd)
