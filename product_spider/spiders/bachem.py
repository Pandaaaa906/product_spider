from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class BachemSpider(BaseSpider):
    name = "bachem"
    base_url = "https://shop.bachem.com/"
    currency_url = 'https://shop.bachem.com/storeselect/index/forward/country/CN/'
    start_urls = [
        "https://shop.bachem.com/application.html",
        "https://shop.bachem.com/inhibitors-and-substrates.html",
        "https://shop.bachem.com/amino-acids-and-biochemicals.html",
        "https://shop.bachem.com/peptides.html",
        "https://shop.bachem.com/new-products.html",
    ]
    cookies = {
        'store_country': 'US',
        'store': 'us',
        'storeselect': 'US%2Fus'
    }

    def parse(self, response):
        urls = response.xpath('//div[@class="product-name"]/a/@href').getall()
        for url in urls:
            yield Request(url, callback=self.parse_detail, cookies=self.cookies)

        next_page = response.xpath('//li[@class="current"]/following-sibling::li/a[not(@title)]/@href').get()
        if next_page:
            yield Request(next_page, callback=self.parse, cookies=self.cookies)

    def parse_detail(self, response):
        tmp = '//span[text()={!r}]/following-sibling::span/text()'
        tmp2 = '//h2/div[@class="std"]//text()[not(parent::span) and not(parent::a/parent::span)]'
        sequence = strip(''.join(response.xpath('//div[@class="std"]/span[@class]//text()').getall()))
        en_name = strip(''.join(response.xpath(tmp2).getall())) or None
        synonyms = strip(response.xpath(tmp.format("Synonyms")).get())
        d = {
            'brand': 'Bachem',
            'parent': strip(response.xpath('//li[@class="product"]/preceding-sibling::li[1]/a/text()').get()),
            'cat_no': strip(response.xpath('//div[@id="productname"]/text()').get()),
            'en_name': en_name or sequence,
            'cas': response.xpath(tmp.format("CAS Registry Number")).get(),
            'mf': formula_trans(response.xpath(tmp.format("Molecular Formula")).get()),
            'mw': response.xpath(tmp.format("Relative Molecular Mass")).get(),
            'info1': ';'.join(filter(lambda x: x, (synonyms, sequence))),
            'info2': response.xpath(tmp.format("Storage Conditions")).get(),
            'info3': response.xpath('//td[@class="masWeight"]/text()').get(),
            'info4': strip(response.xpath('//div[contains(@class, "formatted-price")]/text()').get()),
            'stock_info': response.xpath('//p[contains(@class, "availability")]/span/text()').get(),
            'img_url': response.xpath('//img[@class="zoom-image"]/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
