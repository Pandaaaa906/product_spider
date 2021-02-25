import json
from urllib.parse import urljoin

from scrapy import Request, FormRequest

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class SddStoreSpider(BaseSpider):
    name = "sddstore"
    base_url = "http://www.sddstore.com/"
    prd_url = 'http://www.sddstore.com/web/item/info/getAll.do'

    @staticmethod
    def make_form(page: int):
        return {
            'page': str(page),
            'limit': '12',
            'state': '1',
            'queryType': 'web',
        }

    def start_requests(self):
        page = 1
        d = self.make_form(page)
        yield FormRequest(self.prd_url, formdata=d, callback=self.parse)

    def parse(self, response):
        j_obj = json.loads(response.text)
        prds = j_obj.get('data', [])
        for prd in prds:
            prd_id = prd.get('id')
            if not prd_id:
                continue
            yield Request(f'http://www.sddstore.com/info/item/{prd_id}', callback=self.parse_detail)

        if prds:
            next_page = response.meta.get('page', 1) + 1
            f = self.make_form(next_page)
            yield FormRequest(self.prd_url, formdata=f, callback=self.parse, meta={'page': next_page})

    def parse_detail(self, response):
        tmp = '//div[contains(text(), {!r})]/following-sibling::div/text()'
        rel_img = response.xpath('//img[@class="pic"]/@src').get()

        d = {
            'brand': 'sdd',
            'cat_no': response.xpath('//tr/td[1]/text()').get(),
            'en_name': response.xpath('//div[@class="row"]//dl/dd/text()').get(),
            'chs_name': response.xpath('//div[@class="row"]//dl/dt/text()').get(),
            'cas': strip(response.xpath(tmp.format("CAS NO.")).get()),
            'mf': strip(response.xpath(tmp.format("分子式")).get()),
            'mw': strip(response.xpath(tmp.format("分子量")).get()),
            'info1': strip(response.xpath(tmp.format("英文异名")).get()),
            'info2': response.xpath('//td[contains(text(), "存储条件")]/following-sibling::td[1]/text()').get(),
            'info3': response.xpath('//tr/td[6]/text()').get(),
            'info4': response.xpath('//tr/td[5]/text()').get(),
            'stock_info': response.xpath('//tr/td[7]/text()').get(),
            'appearance': response.xpath('//td[contains(text(), "性状")]/following-sibling::td[1]/text()').get(),
            'img_url': rel_img and urljoin(self.base_url, rel_img),
            'prd_url': response.url,
        }
        yield RawData(**d)
