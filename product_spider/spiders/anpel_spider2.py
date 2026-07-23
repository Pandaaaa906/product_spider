import json
import random
import re
import time
from hashlib import md5
from io import BytesIO
from itertools import product
from string import digits
from urllib.parse import urljoin, urlencode

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from fontTools.ttLib import TTFont
from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.items_translate import product_package_to_raw_supplier_quotation, rawdata_to_supplier_product
from product_spider.utils.jsonpath import jsonpath_query_nth, jsonpath_query_all
from product_spider.utils.spider_mixin import BaseSpider

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                  'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8'
}

default_brands = [
    {"brand_id": "ANPEL", "alt": "ANPEL"},
    # {"brand_id": "0281", "alt": "anpel-检科院"},
    # {"brand_id": "B0249", "alt": "Anpel-农科院质标所"},
    # {"brand_id": "402", "alt": "Anpel-国家粮食局"},
    {"brand_id": "CNW", "alt": "CNW"},
    {"brand_id": "安谱优选", "alt": "安谱优选"},
    {"brand_id": "上海安谱", "alt": "上海安谱"},
    # {"brand_id": "0181", "alt": "o2si"},
    {"brand_id": "安谱璀世", "alt": "安谱璀世"},
]

publicKey = (
    'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCeCDcnFrS7DIRbvZLHreVUzaMbAFy2DYmioxBK606urY4rVR8IgLgUhnyw2'
    '/GQ99pyr8lGtqPeOoapantw1XwEVyi74MDxs4UDL8j4OZR1Es7HVGOB0GwKWobdU9cm'
    '/1iDwGyouSmijxKyAePg6KsLNgbjDPYZRS11bYEuZ8/RLQIDAQAB/8008D6C4DB52407FA89761C10A391F21'
)
cmap_char = f'.{digits}'


def decrypt_font_name(hex_ciphertext: str, key: str = None) -> str:
    if key is None:
        key = "1678122asdasdasdasdasdasdasdasd345678"

    # 与JS一致
    if len(key) > 32:
        key = key[:32]
    elif len(key) < 32:
        key = key.ljust(32, "@")

    key_bytes = key.encode("utf-8")

    # Hex.parse()
    ciphertext = bytes.fromhex(hex_ciphertext)

    cipher = AES.new(key_bytes, AES.MODE_ECB)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)

    return plaintext.decode("utf-8")



