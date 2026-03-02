import json
from urllib.parse import urljoin, urlencode

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class USPSpider(BaseSpider):
    name = "usp"
    brand = 'usp'
    start_urls = []
    store_url = 'https://store.usp.org/ccstoreui/v1/products'
    base_url = "https://store.usp.org/"

    LIMIT = 250

    custom_settings = {
        'RETRY_HTTP_CODES': [403],
    }

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

        通过 USP typeahead 接口搜索产品，获取产品信息后解析。
        接口: /ccstore/v1/assembler/pages/Default/services/typeahead?Ntt={keyword}&Ntk=TypeAhead&Nrpp=8000
        该接口返回精确匹配的结果（如 acetone 只有7个产品）。
        """
        # 使用 typeahead 搜索接口获取产品信息
        d = {
            "Ntt": keyword,
            "Ntk": "TypeAhead",
            "Nrpp": "8000",
        }
        search_url = f"{self.base_url}ccstore/v1/assembler/pages/Default/services/typeahead?{urlencode(d)}"

        yield Request(
            url=search_url,
            headers={
                "Accept": "application/json",
            },
            meta={
                'keyword': keyword,
                'search_params': search_params,
                'task_id': self.task_id,
            },
            callback=self.parse_typeahead_results
        )

    def parse_typeahead_results(self, response):
        """解析 typeahead JSON 响应，直接提取产品信息并生成 items

        从 USP typeahead 接口返回的 JSON 数据中提取产品属性，生成 RawData、
        ProductPackage、SupplierProduct 和 RawSupplierQuotation items。

        数据格式：
        - resultsList.records: 产品列表，每个 record 包含嵌套的 records
        - 每个内部 record 的 attributes 包含产品属性（product.id、
          product.displayName、USPProductType.usp_cas_number 等）

        属性提取使用 first() 方法安全处理空列表情况。
        """
        data = response.json()
        results_list = data.get('resultsList', {})
        records = results_list.get('records', [])

        self.logger.info(f"Found {len(records)} products from typeahead")

        # 直接从 typeahead 结果中提取产品信息
        for record in records:
            # 内部 records 包含实际的产品数据
            inner_records = record.get('records', [])
            for inner_record in inner_records:
                attrs = inner_record.get('attributes', {})

                # 提取产品ID
                cat_no = first(attrs.get('product.id', []), None)
                if not cat_no:
                    continue

                # 提取其他属性
                prd_attrs = {}

                # 检查是否是管制物品
                dea_number = first(attrs.get('USPProductType.usp_dea_number', []), None)
                if dea_number and dea_number != '0':
                    prd_attrs["regulated_info"] = "US DEA Regulated Item"

                # 提取产品名称
                en_name = first(attrs.get('product.displayName', []), None) or first(attrs.get('product.description', []), None)

                # 提取 CAS
                cas = first(attrs.get('USPProductType.usp_cas_number', []), None)

                # 提取分子式
                mf = first(attrs.get('USPProductType.usp_molecular_formula', []), None)
                mf = mf.replace('-','') if isinstance(mf, str) else mf

                # 提取 parent (schedule_b_desc)
                parent = first(attrs.get('USPProductType.usp_schedule_b_desc', []), None)

                # 提取库存信息
                stock_info = first(attrs.get('USPProductType.usp_in_stock', []), None)

                # 提取产品链接
                route = first(attrs.get('product.route', []), None)
                prd_url = urljoin(self.base_url, route) if route else None

                d = {
                    'brand': self.brand,
                    'cat_no': cat_no,
                    'parent': parent,
                    'en_name': en_name,
                    'cas': cas,
                    'mf': mf,
                    'stock_info': stock_info,
                    'prd_url': prd_url,
                    'attrs': json.dumps(prd_attrs, ensure_ascii=False) if prd_attrs else None,
                }

                yield RawData(**d)
                yield SupplierProduct(**rawdata_to_supplier_product(d, self.name, self.name))

                # 提取价格和包装信息
                list_price = first(attrs.get('product.listPrice', []), None)
                cost = str(list_price) if list_price else None

                package_size = first(attrs.get('USPProductType.usp_packing_size', []), None)
                unit = first(attrs.get('USPProductType.usp_uom', []), None)
                package = f"{package_size}{unit}" if package_size and unit else None

                if cost and package:
                    dd = {
                        'brand': self.brand,
                        'cat_no': cat_no,
                        'package': package,
                        'cost': cost,
                        'currency': 'USD',
                        'delivery_time': stock_info,
                    }
                    yield ProductPackage(**dd)
                    yield RawSupplierQuotation(
                        **product_package_to_raw_supplier_quotation(d, dd, self.name, self.name)
                    )
