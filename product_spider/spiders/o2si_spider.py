from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class O2siSpider(BaseSpider):
    name = "o2si"
    brand = 'O2si'
    base_url = "https://www.o2si.com/"
    start_urls = ['https://www.o2si.com/', ]
    custom_settings = {
        'CONCURRENT_REQUESTS': '4',
    }

    def parse(self, response):
        a_nodes = response.xpath('//li[a/text()="Catalog"]//li/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url),
                          callback=self.parse_sub_parent, meta={'parent': parent})

    def parse_sub_parent(self, response):
        a_nodes = response.xpath('//div[h1]//li/a')
        top_parent = response.meta.get('parent')
        for a in a_nodes:
            sub_parent = a.xpath('./text()').get()
            parent = f'{top_parent}__{sub_parent}'
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        parent = response.meta.get('parent')
        rows = response.xpath('//li/form')
        for row in rows:
            rel_url = row.xpath('.//span[@class="title"]/a/@href').get()

            yield Request(
                urljoin(self.base_url, rel_url), callback=self.parse_detail,
                meta={
                    'parent': parent,
                    'cat_no': strip(row.xpath('./span[@class="number"]/text()').get()),
                    'en_name': strip(row.xpath('./span[@class="title"]/a/text()').get()),
                    'package': strip(row.xpath('./span[@class="size"]/text()').get()),
                })

        next_page = response.xpath(
            '//div[contains(text(),"Page")]/a[contains(@class,"current")]/following-sibling::a/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        cas = response.xpath('//tr[@class="style17"]/td[3]/text()').getall()
        cas = tuple(filter(lambda x: x, (strip(i) for i in cas)))
        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': response.meta.get('cat_no'),
            'en_name': response.meta.get('en_name'),
            'cas': first(cas, None) if len(cas) == 1 else None,
            'info1': ';'.join(set(cas)),
            'info3': response.meta.get('package'),
            'info4': response.xpath('//p[contains(text(), "Price:")]/strong/text()').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
