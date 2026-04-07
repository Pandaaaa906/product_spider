import json

from scrapy import Request
from scrapy.http import JsonRequest

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class AltaSpider2(BaseSpider):
    """阿尔塔"""
    name = "alta2"
    brand = 'alta'
    base_url = "http://www.altascientific.com/"
    start_urls = ['https://store.altascientific.com/', ]
    list_url = 'https://store.altascientific.com/api/gd-goods/member/alter/product/spuInfo/page/list'
    category_url = 'https://store.altascientific.com/api/gd-goods/member/alter/product/spuInfo/category/list'

    def _start_requests(self):
        yield Request(self.category_url, callback=self.parse)

    def parse(self, response, **kwargs):
        j_obj = response.json()
        categories = j_obj.get("data", [])
        for category in categories:
            children = category.get("children", [])
            for child in children:
                yield from self.request_list(page_index=1, label_id=child.get('categoryId'),
                                             parent=child.get("name"))

        # 混标
        yield from self.request_list(page_index=1, parent='混标', spuType=2)

    def request_list(self, page_index: int, label_id: str = '', parent: str = '', spuType: int = '', **kwargs):
        params = {"keywords": "", "labelId": label_id, "categoryId": '', "pageIndex": page_index, "pageSize": 10,
                  "spuType": spuType, "userId": ""}
        yield JsonRequest(self.list_url, data=params, callback=self.parse_list, meta={
            'cur_page': page_index,
            'parent': parent,
            'params': params,
        })

    def parse_list(self, response):
        cur_page = response.meta.get('cur_page')
        parent = response.meta.get('parent', None)
        j_obj = response.json()
        products = j_obj.get('data', [])
        for p in products:
            if _id := p.get('id'):
                detail_url = (f'https://store.altascientific.com/api/gd-goods/member/alter/product/spuInfo/not'
                              f'/loggedIn/detail/{_id}')
                yield JsonRequest(detail_url, callback=self.parse_detail, meta={'parent': parent})

        total_page = (j_obj.get('total') // j_obj.get('pageSize')) + 1
        if cur_page < total_page:
            params = response.meta['params']
            yield from self.request_list(page_index=cur_page + 1, label_id=params['labelId'], parent=parent,
                                         spuType=params['spuType'])

    def parse_detail(self, response):
        j_obj = response.json()
        j_obj = j_obj.get('data')
        if not j_obj:
            self.logger.warning(f"No detail found, url:{response.url}")
            return
        prd_attrs = {}
        synonym = ';'.join(x for x in (j_obj.get("synonymCn"), j_obj.get("synonymEn")) if x)
        cat_no = j_obj.get('parentCode')

        spu_group_list = j_obj.get("spuGroupList")
        components = []
        if isinstance(spu_group_list, list):
            components = [{
                'cas': x.get("cas"),
                'en_name': x.get("nameEn"),
                'cn_name': x.get("name"),
                'conc': x.get("specs"),
                'cat_no': x.get("code"),
            } for x in spu_group_list]
        if components:
            prd_attrs['components'] = components
        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': cat_no,
            'en_name': j_obj.get('spuNameEn'),
            'chs_name': j_obj.get('spuName'),
            'mf': j_obj.get('formula'),
            'mw': j_obj.get('formulaNum'),
            'cas': j_obj.get('cas'),
            'purity': j_obj.get('density'),
            'info1': synonym,
            'info2': j_obj.get('storage'),
            'shipping_info': j_obj.get('transport'),
            "attrs": json.dumps(prd_attrs),
            'img_url': j_obj.get('img'),
            'prd_url': f'https://store.altascientific.com/#/mall/goods/detail?spuId={j_obj.get("id")}',
        }

        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, platform=self.brand, vendor=self.brand)
        yield SupplierProduct(**ddd)

        stock_num = j_obj.get('num') if j_obj.get('showNum') == '现货' else j_obj.get('showNum')
        # TODO 登录拿价格
        cost = 0
        dd = {
            'brand': self.brand,
            'cat_no': cat_no,
            'package': j_obj.get("specs"),
            'cost': cost,
            'price': cost,
            "stock_num": str(stock_num),
            'currency': 'RMB',
            'purity': d.get('purity'),
        }
        yield ProductPackage(**dd)

        dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.brand, vendor=self.brand)
        yield RawSupplierQuotation(**dddd)
