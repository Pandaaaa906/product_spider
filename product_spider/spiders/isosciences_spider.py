from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class IsosciencesSpider(BaseSpider):
    name = "isosciences"
    base_url = "https://isosciences.com/"
    start_urls = ['https://isosciences.com/', ]

    def parse(self, response):
        urls = response.xpath('//a[@title="Products"]/following-sibling::ul//li[not(child::ul)]/a/@href').getall()
        for url in urls:
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        parent = response.xpath('//nav[@class="woocommerce-breadcrumb"]/a[last()]/text()').get()
        urls = response.xpath('//a[@class="btn-view-details"]/@href').getall()
        for url in urls:
            yield Request(url, callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//span[@aria-current]/../following-sibling::li/a/@href').get()
        if next_page:
            yield Request(next_page, callback=self.parse_list)

    def parse_detail(self, response):
        tmp = '//th[contains(text(), {!r})]/following-sibling::td//text()'
        price = response.xpath('//span[@class="price"]/span/text()').get()
        d = {
            'brand': 'isosciences',
            'parent': response.meta.get('parent'),
            'cat_no': response.xpath(tmp.format("Catalog #")).get(),
            'en_name': strip(''.join(response.xpath('//h1[contains(@class, "product_title")]//text()').getall())),
            'cas': response.xpath(tmp.format("CAS #")).get(),
            'purity': response.xpath(tmp.format("Purity")).get(),
            'info2': response.xpath(tmp.format("Shipping Information")).get(),
            'info3': response.xpath('//label[contains(@for, "pa_size_")]/text()').get(),
            'info4': price and f'USD {price}',
            'img_url': response.xpath('//a[@data-lightbox="product-image"]/img/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
