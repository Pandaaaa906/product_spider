from urllib.parse import urljoin, urlencode

from scrapy import Request

from product_spider.items import RawData, ProductPackage
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
        yield Request(f'{self.store_url}?{urlencode(d)}', meta={'data': d})

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

            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': f"{product.get('usp_packing_size', '')}{product.get('usp_uom', '')}",
                'cost': product.get('listPrice'),
                'currency': 'USD',
                'delivery_time': product.get('usp_in_stock'),
            }
            yield ProductPackage(**dd)

        offset = j.get('offset', 0) + j.get('limit', 250)
        if offset > j.get('totalResults', 0):
            return
        data = response.meta.get('data', {})
        data['offset'] = offset
        yield Request(f'{self.store_url}?{urlencode(data)}', meta={'data': data})
