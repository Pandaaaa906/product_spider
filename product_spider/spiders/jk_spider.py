import json
import re
from string import ascii_uppercase
from time import time
from urllib.parse import urljoin

import scrapy
from more_itertools import first
from scrapy import Request, FormRequest
from scrapy.http import JsonRequest

from product_spider.items import JkProduct, JKPackage
from product_spider.utils.functions import strip


class JkPrdSpider(scrapy.Spider):
    name = "jk"
    allowed_domains = ["jkchemical.com"]
    base_url = "http://www.jkchemical.com"
    prd_url = 'https://web.jkchemical.com/api/product-catalog/{catalog_id}/products/{page}'

    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                          'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
            # hardcoding?
            'Authorization': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MCwidW5pdCI6MjQsImd1ZXN0Ijo3NjE2OTUsInVxIjo1'
                             'NCwicm9sZXMiOm51bGwsImlhdCI6MTYyNzk2Njk4NX0.8mea_0U6wOZKvqrb-y6k689j8R1coOcnSUNOIOHyiMo',
        }
    }

    def start_requests(self):
        d = {
            'language': 196,
            'salesRegion': 1,
        }
        yield JsonRequest(
            'https://shop.jkchemical.com/uq/prod/product/tv/query/GetRootCategory',
            data=d,
            callback=self.parse
        )

    def parse(self, response, **kwargs):
        obj = response.json()
        ret = obj.get('res', '')
        for line in ret.split('\n'):
            catalog_id, *_ = line.split('\t')
            page = 1
            yield Request(
                self.prd_url.format(catalog_id=catalog_id, page=page),
                meta={'page': page, 'catalog_id': catalog_id},
                callback=self.parse_list
            )

    def parse_list(self, response):
        obj = response.json()
        prds = obj.get('hits', [])
        for prd in prds:
            d = {
                'brand': prd.get('brand', {}).get('name'),
                'cat_no': prd.get('origin'),
                'en_name': prd.get('description'),
                'cn_name': prd.get('descriptionC'),
                'cas': prd.get('CAS'),
                'purity': prd.get('purity'),
                'img_url': (img_url_id := prd.get('imageUrl')) and f'https://static.jkchemical.com/Structure/{img_url_id[:3]}/{img_url_id}.png',
                'prd_url': (tmp := prd.get('id')) and f'https://www.jkchemical.com/product/{tmp}'
            }
            yield JkProduct(**d)


    def parse_package(self, response):
        s = re.findall(r"(?<=\().+(?=\))", response.text)[0]
        packages = json.loads(s)
        d = response.meta.get('prd_data', {})
        package = first(packages, {})
        if package:
            d['brand'] = d['brand'] or package.get('Product', {}).get('BrandName')
        yield JkProduct(**d)
        for package_obj in packages:
            catalog_price = package_obj.get("CatalogPrice", {})
            dd = {
                'brand': d.get('brand'),
                'cat_no': d.get('cat_no'),
                'package': package_obj.get("stringFormat"),
                'price': catalog_price and catalog_price.get('Value'),
                'currency': catalog_price and strip(catalog_price.get('Currency')),
                'attrs': json.dumps(package_obj),
            }
            yield JKPackage(**dd)
