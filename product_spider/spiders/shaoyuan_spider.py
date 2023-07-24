import re
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class ShaoyuanSpider(BaseSpider):
    name = "shaoyuan"
    # start_urls = ["http://www.shao-yuan.com/cn/productlist_catalogid_205.html", ]
    base_url = "http://www.shao-yuan.com/"
    brand = '韶远'

    def start_requests(self):
        _id = 1
        while _id < 600000:
            yield Request(
                f"http://www.shao-yuan.com/cn/productview_goodsid_{_id}.html",
                callback=self.parse_detail,
            )
            _id += 1

    def parse_detail(self, response):
        tmp = '//li[contains(text(), {!r})]//text()'
        func = lambda res, t: res.xpath(tmp.format(t)).get('').lstrip(t) or None
        img_rel = response.xpath('//td/img/@src').get()

        cat_no = response.xpath('//tr[@id][1]/td[2]/text()').get()
        if not cat_no:
            return
        d = {
            'brand': self.brand,
            'cat_no': cat_no,
            'parent': strip(re.sub(r'\s+', ' ', func(response, '产品分类： ') or '')),
            'en_name': strip(response.xpath('//h2/text()[1]').get()),
            'chs_name': strip(response.xpath('//h2/text()[2]').get()),
            'cas': func(response, 'CAS号：'),
            'mf': func(response, '分子式：'),
            'mw': func(response, '分子量：'),
            'purity': func(response, '韶远库存批次纯度：'),

            'info3': response.xpath('//tr[@id][1]/td[4]/text()').get(),
            'info4': response.xpath('//tr[@id][1]/td[5]/text()').get(),
            'stock_info': response.xpath('//tr[@id][1]/td[8]/text()').get(),

            'img_url': img_rel and urljoin(response.url, img_rel),
            'prd_url': response.url,
        }
        yield RawData(**d)

        for tr in response.xpath('//tr[@id]'):
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': tr.xpath('./td[4]/text()').get(),
                'cost': tr.xpath('./td[5]/text()').get(),
                'currency': 'RMB',
                'delivery_time': tr.xpath('./td[8]/text()').get(),
            }
            if dd['package'] == 'bulk':
                continue
            yield ProductPackage(**dd)
