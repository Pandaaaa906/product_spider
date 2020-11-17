from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class OmicronSpider(BaseSpider):
    name = "omicron"
    base_url = "https://www.omicronbio.com/"
    start_urls = ['https://www.omicronbio.com/products/index.html', ]

    def parse(self, response):
        a_nodes = response.xpath('//ul[not(@id) and not(@class)]/li/a')
        for a in a_nodes:
            parent = strip(a.xpath('./text()').get())
            rel_url = a.xpath('./@href').get()
            url = urljoin(response.url, rel_url)
            if rel_url.startswith('..'):
                yield Request(url, callback=self.parse_detail, meta={'parent': parent})
            else:
                yield Request(url, callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        rel_urls = response.xpath('//td[@class="prdname"]/a/@href').getall()
        parent = response.meta.get('parent')
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//th[contains(text(), {!r})]/following-sibling::td//text()'
        rel_img = response.xpath('//img[@id="structure"]/@src').get()
        d = {
            'brand': 'Omicron',
            'parent': response.meta.get('parent'),
            'cat_no': response.xpath(tmp.format("Catalog")).get(),
            'en_name': ''.join(response.xpath('//h1//text()').getall()),
            'cas': response.xpath(tmp.format("CAS RN")).get(),
            'mw': response.xpath(tmp.format("MW")).get(),
            'mf': ''.join(response.xpath(tmp.format("Formula")).getall()),
            'info1': ';'.join(response.xpath('//ul[@id="syn"]/li/text()').getall()),
            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }
        yield RawData(**d)
