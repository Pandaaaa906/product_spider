import itertools
import math
import time
from hashlib import md5

from scrapy import FormRequest

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class AikonchemSpider(BaseSpider):
    name = "aikonchem"
    brand = "aikonchem"
    start_urls = ["https://aikonchem.com/product", ]
    list_url = 'https://apii.aikonchem.com/home/prodList'
    detail_url = 'https://apii.aikonchem.com/home/prodInfo'
    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        'RETRY_ENABLED': True,
        'RETRY_HTTP_CODES': [403],
        'RETRY_TIMES': 10,
        'RETRY_BACKOFF_BASE': 2,
        'RETRY_BACKOFF_MAX': 60,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }

    def get_sign(self, cur_time: int):
        return md5(f'PBn2W4%6Y7J4SYWERTYgo0k%n!@d7x%k{cur_time}'.encode('utf-8')).hexdigest()

    def make_request(self, url, form, callback, meta=None):
        cur_time = int(time.time())
        sign = self.get_sign(cur_time)
        return FormRequest(
            url,
            formdata=form,
            headers={'sign': sign, 'time': cur_time},
            callback=callback,
            method='POST',
            meta=meta or {}
        )

    def parse(self, response, **kwargs):
        url = 'https://apii.aikonchem.com/home/categoryList'
        cur_time = int(time.time())
        sign = self.get_sign(cur_time)
        yield FormRequest(url, headers={'sign': sign, 'time': cur_time}, callback=self.handle_category_response,
                          method='POST')

    def handle_category_response(self, response):
        j_obj: dict = response.json()
        if j_obj.get('code') != 200:
            self.logger.info(f'Error data code:{j_obj}')
            return
        items = j_obj.get('data')
        items = [x.get('children', []) for x in items if type(x) is dict]
        items = list(itertools.chain.from_iterable(items))

        for item in items:
            cate_id = item.get('id')
            if not cate_id:
                continue
            form = {
                'page': '1',
                'pageSize': '20',
                'cate_id': str(cate_id),
            }
            yield self.make_request(self.list_url, form, callback=self.parse_list, meta={
                'cur_page': 1,
                'page_size': 20,
                'cate_id': cate_id,
                'parent': item.get('name')
            })

    def parse_list(self, response):
        j_obj: dict = response.json()
        if j_obj.get('code') != 200:
            self.logger.info(f'Error data code:{j_obj}')
            return
        items = j_obj.get('data', {}).get('list', [])
        total: int = j_obj.get('data', {}).get('total', 0)
        cas_list = [x.get('cas') for x in items if type(x) is dict]
        for cas in cas_list:
            form = {
                'keyword': cas,
            }
            yield self.make_request(self.detail_url, form, self.parse_detail, meta=response.meta)

        cur_page = response.meta.get('cur_page', 1)
        page_size = response.meta.get('page_size', 20)
        total_page = math.ceil(total / page_size)

        if cur_page < total_page:
            next_page = cur_page + 1
            form = {
                'page': str(next_page),
                'pageSize': str(page_size),
                'cate_id': str(response.meta.get('cate_id')),
            }
            yield self.make_request(self.list_url, form, self.parse_list, meta={
                'cur_page': next_page,
                'page_size': page_size,
                'parent': response.meta.get('parent'),
                'cate_id': response.meta.get('cate_id')
            })

    def parse_detail(self, response):
        j_obj: dict = response.json()
        if j_obj.get('code') != 200:
            self.logger.info(f'Error data code:{j_obj.get("code")}')
            return
        product_info: dict = (j_obj.get('data') or {}).get('prod_info')
        if not product_info:
            self.logger.warning(f'No product info')
            return

        cas = product_info.get("cas")
        d = {
            "brand": self.brand,
            "parent": response.meta.get('parent'),
            "cat_no": product_info.get('prod_no'),
            "en_name": product_info.get('en_name'),
            "chs_name": product_info.get('name'),
            "cas": cas,
            "smiles": product_info.get('smiles'),
            "mf": product_info.get('mf'),
            "mw": product_info.get('mw'),
            "prd_url": f'https://aikonchem.com/product/{cas}?cas={cas}',
            "img_url": product_info.get('img'),
            "mdl": product_info.get('mdl'),
        }
        yield RawData(**d)

        rows = j_obj.get('data').get('price_list', [])
        if not rows:
            return
        for row in rows:
            dd = {
                "brand": self.name,
                "cat_no": d['cat_no'],
                "package": f'{row.get("num")}{row.get("unit")}',
                "cost": row.get('price'),
                "price": row.get('price'),
                "currency": 'RMB',
                "purity": row.get('purity'),
                "delivery_time": row.get('inventory'),
            }
            yield ProductPackage(**dd)
