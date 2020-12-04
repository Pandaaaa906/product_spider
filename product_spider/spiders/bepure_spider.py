import json
import re
from random import random
from urllib.parse import urlencode, quote

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class BepureSpider(BaseSpider):
    name = "bepure"
    base_url = "http://www.bepurestandards.com/"
    api_url = 'http://www.bepurestandards.com/a.aspx?'
    start_urls = ["http://www.bepurestandards.com/a.aspx?oper=getSubNav", ]

    def parse(self, response):
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
                'brand': 'BePure',
            }
            yield Request(
                self.api_url+urlencode(params),
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
            d = {
                'brand': 'Bepure',
                'cat_no': product.get('code'),
                'chs_name': product.get('name'),
                'stock_info': product.get('cnum'),
                'cas': cas,
                'purity': product.get('purity'),
                'info3': product.get('pack'),
                'info4': product.get('price'),
                'expiry_date': product.get('enddate'),
                'prd_url': tmp.format(product.get('id'), quote(parent))
            }
            yield RawData(**d)

        page_table = first(j_obj.get('table1'), {})
        cur_page = int(page_table.get('no', 0))
        total_page = int(page_table.get('pagecount', 0))
        params = response.meta.get('params')

        if cur_page >= total_page:
            return
        params['page'] = str(int(params['page']) + 1)
        yield Request(
            self.api_url+urlencode(params),
            callback=self.parse_list,
            meta={
                'parent': parent,
                'params': params,
            }
        )
