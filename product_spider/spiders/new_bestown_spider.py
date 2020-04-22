import json
import logging
from random import random
from urllib.parse import urlencode

from more_itertools import first
from scrapy import Request

from product_spider.items import NewBestownItem
from product_spider.utils.spider_mixin import JsonSpider

logger = logging.getLogger(__name__)


def gen_post_data(catalog, page, operate='Product_list'):
    return {
        'oper': operate,
        'time': str(random()),
        'title': catalog,
        'page': str(page),
        'oderby': '价格',
        'sort': '降序',
        # 'orderby': '品牌',
        # 'sorder': '升序',
        'brand': '',
        'userid': '',
    }


class NewBestownSpider(JsonSpider):
    name = "new_bestown_prds"
    base_url = 'http://www.bepurestandards.com/'
    start_urls = [
        'http://www.bepurestandards.com/a.aspx?oper=Product_classification',
    ]

    def parse(self, response):
        j_obj = json.loads(response.text)
        for item in j_obj.get('table', ()):
            params = gen_post_data(item.get('title', ''), 1)
            yield Request(f'http://www.bepurestandards.com/a.aspx?{urlencode(params)}',
                          callback=self.list_parse,
                          meta=params
                          )

        # for kw in l_keywords:
        #     params = gen_post_data(kw, 1, 'sou_list')
        #     yield Request(f'http://www.bepurestandards.com/a.aspx?{urlencode(params)}',
        #                   callback=self.list_parse,
        #                   meta=params
        #                   )

    def list_parse(self, response):
        j_obj = json.loads(response.text)
        if j_obj.get('msg') != '正常':
            logger.info("出现不正常")
        for prd in j_obj.get('table2', []):
            params = {
                'oper': 'Detailed_product',
                'shopID': prd.get('id'),
                'sale': 'Y',
            }
            yield Request(f'http://www.bepurestandards.com/a.aspx?{urlencode(params)}',
                          callback=self.detail_parse
                          )
        total_page = int(first(j_obj.get('table1', []), {}).get('pagecount', '0'))
        cur_page = int(response.meta.get('page'))
        if total_page <= cur_page:
            return
        params = response.meta
        params['page'] = str(cur_page+1)
        yield Request(f'http://www.bepurestandards.com/a.aspx?{urlencode(params)}',
                      callback=self.list_parse,
                      meta=params
                      )

    def detail_parse(self, response):
        j_obj = json.loads(response.text)
        d = first(j_obj.get('table', []), {})
        if not d:
            return
        del d['no']
        d['uid'] = d['id']
        del d['id']
        yield NewBestownItem(**d)
