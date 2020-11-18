from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class PharmaffiliatesSpider(BaseSpider):
    name = "pharmaffiliates"
    start_urls = ['https://www.pharmaffiliates.com/en/allapi']

    def parse(self, response):
        a_nodes = response.xpath('//a[@class="sort-alpha"]')
        for a in a_nodes:
            parent = strip(a.xpath('./text()').get())
            rel_url = a.xpath('./@href').get()
            if not rel_url:
                continue
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        urls = response.xpath('//a[text()="Details "]/@href').getall()
        parent = response.meta.get('parent')
        for url in urls:
            yield Request(url, callback=self.parse_detail, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td//text()'
        parent = response.meta.get('parent')
        name = strip(response.xpath('//h1[@class]/text()').get())
        chemical_name = response.xpath(tmp.format("Chemical name")).get()
        d = {
            'brand': 'Pharmaffiliates',
            'parent': parent and parent.title(),
            'cat_no': response.xpath(tmp.format("Catalogue number")).get(),
            'en_name': name or chemical_name,
            'cas': strip(response.xpath('//h2[contains(text(), "CAS Number")]/../following-sibling::td//text()').get()),
            'mf': ''.join(response.xpath(tmp.format("Molecular form")).getall()),
            'mw': response.xpath(tmp.format("Mol. Weight")).get(),
            'appearance': response.xpath(tmp.format("Appearance")).get(),
            'info1': response.xpath(tmp.format("Synonyms")).get() or chemical_name,
            'info2': strip(response.xpath(tmp.format("Storage")).get()),
            'img_url': response.xpath('//img[@id="mainimg"]/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
