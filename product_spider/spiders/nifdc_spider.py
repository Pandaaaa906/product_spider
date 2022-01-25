import re
from os import getenv
from urllib.parse import urljoin

from scrapy import FormRequest, Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


NIFDC_USER = getenv('NIFDC_USER', '')
NIFDC_PASS = getenv('NIFDC_PASS', '')


class NifdcSpider(BaseSpider):
    name = 'nifdc'
    brand = '中检所'
    start_urls = [
        'http://aoc.nifdc.org.cn/sell/sgoodsQuerywaiw.do?formAction=queryzc',  # 常规
        'http://aoc.nifdc.org.cn/sell/sgoodsQuerywaiwTs.do?formAction=queryTs',  # 特殊
    ]
    code_url = 'http://aoc.nifdc.org.cn/sell/regwwuser.do?formAction=qdyanzm'
    login_url = 'http://aoc.nifdc.org.cn/sell/loginwaiw.do?formAction=index'

    def start_requests(self):
        yield Request(self.code_url, callback=self.login)

    def login(self, response):
        yield FormRequest(self.login_url, formdata={
            'user_code': NIFDC_USER,
            'userpwd': NIFDC_PASS,
            'inputCode': response.text,
        }, callback=self.parse)

    def parse(self, response, **kwargs):
        for url in self.start_urls:
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        tmp = './/input[@name={!r}]/@value'
        rows = response.xpath('//table[@class="list_tab"]/tr')
        for row in rows:
            coa = row.xpath('.//td[14]/a/@href').get()
            d = {
                'brand': self.brand,
                'cat_no': (cat_no := rows.xpath(tmp.format('sgoods_no')).get()),
                'parent': row.xpath(tmp.format('sgoods_type')).get(),
                'chs_name': rows.xpath(tmp.format('sgoods_name')).get(),
                'en_name': rows.xpath(tmp.format('english_name')).get(),
                'info2': rows.xpath(tmp.format('save_condition')).get(),
                'stock_info': rows.xpath(tmp.format('zdgmshu')).get(),
                'prd_url': coa and urljoin(response.url, coa),
            }
            yield RawData(**d)
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': row.xpath(tmp.format('standard')).get(),
                'price': row.xpath(tmp.format('unit_price')).get(),
                'info': row.xpath(tmp.format('xsBatch_no')).get(),
                'currency': 'RMB'
            }
            yield ProductPackage(**dd)

        m = re.search(r'(?:buildPageCtrlOne001\()(\d+),(\d+),(\d+)', response.text)
        if not m:
            return
        cur_page, per_page, total = m.groups()
        if (cur_page := int(cur_page)) * int(per_page) > int(total):
            return
        form_data = {
            "curPage": str(cur_page + 1),
            "toPage": str(cur_page),
        }
        yield FormRequest(response.url, formdata=form_data, callback=self.parse_list)

