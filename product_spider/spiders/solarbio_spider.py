import urllib.parse
from urllib.parse import urljoin

from scrapy import FormRequest

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider

IGNORE_BRANDS = {
    'cerillian',
    'usp',
}
BRANDS_MAPPING = {
    "sigald": "sigma",
    "sial": "sigma",
    "aldrich": "sigma",
    "saj": "sigma",
    "sigma": "sigma",
    "mm": "supelco",
    "supelco": "supelco",
    "vetec": "vetec",
    "avanti": "avanti",
    "roche": "roche",
}


class SigmaSpider(BaseSpider):
    name = "solarbio"
    start_urls = ["https://www.solarbio.com/", ]
    base_url = "https://www.solarbio.com/"
    category_url = 'https://www.solarbio.com/web/lists/category/index'
    product_list_url = "https://www.solarbio.com/web/lists/category/goods"

    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                          'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
            'Accept-Encoding': 'gzip, deflate, br', 'Accept': '*/*', 'Connection': 'keep-alive',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        },
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'CONCURRENT_REQUESTS_PER_IP': 8,
    }

    def _start_requests(self):
        yield FormRequest(self.category_url, callback=self.parse, headers={'referer': 'https://www.solarbio.com/'})

    def parse(self, response, **kwargs):
        j_obj = response.json()
        data = j_obj.get('data', [])

        for item in data:
            children = item.get('cat_id', [])
            if children:
                for child in children:
                    parent = child.get('name')
                    cat_id = child.get('id')
                    params = {
                        'id': cat_id,
                        'keywords': '',
                        'page': '1',
                        'size': '10',
                    }
                    yield FormRequest(self.product_list_url, callback=self.parse_list, meta={
                        'params': params,
                        'parent': parent,
                    }, formdata=params)
            else:
                parent = item.get('name')
                cat_id = item.get('id')
                params = {
                    'id': cat_id,
                    'keywords': '',
                    'page': '1',
                    'size': '10',
                }
                yield FormRequest(self.product_list_url, formdata=params, callback=self.parse_list, meta={
                    'params': params,
                    'parent': parent,
                })

    def parse_list(self, response):
        j_obj = response.json()
        data = j_obj.get('data', {}).get('data', [])
        if not data:
            return
        parent = response.meta.get('parent')
        params = response.meta.get('params')
        for item in data:
            product_id = item.get('goods_id')
            if not product_id:
                continue
            yield FormRequest('https://www.solarbio.com/web/goods/info/index', formdata={
                'goods_id': product_id,
            }, meta={'parent': parent}, callback=self.parse_detail)

        page = j_obj.get('data', {}).get('page')
        total_page = j_obj.get('data', {}).get('page_count')
        if page and total_page:
            if page < total_page:
                params['page'] = str(page + 1)
                yield FormRequest(self.product_list_url, formdata=params, callback=self.parse_list, meta={
                    'params': params,
                    'parent': parent,
                })

    def parse_detail(self, response):
        j = response.json()
        j_obj = j.get('data', {})
        rel_img = j_obj.get('img')
        if rel_img and type(rel_img) is list:
            rel_img = urllib.parse.urljoin('https://img.solarbio.com/', rel_img[0])

        brand = j_obj.get('brand_name', '').lower()
        cat_no = j_obj.get('goods_sn')
        if not brand:
            self.logger.warning(f"no brand found in url: {response.url}")
            return

        attrs = j_obj.get('attrs_main')
        if attrs:
            attrs = attrs[0].get('attr')
            if type(attrs) is list:
                attrs = {x.get("name"): x.get("value") for x in attrs}
        if type(attrs) is not dict:
            attrs = {}

        d = {
            "brand": BRANDS_MAPPING.get(brand, brand),
            "parent": response.meta.get('parent'),
            "cat_no": cat_no,
            "chs_name": j_obj.get('goods_name'),
            "en_name": j_obj.get('goods_name_en'),
            "purity": attrs.get('浓度'),
            "img_url": rel_img,
            "info2": attrs.get('存储条件'),
            "shipping_info": attrs.get('运输条件'),
            "prd_url": f'https://www.solarbio.com/goodsInfo?id={j_obj.get("goods_id")}',
        }
        if d['brand'] not in IGNORE_BRANDS:
            yield RawData(**d)

        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        yield SupplierProduct(**ddd)

        packages = j_obj.get('products')
        if type(packages) is list:
            req_stock_params = {str(index): x.get('product_sn') for index, x in enumerate(packages) if
                                x.get('product_sn')}
            cat_no_index_map = {index: x.get('product_sn') for index, x in enumerate(packages) if
                                x.get('product_sn')}
            yield FormRequest('https://www.solarbio.com/web/goods/info/new_number', formdata=req_stock_params,
                              callback=self.handle_stock_resp,
                              meta={'packages': packages, 'd': d, 'cat_no_index_map': cat_no_index_map, }, )

    def handle_stock_resp(self, response):
        cat_no_index_map = response.meta.get('cat_no_index_map')
        d = response.meta.get('d')
        stock_map = {}
        try:
            j_obj = response.json()
            data = j_obj.get('data')
            for index, item in enumerate(data):
                if type(item) is dict:
                    stock = sum(filter(lambda x: type(x) is int, dict(item).values()))
                    gt10 = sum([11 for _ in filter(lambda x: x == '>10', dict(item).values())])
                    stock += gt10
                    cat_no = cat_no_index_map.get(index)
                    if cat_no:
                        stock_map[cat_no] = str(stock)
        except:
            self.logger.warning(f"解析库存信息失败: response:{response.text} cat_no:{d['cat_no']}")
        packages = response.meta.get('packages')
        for package in packages:
            dd = {
                "brand": d['brand'],
                "cat_no": d['cat_no'],
                "package": package.get('attr_value'),
                "cost": package.get('attr_price'),
                "price": package.get('attr_price'),
                "currency": 'CNY',
                'stock_num': stock_map.get(package.get('product_sn'))
            }
            yield ProductPackage(**dd)
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
            yield RawSupplierQuotation(**dddd)
