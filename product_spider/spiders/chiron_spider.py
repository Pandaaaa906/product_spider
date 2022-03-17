from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class ChironSpider(BaseSpider):
    name = "chiron"
    start_urls = ['http://shop.chiron.no/main.aspx']

    def parse(self, response, **kwargs):
        rel_urls = response.xpath(
            '//a[@class="product-cat" and text()!="Agency products"]/'
            'following-sibling::ul//li[not(child::ul) and @class="selected"]/a[contains(@href, "pid_3")]/@href'
        ).getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list)

    def parse_list(self, response):
        rel_urls = response.xpath('//a[@class="prod-name"]/@href').getall()
        parent = response.xpath('//ul[contains(@class, "breadcrumb")]/li[last()]/a/text()').get()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//a[text()="Next page"]/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse_list)

    def parse_detail(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td/text()'
        currency = response.xpath(tmp.format("Currency")).get()
        cost = response.xpath(tmp.format("excl. VAT")).get()
        package = response.xpath(tmp.format("Pack size")).get()
        if package:
            package = package.replace(" ", '')
        cat_no = response.xpath(tmp.format("Product no.")).get()
        d = {
            'brand': 'chiron',
            'parent': response.meta.get('parent'),
            'cat_no': cat_no,
            'en_name': response.xpath('//h2/text()').get(),
            'cas': response.xpath(tmp.format("CAS Nr.")).get(),
            'stock_info': response.xpath(
                '//span[contains(text(), "Stock status")]/parent::div/parent::td/following-sibling::td/span/text()'
            ).get(),
            'prd_url': response.url,
        }
        dd = {
            'brand': 'chiron',
            "cat_no": cat_no,
            "package": package,
            "cost": cost,
            "currency": currency,
        }
        yield RawData(**d)
        yield ProductPackage(**dd)
