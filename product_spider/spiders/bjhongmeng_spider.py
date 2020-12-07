import json
import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request

from product_spider.items import HongmengItem
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class HongmengSpider(BaseSpider):
    name = "hongmeng"
    start_urls = ["http://www.bjhongmeng.com/shop/", ]
    base_url = "http://www.bjhongmeng.com/"

    def parse(self, response):
        a_nodes = response.xpath('//ul[@class="kj_sc_list l"]//li[not(child::ul/li/a)]/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        urls = response.xpath('//h4[@class="c"]/a/@href').getall()
        parent = response.meta.get('parent')
        for url in urls:
            yield Request(urljoin(self.base_url, url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//ul[contains(@class, "pagination")]/li[@class="active"]/following-sibling::li/a/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        d = {
            'brand': '海岸鸿蒙',
            'parent': response.meta.get('parent'),
            'cat_no': strip(response.xpath('//span[contains(@class, "kj_customno")]/text()').get()),
            'cas': strip(response.xpath('//p/text()[contains(self::text(), "CAS")]/following-sibling::span/text()').get()),
            'cn_name': strip(response.xpath('//h4[@class="c red1"]/text()').get()),
            'prd_url': response.url,
        }
        pd_id = response.xpath('//input[@id="nowproductid"]/@value').get()
        if not pd_id:
            return
        yield Request(
            'http://www.bjhongmeng.com/ajaxpro/Web960.Web.index,Web960.Web.ashx',
            method='POST',
            body=json.dumps({'pd_id': pd_id, }),
            headers={'X-AjaxPro-Method': 'LoadGoods', },
            callback=self.parse_price,
            meta={'product': d}
        )

    def parse_price(self, response):
        t = first(re.findall(r'({.+});', response.text))
        if not t:
            return
        obj = json.loads(t)
        obj = json.loads(obj.get('ObjResult'))
        d = response.meta.get('product', {})

        if not obj.items():
            yield HongmengItem(**d)
            return

        _, prds = zip(*obj.items())
        for prd in prds:
            prd = first(prd)
            for inventory in prd.get('Inventores', []):
                goods_info = json.loads(inventory.get('Goods_Info', '{}')).get('goodsinfo', {})

                d_prd = {
                    'sub_cat_no': inventory.get('Goods_no'),
                    'place_code': inventory.get('Placecode'),
                    'amount': inventory.get('Amount'),
                    'package': goods_info.get('packaging'),
                    'sub_brand': goods_info.get('brand'),
                    'purity': goods_info.get('purity'),
                    'price': f"{inventory.get('MoneyUnit')} {inventory.get('Price')}"
                }
                d_prd.update(d)
                yield HongmengItem(**d_prd)
