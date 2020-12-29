from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class LeyanSpider(BaseSpider):
    name = "leyan"
    base_url = "http://www.leyan.com.cn/"
    start_urls = ['http://www.leyan.com.cn/product-center.html', ]
    brand = '乐研'

    def parse(self, response):
        a_nodes = response.xpath('//div[@class="row"]/div/a')
        for a in a_nodes:
            parent = a.xpath('./span/text()').get()
            if parent in {'耗材', '仪器'}:
                continue
            rel = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel), callback=self.parse_list)

    def parse_list(self, response):
        rel_urls = response.xpath('//p[@class="products-thumb"]/a/@href').getall()
        for rel in rel_urls:
            yield Request(urljoin(response.url, rel), callback=self.parse_detail)

        next_page = response.xpath('//a[@aria-label="Next"]/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse_list)

    def parse_detail(self, response):
        tmp = '//div[contains(*/text(), {!r})]/following-sibling::div/*/text()'
        cat_no = response.xpath('//span[@id="catalogNo"]/text()').get()
        rel_img = response.xpath('//input[@id="image"]/@value').get()
        d = {
            'brand': self.brand,
            'parent': '_'.join(response.xpath('//li[@class="active"]/following-sibling::li/a/text()').getall()),
            'cat_no': cat_no,
            'en_name': response.xpath('//h2/span/text()').get(),
            'purity': response.xpath('//span[@class="d-purity"]/text()').get(),
            'cas': response.xpath(tmp.format("CAS 号")).get(),
            'mf': response.xpath(tmp.format("分子式")).get(),
            'mw': response.xpath(tmp.format("分子量")).get(),
            'smiles': response.xpath(tmp.format("Smiles Code")).get(),
            'info2': response.xpath(tmp.format("存储条件")).get(),
            'mdl': response.xpath(tmp.format("MDL 号")).get(),

            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }
        yield RawData(**d)

        rows = response.xpath('//div[@class="table-responsive"]//tr[position()!=1]')
        for row in rows:
            package = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': row.xpath('./td[@id="packing"]/text()').get(),
                'price': row.xpath('./td[@id="money"]/text()').get(),
                'currency': 'RMB',
                'stock_num': row.xpath('./td[@id="stock"]/text()').get(),
            }
            yield ProductPackage(**package)
