import re

import demjson
import execjs
from more_itertools import first
from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.middlewares.handle521 import get_params, encrypt_cookies, hash_d
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class TanmoSpider(BaseSpider):
    name = "tanmo"
    base_url = "https://www.gbw-china.com/"
    start_urls = ["https://www.gbw-china.com/", ]

    handle_httpstatus_list = [521]

    # custom_settings = {
    #     'DOWNLOADER_MIDDLEWARES': {
    #         'product_spider.middlewares.handle521.Cookie521Middleware': 100,
    #     }
    # }

    def parse(self, response, **kwargs):
        a_nodes = response.xpath(
            '//a[parent::dd|parent::dt[not(following-sibling::dd/a)]][contains(@href, "list_good")]')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            url = a.xpath('./@href').get()
            yield Request(url, callback=self.parse_list, meta={'parent': parent})

    def handle_521(self, response, callback, **kwargs):
        n = response.meta.get('n', 0)
        if 'document.cookie' in response.text:
            js_clearance = re.findall('cookie=(.*?);location', response.text)[0]
            result = execjs.eval(js_clearance).split(';')[0]
            k, v, *_ = result.split('=')
            yield Request(response.url, callback=callback, cookies={k: v}, meta={'n': n + 1},
                          dont_filter=True)
        else:
            params = get_params(response)
            chars = params['chars']
            bts = params['bts']
            ha = params['ha']
            ct = params['ct']
            hash_func = hash_d[ha]
            clearance = encrypt_cookies(chars, bts, ct, hash_func)
            yield Request(response.url, callback=callback,
                          cookies={'__jsl_clearance_s': clearance}, meta={'n': n + 1}, dont_filter=True
                          )

    def parse_list(self, response):
        if response.status == 521:
            yield from self.handle_521(response, self.parse_list)
            return
        parent = response.meta.get('parent')
        rows = response.xpath('//table[@id="product_table"]/tbody/tr')
        for row in rows:
            sub_brand = row.xpath('./td[10]/div/text()').get()
            if sub_brand and not ('坛墨' in sub_brand or 'tm' in sub_brand.lower()):
                continue
            url = row.xpath('./td[1]//a/@href').get()
            yield Request(url, callback=self.parse_detail, meta={'parent': parent})

        cur_page = first(re.findall(r'pno: (\d+),', response.text), None)
        total_page = first(re.findall(r'total: (\d+),', response.text), None)
        if cur_page is None or total_page is None:
            return
        if int(cur_page) >= int(total_page):
            return
        next_page = re.sub(r'\d+(?=\.html)', str(int(cur_page) + 1), response.url)
        yield Request(next_page, callback=self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        if response.status == 521:
            yield from self.handle_521(response, callback=self.parse_detail)
            return
        tmp = '//el-form-item[contains(@label, {!r})]/span/text()'
        brand = strip(response.xpath(tmp.format("品牌")).get(), "")
        brand = '_'.join(('Tanmo', brand)).lower()
        cat_no = strip(response.xpath(tmp.format("产品编号")).get())
        good_obj = demjson.decode(first(re.findall(r'goodObj: ({[^}]+}),', response.text), '{}'))

        d = {
            'brand': brand,
            'cat_no': cat_no,
            'chs_name': strip(response.xpath('//h2[@class="p-right-title"]/text()').get()),
            'cas': strip(response.xpath(tmp.format("CAS号")).get()),

            'stock_info': good_obj.get('number', 0),
            'expiry_date': good_obj.get('date', 0),
            'purity': strip(response.xpath(tmp.format("标准值")).get()),

            'info2': strip(response.xpath(tmp.format("储存条件")).get()),
            'info3': strip(response.xpath(tmp.format("规格")).get()),
            'info4': good_obj.get('price', '咨询'),

            'prd_url': response.url,
        }
        yield RawData(**d)

        dd = {
            'brand': brand,
            'cat_no': cat_no,
            'package': strip(response.xpath(tmp.format("规格")).get()),
            'price': good_obj.get('price', '咨询'),
            'currency': 'RMB',
        }
        yield ProductPackage(**dd)
