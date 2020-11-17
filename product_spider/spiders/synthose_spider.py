from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class SynthoseSpider(BaseSpider):
    name = "synthose"
    base_url = "https://www.lcsci.com/"
    start_urls = ['https://www.lcsci.com/', ]

    def parse(self, response):
        a_nodes = response.xpath('//div[@id="lnav"]//li[not(child::ul)]/a')
        for a in a_nodes:
            parent = strip(a.xpath('./text()').get())
            rel_url = strip(a.xpath('./@href').get())
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        rel_urls = response.xpath('//dt/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, strip(rel_url)), callback=self.parse_detail, meta=response.meta)

    def parse_detail(self, response):
        tmp = '//th[contains(text(), {!r})]/following-sibling::td//text()'
        img_url = strip(response.xpath('//b/img/@src').get())
        d = {
            'brand': 'Synthose',
            'parent': response.meta.get('parent'),
            'cat_no': strip(response.xpath('//h1[@class="header"]/text()').get()),
            'en_name': strip(response.xpath('//h2[@class="compound"]/text()').get()),
            'mf': strip(response.xpath(tmp.format("Molecular Formula")).get()),
            'mw': strip(response.xpath(tmp.format("Molecular Weight")).get()),
            'cas': strip(response.xpath(tmp.format("CAS Number")).get()),
            'purity': strip(response.xpath(tmp.format("Chemical Purity")).get()),
            'appearance': strip(response.xpath(tmp.format("Appearance")).get()),
            'info1': strip(response.xpath('//h3[@class="synonym"]/text()').get()),
            'info3': strip(response.xpath('//table[@class="stock"]//tr[1]/th/text()').get()),
            'info4': strip(response.xpath('//table[@class="stock"]//tr[1]/td[1]/text()').get()),
            'stock_info': strip(response.xpath('//table[@class="stock"]//tr[1]/td[2]/text()').get()),
            'img_url': img_url and urljoin(self.base_url, img_url),
            'prd_url': response.url,
        }
        yield RawData(**d)
