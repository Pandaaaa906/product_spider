from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class HPCSpider(BaseSpider):
    name = "hpc"
    base_url = "https://www.hpc-standards.com/"
    start_urls = ["https://www.hpc-standards.com/shop/", ]

    def parse(self, response):
        urls = response.xpath('//li[@class="second-level"]/a/@href').getall()
        for url in urls:
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        urls = response.xpath('//td/p/a[@name]/@href').getall()
        parent = response.xpath('//h1/text()').get()
        for url in urls:
            yield Request(url, callback=self.parse_detail, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td//text()'
        quantity = response.xpath(tmp.format("Quantity")).get()
        concentration = response.xpath(tmp.format("Concentration")).get()
        solvent = response.xpath(tmp.format("Solvent")).get()
        info3 = f'{quantity}; {concentration} in {solvent}' if concentration else quantity
        mw = response.xpath(tmp.format("Molecular weight")).get()
        d = {
            'brand': 'hpc',
            'parent': response.meta.get('parent'),
            'cat_no': response.xpath(tmp.format("Item number")).get(),
            'en_name': response.xpath('//h1/text()').get(),
            'cas': response.xpath(tmp.format("CAS")).get(),
            'mf': response.xpath(tmp.format("Formula")).get(),
            'mw': mw,
            'info2': response.xpath(tmp.format("storage conditions")).get(),
            'info3': info3,
            'img_url': response.xpath('//a[@class="fancybox"]/img/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