# TODO 破解图片验证码
class AnpelSpider(BaseSpider):
    name = "anpel2"
    base_url = 'https://www.labsci.com.cn/'
    start_urls = [
        'https://www.labsci.com.cn/',
    ]

    custom_settings = {
        # "DOWNLOADER_MIDDLEWARES": {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        'PROXY_POOL_REFRESH_STATUS_CODES': [403],
        'RETRY_TIMES': 20,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        ),
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 5,
        'CONCURRENT_REQUESTS_PER_IP': 5,
    }
    _font_mapping = {}
    _font_code_mapping = {
        'otilde': '3',
        'odieresis': '2',
        'divide': '1',
        'oslash': '0',
        'ugrave': '.',
        'uacute': '9',
        'ucircumflex': '8',
        'udieresis': '7',
        'yacute': '6',
        'thorn': '5',
        'ydieresis': '4',

        'ebreve': '3',
        'Edotaccent': '2',
        'edotaccent': '1',
        'Eogonek': '0',
        'eogonek': '.',
        'Ecaron': '9',
        'ecaron': '8',
        'Gcircumflex': '7',
        'gcircumflex': '6',
        'Gbreve': '5',
        'gbreve': '4',

        'agrave': '6',
        'aacute': '7',
        'acircumflex': '8',
        'atilde': '9',
        'adieresis': '.',
        'aring': '0',
        'ae': '1',
        'ccedilla': '2',
        'egrave': '3',
        'eacute': '4',
        'ecircumflex': '5',
    }
    _font_blacklist = set()

    def __init__(self, brands=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if brands is None:
            self.brands = default_brands
        else:
            brands = json.loads(brands)
            self.brands = brands

    def is_proxy_invalid(self, request, response):
        proxy = request.meta.get('proxy')
        if response.status in {403, }:
            self.logger.warning(f'status code:{response.status}, {request.url}')
            return True
        if "VerifyIP" in response.url:
            detected_ip = response.xpath('//span[@id="lblIP"]/text()').get()
            self.logger.warning(f"IP being detected {detected_ip}, using proxy {proxy}")
            return True
        for c in ('GetBrandWahStock', 'GetStandardWahStock'):
            if c not in response.url:
                continue
            if not response.text.startswith('{'):
                return True
        return False

    def _get_headers(self):
        ts = int(time.time() * 1000)
        return {
            "Timestamp": f"{ts}",
            "Selectkey": md5(f"{ts}{publicKey}".encode()).hexdigest(),

        }

    def make_request(
            self, brand_id: str = '', brand_name: str = '', keyword: str = '',
            per_page: int = 28, page: int = 0,
            callback=None, meta: dict = None
    ):
        if meta is None:
            meta = {}
        d = {
            "Keyword": keyword,
            "SkipCount": page * per_page,
            "MaxResultCount": per_page,
            "BrandId": brand_id,
            'LabelValues': '[]',
            "BrandName": brand_name,
            "totalQty": '',
            "SortType": 4,
            "CusId": '',
            "TypeTwoValue": '-1',
            "TypeThreesValue": '',
        }
        _url = f"https://star.labsci.com.cn/Elasticsearch/GetLabelNewStockQuanBuSeach?{urlencode(d)}"
        return Request(
            _url,
            callback=callback,
            headers=self._get_headers(),
            meta={
                "brand_id": brand_id,
                "brand_name": brand_name,
                "per_page": per_page,
                "keyword": keyword,
                "page": page + 1,
                **meta
            },
            errback=self.parse
        )

    def make_search_request(
            self,
            brand_name: str = '', keyword: str = '',
            per_page: int = 28, page: int = 0,
            callback=None, meta: dict = None
    ):
        if meta is None:
            meta = {}
        d = {
            "Keyword": keyword,
            "SkipCount": per_page * page,
            "MaxResultCount": per_page,
            "ClassId": "",
            "ClassName": "全部",
            "BrandId": "",
            "BrandName": brand_name,
            "TotalQty": "全部",
            "PriceType": 0,
            "SortType": 4,
            "OnlyStandardVariety": True,
            "ExistTradingRecord": False,
            "CusId": "",
            "nocache": 1
        }
        return Request(
            f"https://star.labsci.com.cn/Elasticsearch/GetStandardWahStock?{urlencode(d)}",
            callback=callback,
            headers=self._get_headers(),
            meta={
                "brand_name": brand_name,
                "per_page": per_page,
                "keyword": keyword,
                "page": page + 1,
                **meta
            }
        )

    def start_requests(self):
        # yield self.make_search_request('0032', callback=self.parse)

        for item in self.brands:
            brand_id = item.get('brand_id')
            brand_name = item.get('alt')
            if not brand_id:
                continue
            for a, b, c in product(digits, repeat=3):
                yield self.make_request(brand_id=brand_id, brand_name=brand_name, keyword=f"{a}{b}-{c}",
                                        callback=self.parse)

    def parse(self, response, **kwargs):
        j = response.json()
        font_name = jsonpath_query_nth(j, '$.data.fontPath')
        if not font_name:
            self.logger.warning(f"fontPath为空:{response.url}")
        else:
            font_name = decrypt_font_name(font_name)
        rows = jsonpath_query_all(j, '$.data.items[*]')
        for row in rows:
            img = jsonpath_query_nth(row, '@.photoPath')
            prd_id = jsonpath_query_nth(row, '@.seqNoKey')
            cas = jsonpath_query_nth(row, '@.casNo')
            if cas:
                cas = re.sub(r'[\[\]]', '', cas)
            d = {
                "brand": jsonpath_query_nth(row, '@.brandName').lower(),
                "cat_no": jsonpath_query_nth(row, '@.stkNo'),
                "chs_name": jsonpath_query_nth(row, '@.stkName'),
                "en_name": jsonpath_query_nth(row, '@.stkNameEng'),
                "cas": cas,
                "purity": jsonpath_query_nth(row, '@.spec'),
                "stock_info": jsonpath_query_nth(row, '@.totalQtyMeo'),

                "img_url": img and urljoin('https://dianzi.labsci.com.cn/UpFile/Brand', img.replace('\\', '/')),
                "prd_url": f"https://www.labsci.com.cn/products?id={prd_id}",
            }
            price = jsonpath_query_nth(row, '@.priceStr')
            try:
                price = self.decode_price(price, font_name)
            except ValueError as e:
                self.logger.error(e)
                new_request = response.request.copy()
                new_request.dont_filter = True
                for k, v in self._get_headers().items():
                    new_request.headers[k] = v
                yield new_request
                break
            price = price if price != '0.00' else None
            cost = self.decode_price(jsonpath_query_nth(row, '@.price2Str'), font_name)
            cost = cost if cost != '0.00' else price
            dd = {
                "brand": d["brand"],
                "cat_no": d["cat_no"],
                "package": jsonpath_query_nth(row, '@.spec') or '',
                "currency": "RMB",
                "cost": cost,
                "price": price,
                "delivery_time": jsonpath_query_nth(row, '@.totalQtyMeo'),
            }
            if d["brand"] == 'anpel':
                yield RawData(**d)
                yield ProductPackage(**dd)
            pass

            ddd = rawdata_to_supplier_product(d, self.name, self.name)
            yield SupplierProduct(**ddd)
            if dd.get("cost"):
                dddd = product_package_to_raw_supplier_quotation(d, dd, self.name, self.name)
                yield RawSupplierQuotation(**dddd)

        per_page = response.meta.get("per_page", 0)
        page = response.meta.get("page", 0)
        keyword = response.meta.get("keyword", '')
        total = jsonpath_query_nth(j, '$.data.totalCount') or 0
        if total < page * per_page:
            return
        brand_id = response.meta.get("brand_id", "")
        # brand_name = response.meta.get("brand_name", "")
        # yield self.make_search_request(
        #     brand_name=brand_name, keyword=keyword, per_page=per_page, page=page,
        #     callback=self.parse)
        yield self.make_request(
            brand_id=brand_id, keyword=keyword, per_page=per_page, page=page,
            callback=self.parse)

    def _get_cmap(self, font_name, max_try=3):
        tried = 0
        r = None
        while tried < max_try:
            try:
                r = requests.get(urljoin("https://www.labsci.com.cn/", font_name), headers=headers)
            except Exception as e:
                self.logger.warn(e)
            if r and r.status_code == 200:
                break
        if not r:
            raise ValueError(f"cant get font_map of: {font_name}")
        font = TTFont(BytesIO(r.content))
        cmap = font.getBestCmap()
        return cmap

    def decode_price(self, value: str, font_name):
        if not isinstance(value, str):
            return value
        if font_name in self._font_blacklist:
            raise ValueError(f"blacklist font: {font_name}")
        if font_name not in self._font_mapping:
            *_, dot, zero1, zero2 = value
            if zero1 != zero2:
                raise ValueError(f"value not ends with double zeros, {value}")
            cmap = self._get_cmap(font_name)
            keys = {k: idx for idx, k in enumerate(cmap.keys())}  # 如果对方都是用字节序排，其实可以不用这样写
            idx_dot = keys[ord(dot)]
            idx_zero1 = keys[ord(zero1)]
            # 9 = len(cmap) - 2
            if abs(idx_dot - idx_zero1) % 9 != 1:
                self._font_blacklist.add(font_name)
                raise ValueError(f"dot and zero should be neighbour: {font_name=}, {dot=}, {zero1=}, {cmap=}")
            min_cmap = min(cmap.keys())
            if (idx_dot < idx_zero1 and not (idx_dot == 0 and idx_zero1 == 10)) or (idx_dot == 10 and idx_zero1 == 0):
                l_cmap_char = cmap_char
            else:
                l_cmap_char = tuple(reversed(cmap_char))
                min_cmap += 1
            self._font_mapping[font_name] = str.maketrans(
                {chr(k): l_cmap_char[k - min_cmap - idx_dot] for k in cmap.keys()})
        ret = value.translate(self._font_mapping[font_name])
        if ret.endswith('.99'):
            raise ValueError(f"wrong translation: {value} -> {ret}")
        return ret
