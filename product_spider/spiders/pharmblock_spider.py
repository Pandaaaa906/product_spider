import json
import time
from base64 import b64decode
from hashlib import md5
from typing import List
from urllib.parse import urlencode, urlsplit

from Crypto.Cipher import DES
from Crypto.Util.Padding import unpad
from scrapy import Request
from scrapy.http import JsonRequest

from product_spider.items import RawData, ProductPackage, RawSupplierQuotation
from product_spider.utils.spider_mixin import BaseSpider


class PharmBlockSpider(BaseSpider):
    name = "pharmblock"
    base_url = "https://product.pharmablock.com/"
    brand = '南京药石'
    category_url = "https://product.pharmablock.com/cnApi/api/base/v1/productCategoryPath"
    product_url = "https://product.pharmablock.com/cnApi/api/base/v1/product"
    package_url = "https://product.pharmablock.com/cnApi/api/base/v1/productPrice"
    encrypt_key = b"pb!@S@#@"

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'RETRY_HTTP_CODES': [503, 403, 504],
        'RETRY_TIMES': 10,

        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'CONCURRENT_REQUESTS_PER_IP': 8,
    }

    def is_proxy_invalid(self, request, response):
        proxy = request.meta.get('proxy')
        if response.status in {503, 403, 504}:
            self.logger.warning(f'status code:{response.status}, {request.url}, using proxy {proxy}')
            return True
        return False

    def make_products_request(self, page=1, category_id='', **kwargs):
        t = int(time.time() * 1000)
        params = {"t": t, "sign": self.get_sign(self.product_url, t)}
        d = {
            "currentPage": page,
            "pageSize": 50,
            "filter": {
                "categoryId": category_id,
                "searchType": 0,
                "content": "",
                "smiles": "",
                "chirality": -1,
                "stock": -1,
                "clogp": None,
                "weight": None,
                "hbd": None,
                "hba": None,
                "group": [],
                "subgroup": [],
                "similarity": 0,
                "isNewProduct": -1,
                "isFeatureProduct": -1
            }
        }
        return JsonRequest(
            url=f"{self.product_url}?{urlencode(params)}",
            data=d,
            **kwargs
        )

    def make_product_request(self, key: str, **kwargs):
        t = int(time.time() * 1000)
        params = {
            "t": t,
            "sign": self.get_sign(self.product_url, t),
            "key": key,
            "from": "",
        }
        return Request(
            url=f"{self.product_url}?{urlencode(params)}",
            **kwargs
        )

    def make_package_request(self, product_id, **kwargs):
        t = int(time.time() * 1000)
        params = {
            "t": t,
            "sign": self.get_sign(self.package_url, t),
            "productId": product_id,
        }
        return Request(
            url=f"{self.package_url}?{urlencode(params)}",
            **kwargs
        )

    def decrypt(self, encrypted, key=None, mode=DES.MODE_CBC, padding='pkcs7'):
        if not key:
            key = self.encrypt_key
        des = DES.new(key, mode, key)
        dec_data = des.decrypt(b64decode(encrypted))
        return unpad(dec_data, DES.block_size, style=padding).decode('u8')

    @staticmethod
    def get_sign(url, t, ):
        *_, e = str.split(urlsplit(url).path, "/", 2)
        return md5(f"/{e}{t}p(ha#rmab^@lo!ck@2023^%%*&(".encode()).hexdigest()

    def start_requests(self):
        for category_type in range(1, 6):
            t = int(time.time() * 1000)
            d = {
                "t": t,
                "categoryType": category_type,
                "sign": self.get_sign(self.category_url, t),
            }
            yield Request(
                url=f"{self.category_url}?{urlencode(d)}",
                method='POST',
                callback=self.parse
            )

    def _iter_end_category(self, obj: List[dict]):
        for category in obj:
            children = category.get('items', [])
            if children:
                yield from self._iter_end_category(children)
            else:
                yield category

    def parse(self, response, **kwargs):
        j_obj = json.loads(response.text)
        for category in self._iter_end_category(j_obj["data"]):
            category_id = category.get('categoryId')
            yield self.make_products_request(
                page=1, category_id=category_id, callback=self.parse_list,
                meta={'cur_page': 1, 'category_id': category_id,
                      'parent': category.get('categoryNameEn'), 'parent_cn': category.get('categoryNameCn')}
            )

    def parse_list(self, response):
        j_obj = json.loads(response.text)
        page = (cur_page := response.meta.get('cur_page', 0)) + 1
        category_id = response.meta.get('category_id')
        if not (data := j_obj.get('data')):
            return
        for row in data.get('list', []):
            cat_no = row.get('productCode')
            yield Request(
                url=f"https://product.pharmablock.com/cn/product/{cat_no}",
                callback=self.parse_nothing,
                meta={**response.meta, 'cat_no': cat_no},
            )
        total = data.get('total', 0)
        if total < cur_page * 50:
            return
        yield self.make_products_request(
            page=page, category_id=category_id, callback=self.parse_list,
            meta={**response.meta, 'cur_page': page, 'category_id': category_id}
        )

    def parse_nothing(self, response):
        """
        为了不重复获取产品信息
        :param response:
        :return:
        """
        cat_no = response.meta.get('cat_no')
        yield self.make_product_request(
            key=cat_no,
            callback=self.parse_detail,
            meta=response.meta,
        )

    def parse_detail(self, response):
        j_obj = json.loads(response.text)
        prd = j_obj.get('data')
        if not prd:
            return
        attrs = {
            "boiling_point": prd.get("boilingPoint"),
            "flash_point": prd.get("flashingPoint"),
            "coa_url": prd.get("coaUrl"),
            "msds_url": prd.get("sdsUrl"),
            "nmr_url": prd.get("nmrUrl"),
            "density": prd.get("density"),
            "ghs_code": prd.get("ghsCode"),
            "category": ';'.join(filter(lambda x: x, map(lambda x: x.get('categoryNameCN'), prd.get('bbCategoryList', [])))),
        }
        cas = prd.get("casNum")
        img_url = None
        if cas:
            *_, t = cas.rsplit('-', 1)
            img_url = f"https://productapi.pharmablock.com/doc/product/images/svg/{t}/{cas}.svg"
        d = {
            "brand": self.brand,
            "cat_no": prd.get("productCode"),
            "parent": ';'.join(map(lambda x: x['categoryNameEN'], prd.get('bbCategoryList', []))),
            "en_name": prd.get("nameEN"),
            "chs_name": prd.get("nameCN"),
            "cas": cas,
            "mw": prd.get("molWeight"),
            "mf": prd.get("molFormula"),
            "info2": prd.get("storageCondition"),
            "smiles": prd.get("smiles"),
            "mdl": prd.get("mdlNum"),
            "appearance": prd.get("appearance"),
            "stock_info": (m := prd.get("stockCN")) and self.decrypt(m),
            "prd_url": f"https://product.pharmablock.com/cn/product/{prd.get('productCode')}",
            "img_url": img_url,
            "attrs": json.dumps(attrs)
        }
        product_id = prd.get("productId")
        yield RawData(**d)

        yield self.make_package_request(
            product_id=product_id,
            callback=self.parse_package,
            meta={"product": d, **response.meta}
        )

    def parse_package(self, response):
        j_obj = json.loads(response.text)
        data = j_obj.get('data')
        if not data:
            return
        rows = data.get('list')
        prd = response.meta['product']
        try:
            stock_num = float(prd['stock_info'])
        except Exception:
            stock_num = 0
        for row in rows:
            cn_price = row.get('listPriceCNAlias')
            us_price = row.get('listPriceUSAlias')
            attrs = {
                "usd_price": us_price and self.decrypt(us_price),
            }
            pkg_stock = row.get('package', 0) or 0

            dd = {
                'brand': self.brand,
                'cat_no': prd['cat_no'],
                'package': f"{row.get('packSize')}{row.get('packUnit')}",
                'cost': cn_price and self.decrypt(cn_price),
                'price': cn_price and self.decrypt(cn_price),
                'stock_num': pkg_stock and int(stock_num // pkg_stock),
                'currency': 'RMB',
                'attrs': json.dumps(attrs),
            }
            ddd = {
                "platform": self.name,
                "source_id": f"{self.name}_{dd['cat_no']}",
                "vendor": self.name,
                "brand": self.name,
                "cat_no": dd['cat_no'],
                "package": dd['package'],
                "discount_price": dd['cost'],
                "price": dd['cost'],
                "currency": dd["currency"],
                "stock_num": dd["stock_num"],
                "cas": prd["cas"],
            }
            yield ProductPackage(**dd)
            yield RawSupplierQuotation(**ddd)
