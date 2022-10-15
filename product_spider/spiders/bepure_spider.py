import json
import re
from os import getenv
from random import random
from urllib.parse import urlencode, quote

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.spider_mixin import BaseSpider

BEPURE_USER = getenv('BEPURE_USER')
BEPURE_PWD = getenv('BEPURE_PWD')


class BepureSpider(BaseSpider):
    name = "bepure"
    base_url = "http://www.bepurestandards.com/"
    api_url = 'http://www.bepurestandards.com/a.aspx?'
    start_urls = ["http://www.bepurestandards.com/a.aspx?oper=getSubNav", ]
    brand = 'bepure'

    def start_requests(self):
        if BEPURE_USER and BEPURE_PWD:
            pass
        else:
            yield from super().start_requests()

    def after_login(self, response):
        yield from super().start_requests()

    def parse(self, response, **kwargs):
        j_obj = json.loads(response.text)
        rows = j_obj.get('table', [])
        for row in rows:
            parent = row.get('title')
            if not parent:
                continue
            params = {
                'oper': 'Product_list',
                'time': str(random()),
                'title': parent,
                'page': '1',
                'oderby': '品牌',
                'sort': '降序',
                'brand': '',
            }
            yield Request(
                self.api_url + urlencode(params),
                callback=self.parse_list,
                meta={
                    'parent': parent,
                    'params': params,
                }
            )

    def parse_list(self, response):
        j_obj = json.loads(response.text)
        parent = response.meta.get('parent')
        tmp = 'http://www.bepurestandards.com/show/{}/{}/Y/true'
        products = j_obj.get('table2', [])
        for product in products:
            name = product.get('name')
            cas = first(re.findall(r'\d+-\d{2}-\d', name), None)
            cat_no = product.get('code')
            brand = product.get('brand', '').lower()
            prd_url = tmp.format(product.get('id'), quote(parent))
            d = {
                'brand': brand,
                'cat_no': cat_no,
                'en_name': product.get('name2'),
                'chs_name': product.get('name'),
                'stock_info': product.get('cnum'),
                'cas': cas,
                'purity': product.get('purity'),
                'info3': product.get('pack'),
                'info4': product.get('price'),
                'expiry_date': product.get('enddate'),
                'prd_url': prd_url
            }

            dd = {
                'brand': brand,
                'cat_no': cat_no,
                'package': product.get('pack'),
                'cost': product.get('price'),
                'currency': 'RMB',
                'delivery_time': product.get('cnum')
            }
            yield SupplierProduct(
                platform='bepure',
                source_id=product.get('id'),
                brand=brand,
                cat_no=cat_no,
                cas=cas,
                package=product.get('pack'),
                price=product.get('price'),
                delivery=product.get('cnum'),
                vendor_url=prd_url,
            )
            if not brand or brand != 'bepure':
                continue
            yield RawData(**d)
            yield ProductPackage(**dd)

        page_table = first(j_obj.get('table1'), {})
        total_page = int(page_table.get('pagecount', 0))
        params = response.meta.get('params')
        cur_page = int(params.get('page', 1))
        if cur_page >= total_page:
            return
        params['page'] = str(int(params['page']) + 1)
        yield Request(
            self.api_url + urlencode(params),
            callback=self.parse_list,
            meta={
                'parent': parent,
                'params': params,
            }
        )
