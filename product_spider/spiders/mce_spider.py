from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class MCESpider(BaseSpider):
    name = "mce"
    base_url = "https://www.medchemexpress.com/"
    start_urls = ['https://www.medchemexpress.com/products.html', ]

    def parse(self, response):
        a_nodes = response.xpath('//td/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

        a_nodes = response.xpath('//div[@class="ctg_tit" and not(following-sibling::div[@class="ctg_con"])]/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        rel_urls = response.xpath('//th/a/@href').getall()
        parent = response.meta.get('parent')
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//li[@class="ui-pager focus"]/following-sibling::li/a/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//th[contains(text(), {!r})]/following-sibling::td//text()'
        package = '//td[@class="pro_price_1" and contains(text(), "mg") and not(./b)]'
        rel_img = response.xpath('//div[@class="struct-img-wrapper"]/img/@src').get()
        d = {
            'brand': 'MCE',
            'parent': response.meta.get('parent'),
            'cat_no': response.xpath('').get(),
            'en_name': response.xpath('//h1/strong/text()').get(),

            'cas': ''.join(response.xpath(tmp.format("CAS No.")).getall()),
            'mf': ''.join(response.xpath(tmp.format("Formula")).getall()),
            'mw': ''.join(response.xpath(tmp.format("Molecular Weight")).getall()),
            'smiles': ''.join(response.xpath(tmp.format("SMILES")).getall()),

            'info3': response.xpath(f'{package}/text()').get(),
            'info4': response.xpath(f'{package}/following-sibling::td[1]/text()').get(),

            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }
        yield RawData(**d)
