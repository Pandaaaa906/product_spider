import json
import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData
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
            'chs_name': strip(response.xpath('//h4[@class="c red1"]/text()').get()),
            'prd_url': response.url,
        }
        pd_id = response.xpath('//input[@id="nowproductid"]/@value').get()
        if not pd_id:
            return
        yield Request(
            'http://www.bjhongmeng.com/ajaxpro/Web960.Web.index,Web960.Web.ashx',
            method='POST',
            body=json.dumps({'pd_id': pd_id,}),
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
        (_, (prd, *_)), *_ = obj.items()
        prd, *_ = prd.get('Inventores', [])

        (_, goods_info), *_ = json.loads(prd.get('Goods_Info', '{}')).items()

        d = response.meta.get('product', {})
        d['info3'] = goods_info.get('packaging')
        d['purity'] = goods_info.get('purity')
        d['info3'] = f"{prd.get('Conv', '')} {prd.get('Measure', '')}"
        d['info3'] = f"{prd.get('MoneyUnit', '')} {prd.get('Price', '')}"
        yield RawData(**d)
