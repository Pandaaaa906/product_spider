import json
from urllib.parse import urljoin, urlencode

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class USPSpider(BaseSpider):
    name = "usp"
    brand = 'usp'
    start_urls = ["https://store.usp.org/OA_HTML/ibeCCtpSctDspRte.jsp?section=10042", ]
    store_url = 'https://store.usp.org/ccstoreui/v1/products'
    base_url = "https://store.usp.org/"

    LIMIT = 250

    def _start_requests(self):
        d = {
            'totalResults': True,
            'totalExpandedResults': True,
            'catalogId': 'cloudCatalog',
            'limit': self.LIMIT,
            'offset': 0,
            'sort': 'ID:[object Object]',
            # 'categoryId': 'USP-1010',
            'includeChildren': 'true',
            'storePriceListGroupId': 'defaultPriceGroup'
        }
        yield Request(f'{self.store_url}?{urlencode(d)}', meta={'data': d}, callback=self.parse)

    def parse(self, response, **kwargs):
        j = response.json()
        products = j.get('items', [])
        for product in products:
            prd_attrs = {}
            raw_danger_desc = product.get("usp_control_substance_percent", None)
            if raw_danger_desc is not None:
                prd_attrs["regulated_info"] = "US DEA Regulated Item"
            if oem_brand := product.get('brand'):
                prd_attrs["oem_brand"] = oem_brand
            if usp_country_of_origin := product.get('usp_country_of_origin'):
                prd_attrs["country_of_origin"] = usp_country_of_origin
            d = {
                'brand': self.brand,
                'cat_no': (cat_no := product.get('repositoryId')),
                'parent': product.get('usp_schedule_b_desc'),
                'en_name': product.get('description'),
                'cas': product.get('usp_cas_number'),
                'mf': product.get('usp_molecular_formula'),
                'stock_info': product.get('usp_in_stock'),
                'prd_url': (p := product.get('route')) and urljoin(self.base_url, p),
                'attrs': json.dumps(prd_attrs, ensure_ascii=False),
            }
            yield RawData(**d)
            yield SupplierProduct(**rawdata_to_supplier_product(d, self.name, self.name))

            package_size = product.get('usp_packing_size', '')
            unit = product.get('usp_uom', '')

            package = '{}{}'.format(package_size, unit)
            if (package_size is None) or (unit is None):
                continue
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': package,
                'cost': str(product.get('listPrice')),
                'currency': 'USD',
                'delivery_time': product.get('usp_in_stock'),
            }
            yield ProductPackage(**dd)
            if dd['cost']:
                yield RawSupplierQuotation(
                    **product_package_to_raw_supplier_quotation(d, dd, self.name, self.name)
                )

        offset = j.get('offset', 0) + j.get('limit', self.LIMIT)
        if offset > j.get('totalResults', 0):
            return
        data = response.meta.get('data', {})
        data['offset'] = offset
        yield Request(url=f'{self.store_url}?{urlencode(data)}', meta={'data': data}, callback=self.parse)

    def keyword_search(self, keyword: str, search_params: dict = None):
        """关键词搜索方法

        通过 USP API 搜索产品，使用 searchText 参数进行关键词搜索。
        """
        # 构建搜索参数，keyword_search 时减少 limit 以加速
        d = {
            'totalResults': True,
            'totalExpandedResults': True,
            'catalogId': 'cloudCatalog',
            'limit': 50,  # keyword_search 时使用较小的 limit 加速
            'offset': 0,
            'sort': 'ID:[object Object]',
            'includeChildren': 'true',
            'storePriceListGroupId': 'defaultPriceGroup',
            'searchText': keyword,  # 搜索关键词
        }

        # 如果有额外的搜索参数，添加到请求中
        if search_params:
            d.update(search_params)

        # 返回搜索请求
        yield Request(
            url=f'{self.store_url}?{urlencode(d)}',
            meta={
                'data': d,
                'keyword': keyword,
                'search_params': search_params,
                'task_id': self.task_id,
            },
            callback=self.parse
        )
