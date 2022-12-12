from urllib.parse import urljoin, urlencode

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.spider_mixin import BaseSpider


class USPSpider(BaseSpider):
    name = "usp"
    brand = 'usp'
    start_urls = ["https://store.usp.org/OA_HTML/ibeCCtpSctDspRte.jsp?section=10042", ]
    store_url = 'https://store.usp.org/ccstoreui/v1/products'
    base_url = "https://store.usp.org/"

    LIMIT = 250

    def start_requests(self):
        d = {
            'totalResults': True,
            'totalExpandedResults': True,
            'catalogId': 'cloudCatalog',
            'limit': self.LIMIT,
            'offset': 0,
            'sort': 'displayName:[object Object]',
            'categoryId': 'USP-1010',
            'includeChildren': 'true',
            'storePriceListGroupId': 'defaultPriceGroup'
        }
        yield Request(f'{self.store_url}?{urlencode(d)}', meta={'data': d}, callback=self.parse)

    def parse(self, response, **kwargs):
        j = response.json()
        products = j.get('items', [])
        for product in products:
            d = {
                'brand': self.brand,
                'cat_no': (cat_no := product.get('repositoryId')),
                'parent': product.get('usp_schedule_b_desc'),
                'en_name': product.get('description'),
                'cas': product.get('usp_cas_number'),
                'mf': product.get('usp_molecular_formula'),
                'stock_info': product.get('usp_in_stock'),
                'prd_url': (p := product.get('route')) and urljoin(self.base_url, p),
            }
            yield RawData(**d)

            package_size = product.get('usp_packing_size', '')
            unit = product.get('usp_uom', '')

            package = '{}{}'.format(package_size, unit)
            if (package_size is None) or (unit is None):
                continue
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': package,
                'cost': product.get('listPrice'),
                'currency': 'USD',
                'delivery_time': product.get('usp_in_stock'),
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
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
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

        offset = j.get('offset', 0) + j.get('limit', 250)
        if offset > j.get('totalResults', 0):
            return
        data = response.meta.get('data', {})
        data['offset'] = offset
        yield Request(url=f'{self.store_url}?{urlencode(data)}', meta={'data': data}, callback=self.parse)
