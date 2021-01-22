from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class PayneSpider(BaseSpider):
    name = "payne"
    base_url = "http://www.paynepharm.com/"
    start_urls = ['http://www.paynepharm.com/', ]
    brand = '上海佰纳'

    def parse(self, response):
        urls = response.xpath('//li[@catalogcode="01"]/ul/li/a/@href').getall()
        for url in urls:
            yield Request(url, callback=self.parse_parent)

    def parse_parent(self, response):
        urls = response.xpath('//td/a/@href').getall()
        for url in urls:
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        parent = strip(response.xpath('//strong//text()').get())
        urls = response.xpath('//div[@class="iproimg"]/a/@href').getall()
        for url in urls:
            yield Request(url, callback=self.parse_detail, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td//text()'
        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': strip(response.xpath(tmp.format("产品编号：")).get()),
            'en_name': strip(response.xpath('//div[@class="proinftit_t"]/text()').get()),
            'cas': strip(response.xpath(tmp.format("CAS号：")).get()),
            'mf': strip(''.join(response.xpath(tmp.format("分子式：")).getall())),
            'mw': strip(response.xpath(tmp.format("分子量：")).get()),
            'info1': strip(response.xpath(tmp.format("化学名：")).get()),

            'img_url': response.xpath('//div[@class="proinfotableimg"]/img/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)

