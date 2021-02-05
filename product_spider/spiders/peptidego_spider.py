from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class PeptidegoSpider(BaseSpider):
    name = "peptidego"
    start_urls = ['http://www.peptidego.com/products/products_5_1.html', ]
    brand = 'peptidego'

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 3,
    }

    def parse(self, response):
        rel_urls = response.xpath('//ul[@class="i-list cl"]/li/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list)

    def parse_list(self, response):
        parent = response.xpath('//li[@class="active"]/a/text()').get()

        rel_urls = response.xpath('//li[not(div[@class="i-n-time"])]//h3[@class="ws"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list)

        rel_urls = response.xpath('//li[div[@class="i-n-time"]]//h3[@class="ws"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//span[@class="thisclass"]/following-sibling::a[not(contains(text(), ">"))]/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse_list)

    def parse_detail(self, response):
        tmp = '//td[span[contains(text(), {!r})]]/following-sibling::td/span/text()'
        cat_no = strip(response.xpath(tmp.format("货号")).get())
        if not cat_no:
            return
        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': cat_no,
            'en_name': strip(response.xpath(tmp.format("英文名称")).get()),
            'chs_name': strip(response.xpath(tmp.format("中文名称")).get()),
            'cas': strip(response.xpath(tmp.format("CAS NO")).get()),
            'mf': strip(response.xpath(tmp.format("分子式")).get()),
            'mw': strip(response.xpath(tmp.format("分子量")).get()),
            'info1': strip(response.xpath(tmp.format("序列")).get()),
            'info2': strip(response.xpath(tmp.format("存储温度")).get()),
            'purity': strip(response.xpath(tmp.format("纯度")).get()),

            'prd_url': response.url,
        }
        yield RawData(**d)
