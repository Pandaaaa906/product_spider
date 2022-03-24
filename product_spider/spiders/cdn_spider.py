import json
import re
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip, first
from product_spider.utils.spider_mixin import BaseSpider


class CDNPrdSpider(BaseSpider):
    name = 'cdn'
    brand = 'cdn'
    base_url = "https://cdnisotopes.com/"
    start_urls = [
        "https://cdnisotopes.com/nf/alphabetlist/view/list/?char=ALL&limit=50", ]

    def parse(self, response, **kwargs):
        urls = response.xpath('//ol[@id="products-list"]/li/div[@class="col-11"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin(self.base_url, url), callback=self.detail_parse)
        next_page = response.xpath('//div[@class="pages"]//li[last()]/a/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse)

    # TODO Stock information (actually all product info) is described in the page js var matrixChildrenProducts
    def detail_parse(self, response):
        tmp = '//th[contains(text(),{0!r})]/following-sibling::td/descendant-or-self::text()'
        img_url = response.xpath('//th[contains(text(),"Structure")]/following-sibling::td/img/@src').get()
        cat_no = strip(response.xpath(tmp.format("Product No.")).get())
        d = {
            "brand": self.brand,
            "cat_no": cat_no,
            "parent": response.xpath(tmp.format("Category")).get(),
            "info1": "".join(response.xpath(tmp.format("Synonym(s)")).extract()),
            "mw": response.xpath(tmp.format("Molecular Weight")).get(),
            "mf": "".join(response.xpath(tmp.format("Formula")).extract()),
            "cas": response.xpath(tmp.format("CAS Number")).get(),
            "en_name": strip(
                "".join(response.xpath('//div[@class="product-name"]/span/descendant-or-self::text()').extract())),
            "img_url": img_url and urljoin(self.base_url, img_url),
            "stock_info": response.xpath(
                '//table[@id="product-matrix"]//td[@class="unit-price"]/text()').get(),
            "prd_url": response.url,
        }
        yield RawData(**d)

        matrix = first(re.findall(r'var matrixChildrenProducts = ({.+});', response.text), None)
        if not matrix:
            return
        packages = json.loads(matrix)
        for _, item in packages.items():
            sku = item.get('sku')
            if not sku:
                continue
            package = sku.replace(f'{cat_no}-', '')
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'cat_no_unit': sku,
                'package': strip(package),
                'cost': item.get('price'),
                'currency': 'USD',
                'delivery_time': 'In-stock' if item.get('is_in_stock') else None
            }
            yield ProductPackage(**dd)
