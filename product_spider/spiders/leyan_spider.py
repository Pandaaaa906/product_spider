from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.spider_mixin import BaseSpider


class LeyanSpider(BaseSpider):
    name = "leyan"
    base_url = "http://www.leyan.com.cn/"
    start_urls = ['http://www.leyan.com.cn/product-center.html', ]
    brand = '乐研'

    def parse(self, response, **kwargs):
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
            'brand': self.name,
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
            if not (package := row.xpath('./td[@id="packing"]/text()').get()):
                continue
            dd = {
                'brand': self.name,
                'cat_no': cat_no,
                'package': package,
                'cost': row.xpath('./td[@id="money"]/text()').get(),
                'currency': 'RMB',
                'stock_num': row.xpath('./td[@id="stock"]/text()').get(),
            }

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id": f'{self.name}_{d["cat_no"]}_{dd["package"]}',
                "parent": d["parent"],
                "en_name": d["en_name"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
                "img_url": d["img_url"],
                "prd_url": d["prd_url"],
            }
            dddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id":  f'{self.name}_{d["cat_no"]}',
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'discount_price': dd['cost'],
                'price': dd['cost'],
                'currency': dd["currency"],
            }
            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)
            yield RawSupplierQuotation(**dddd)
