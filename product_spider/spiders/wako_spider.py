from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class WakoSpider(BaseSpider):
    name = "wako"
    base_url = "http://www.bb-china.net/"
    start_urls = ['http://www.bb-china.net/', ]
    brand = 'Wako'

    def parse(self, response):
        rel_urls = response.xpath(
            '//div[@class="search-note-box" and not(contains("耗材仪器", .//h1/text()))]//li/a/@href').getall()
        for rel in rel_urls:
            yield Request(urljoin(response.url, rel)+'&brand=155', callback=self.parse_list)

    def parse_list(self, response):
        rel_urls = response.xpath('//td/a/@href').getall()
        for rel in rel_urls:
            yield Request(urljoin(response.url, rel), callback=self.parse_detail)

        next_page = response.xpath('//a[@class="next"]/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse_list)

    def parse_detail(self, response):
        tmp = '//b[contains(text(), {!r})]/following-sibling::text()'
        cat_no = response.xpath('//td/p/text()').get()
        if not cat_no:
            return
        package = strip(response.xpath('//td[3]/text()').get())
        price =strip(response.xpath('//td[5]/text()').get())
        d = {
            'brand': self.brand,
            'parent': response.xpath('//div[@class="search-tab"]/a[last()]/text()').get(),
            'cat_no': cat_no,
            'en_name': strip(response.xpath('//div[@class="bo2bo"]/h1/text()').get()),
            'chs_name': strip(response.xpath('//div[@class="bo2bo"]/h2/text()').get()),
            'cas': strip(response.xpath(tmp.format("CAS No.：")).get()) or None,
            'info2': response.xpath(tmp.format("储存条件：")).get(),
            'info3': package,
            'info4': price,
            'purity': response.xpath(tmp.format("纯度：")).get(),

            'prd_url': response.url,
        }
        yield RawData(**d)

        yield ProductPackage(
            brand=self.brand,
            cat_no=cat_no,
            package=package,
            price=price
        )
