from urllib.parse import urljoin

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
            'cat_no': strip(response.xpath('//table//tr[2]/td[2]//text()').get()),
            'purity': strip(response.xpath('//table//tr[2]/td[3]//text()').get()),
            'chs_name': strip(response.xpath('//h4[@class="c red1"]/text()').get()),
            'info3': strip(response.xpath('//table//tr[2]/td[4]//text()').get()),
            'info4': strip(response.xpath('//table//tr[2]/td[5]//text()').get()),
            'stock_info': strip(response.xpath('//table//tr[2]/td[7]//text()').get()),
            'prd_url': response.url,
        }
        yield RawData(**d)
