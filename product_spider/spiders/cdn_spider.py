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

    def parse(self, response, *args, **kwargs):
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
        feature = response.xpath(tmp.format('Isotopic Enrichment')).get()  # 特性值
        function_group = response.xpath(tmp.format("Functional Groups")).get()  # 官能团

        stability = response.xpath(tmp.format('Stability')).get()  # 稳定状态
        danger_desc = response.xpath(tmp.format("Shipping Hazards")).get()  # 危险标识
        prd_attrs = json.dumps({
            "feature": feature,
            "danger_desc": danger_desc,
        })

        package_attrs = json.dumps({
            "function_group": function_group,
            "stability": stability,
        })

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
            "info2": response.xpath(tmp.format("Storage Conditions")).get(),  # 储存条件
            "attrs": prd_attrs,
            "prd_url": response.url,
        }

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
                'delivery_time': 'In-stock' if item.get('is_in_stock') else None,
                "attrs": package_attrs,
            }
            yield RawData(**d)
            yield ProductPackage(**dd)
