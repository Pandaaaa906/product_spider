from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class FermentekSpider(BaseSpider):
    name = "fermentek"
    base_url = "https://www.fermentek.com/"
    start_urls = ['https://www.fermentek.com/product-search-panels', ]

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="views-field views-field-title"]/span[@class="field-content"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail)

        next_page = response.xpath('//li[contains(@class,"active")]/following-sibling::li[not(@class)]/a/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse)

    def parse_detail(self, response):
        tmp = '//div[contains(text(),{!r})]/following-sibling::div/div//text()'
        img_url = response.xpath('//a/img[@typeof]/@src').get()
        smiles = ''.join(response.xpath(
            '//div[contains(text(),"Isomeric SMILES")]/following-sibling::div/div//text()[not(parent::a)]'
        ).getall())
        if img_url:
            img_url, *_ = img_url.split('?')
        d = {
            'brand': 'Fermentek',
            'cat_no': response.xpath(tmp.format("Fermentek product code:")).get(),
            'en_name': response.xpath('//div[contains(@class, "field-name-field-fermentek-product-id")]/div//text()').get(),
            'mf': strip(''.join(response.xpath(tmp.format("Molecular Formula")).getall())),
            'mw': response.xpath(tmp.format("Molecular weight:")).get(),
            'cas': response.xpath(tmp.format("CAS number:")).get(),
            'appearance': response.xpath(tmp.format("Appearance:")).get(),
            'info2': ';'.join(response.xpath(tmp.format("Storage, handling:")).getall()),
            'smiles': smiles,
            'img_url': img_url,
            'prd_url': response.url,
        }
        yield RawData(**d)
