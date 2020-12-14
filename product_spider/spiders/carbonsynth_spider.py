from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class CarbonsynthSpider(BaseSpider):
    name = "carbonsynth"
    base_url = "https://www.carbosynth.com/"
    start_urls = ['https://www.carbosynth.com/', ]

    def parse(self, response):
        a_nodes = response.xpath('//a[contains(@href, "all-products-by")]')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        rel_urls = response.xpath('//div[@class="table-responsive"]//td/a/@href').getall()
        parent = response.meta.get('parent')
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//a[contains(text(), "Next Page")]/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//td[child::b[contains(text(), {!r})]]/following-sibling::td//text()'
        rel_img = response.xpath('//div[@class="prod-img-container"]//img/@src').get()
        d = {
            'brand': 'Carbonsynth',
            'parent': response.meta.get('parent'),
            'cat_no': response.xpath('//span[@class="code"]//text()').get(),
            'en_name': strip(response.xpath('//h1[@class="name"]/text()').get()),
            'cas': strip(response.xpath(tmp.format("CAS No:")).get()),
            'mf': strip(''.join(response.xpath(tmp.format("Chemical Formula:")).get())),
            'mw': strip(response.xpath(tmp.format("Molecular Weight:")).get()),

            'info3': strip(response.xpath('//tr[@id="row0"]/td[1]//text()').get()),
            'info4': strip(response.xpath('//tr[@id="row0"]/td[5]//text()').get()),
            'stock_info': strip(response.xpath('//tr[@id="row0"]/td[2]//text()').get()),

            'img_url': rel_img and urljoin(self.base_url, rel_img),
            'prd_url': response.url,
        }
        yield RawData(**d)
