import json
import re
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import strip, first, dumps
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation


class CDNPrdSpider(BaseSpider):
    name = 'cdn'
    base_url = "https://cdnisotopes.com/"
    start_urls = [
        "https://cdnisotopes.com/nf/alphabetlist/view/list/?char=ALL&limit=50",
    ]
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        "PROXY_POOL_REFRESH_STATUS_CODES": [403, 504, 503],
    }

    def parse(self, response, *args, **kwargs):
        urls = response.xpath('//ol[@id="products-list"]/li/div[@class="col-11"]/a/@href').getall()
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

        prd_attrs = {
            "feature": response.xpath(tmp.format('Isotopic Enrichment')).get(),  # 特性值
            "danger_desc":  response.xpath(tmp.format("Shipping Hazards")).get(),  # 危险标识
            "function_group": response.xpath(tmp.format("Functional Groups")).get(),  # 官能团
            "stability": response.xpath(tmp.format('Stability')).get(),  # 稳定状态
        }

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": response.xpath(tmp.format("Category")).get(),
            "info1": "".join(response.xpath(tmp.format("Synonym(s)")).getall()),
            "mw": response.xpath(tmp.format("Molecular Weight")).get(),
            "mf": "".join(response.xpath(tmp.format("Formula")).getall()),
            "cas": response.xpath(tmp.format("CAS Number")).get(),
            "en_name": "".join(response.xpath('//div[@class="product-name"]/span/descendant-or-self::text()').getall()),
            "img_url": img_url and urljoin(self.base_url, img_url),
            "stock_info": response.xpath('//table[@id="product-matrix"]//td[@class="unit-price"]/text()').get(),
            "info2": response.xpath(tmp.format("Storage Conditions")).get(),  # 储存条件
            "attrs": dumps(prd_attrs),
            "prd_url": response.url,
        }
        yield RawData(**d)

        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)

        yield SupplierProduct(**ddd)

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
                'brand': self.name,
                'cat_no': cat_no,
                'cat_no_unit': sku,
                'package': strip(package),
                'cost': str(item.get('price')),
                'currency': 'USD',
                'delivery_time': 'in-stock' if item.get('is_in_stock') else None,
            }
            dddd = product_package_to_raw_supplier_quotation(d, dd,  platform=self.name, vendor=self.name)

            yield ProductPackage(**dd)
            yield RawSupplierQuotation(**dddd)
