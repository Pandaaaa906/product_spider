from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class ShaoyuanSpider(BaseSpider):
    name = "shaoyuan"
    start_urls = ["http://www.shao-yuan.com/cn/productlist_catalogid_205.html", ]
    base_url = "http://www.shao-yuan.com/"
    brand = '韶远'

    def parse(self, response):
        a_nodes = response.xpath('//div[@class="r_a_b_next_ladder"]//li/a')
        parent = response.meta.get('parent', '')
        for a in a_nodes:
            sub_parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse,
                          meta={'parent': f'{parent}_{sub_parent}' if parent else sub_parent}
                          )

        rel_urls = response.xpath('//div[not(@class)]/a[not(@target)]/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//a[text()="下一页"]/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), self.parse, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//li[contains(text(), {!r})]/text()'
        func = lambda res, t: res.xpath(tmp.format(t)).get('').lstrip(t) or None
        img_rel = response.xpath('//td/img/@src').get()

        cat_no = response.xpath('//tr[@id][1]/td[2]/text()').get()
        if not cat_no:
            return
        d = {
            'brand': self.brand,
            'cat_no': cat_no,
            'parent': response.meta.get('parent'),
            'en_name': strip(response.xpath('//h2/text()[1]').get()),
            'chs_name': strip(response.xpath('//h2/text()[2]').get()),
            'cas': func(response, 'CAS号：'),
            'mf': func(response, '分子式：'),
            'mw': func(response, '分子量：'),
            'purity': func(response, '韶远库存批次纯度：'),

            'info3': response.xpath('//tr[@id][1]/td[4]/text()').get(),
            'info4': response.xpath('//tr[@id][1]/td[5]/text()').get(),
            'stock_info': response.xpath('//tr[@id][1]/td[8]/text()').get(),

            'img_url': img_rel and urljoin(self.base_url, img_rel),
            'prd_url': response.url,
        }
        yield RawData(**d)

        for tr in response.xpath('//tr[@id]'):
            d_package = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': tr.xpath('./td[4]/text()').get(),
                'price': tr.xpath('./td[5]/text()').get(),
                'currency': 'RMB',
                'delivery_time': tr.xpath('./td[8]/text()').get(),
            }
            if d_package['package'] == 'bulk':
                continue
            yield ProductPackage(**d_package)
