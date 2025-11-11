import json
import math

import lxml.html
from scrapy import Request
from scrapy.http import JsonRequest

from product_spider.items import RawData, ProductPackage, RawSupplierQuotation, SupplierProduct
from product_spider.utils.functions import get_url, extract_adjacent_property
from product_spider.utils.items_translate import product_package_to_raw_supplier_quotation, rawdata_to_supplier_product
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider
import html


class LabgicSpider(BaseSpider):
    name = "labgic"
    start_urls = ['https://mall.labgic-ljk.com/classified']
    base_url = "https://www.labgic.online/"
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'RETRY_ENABLED': True,
        'RETRY_HTTP_CODES': [403],
        'RETRY_TIMES': 10,
        'RETRY_BACKOFF_BASE': 2,
        'RETRY_BACKOFF_MAX': 60,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }
    currency = 'RMB'

    def parse(self, response, **kwargs):
        urls = ["https://mall.labgic-ljk.com/api/mall4cloud_product/ua/category/getByOneId?oneId=1",
                'https://mall.labgic-ljk.com/api/mall4cloud_product/ua/category/getByOneId?oneId=2',
                'https://mall.labgic-ljk.com/api/mall4cloud_product/ua/category/getByOneId?oneId=3',
                'https://mall.labgic-ljk.com/api/mall4cloud_product/ua/category/getByOneId?oneId=282',
                ]
        for url in urls:
            yield JsonRequest(url, callback=self.handle_category_req, headers={
                'Referer': response.url,
            })

    def parse_brand(self, brand: str):
        if 'labgic' in brand.lower():
            return 'labgic'
        elif 'biosharp' in brand.lower():
            return 'biosharp'
        return brand.lower()

    def handle_category_req(self, response):
        j_obj = response.json()
        item_list = j_obj.get('data')
        for item in item_list:
            children = item.get("childList")
            if type(children) is list:
                for child in children:
                    params = {"isSales": 0, "orderField": 1, "orderType": 2, "categoryName": child.get('name'),
                              "brandName": "", "brandIdFirstList": None, "officeId": None}
                    parent = child.get('name')
                    yield JsonRequest(
                        'https://mall.labgic-ljk.com/api/mall4cloud_product/ma/spu/ua/search?pageNum=1&pageSize=15',
                        data=params, callback=self.parse_list, meta={'page': 1, 'parent': parent, 'params': params, })
            elif name := item.get("name"):
                params = {"isSales": 0, "orderField": 1, "orderType": 2, "categoryName": name,
                          "brandName": "", "brandIdFirstList": None, "officeId": None}
                yield JsonRequest(
                    'https://mall.labgic-ljk.com/api/mall4cloud_product/ma/spu/ua/search?pageNum=1&pageSize=15',
                    data=params, callback=self.parse_list, meta={'page': 1, 'parent': name, 'params': params, })

    def parse_list(self, response):
        parent = response.meta.get('parent')
        self.logger.info(f'list url:{response.url} parent:{parent}')
        j_obj = response.json()
        j_obj = j_obj.get('data')
        item_list = j_obj.get('spuList')
        if not item_list:
            return
        for item in item_list:
            spu_id = item.get('spuId')
            url = f'https://mall.labgic-ljk.com/api/mall4cloud_product/ma/spu/getDetailBySpuId?spuId={spu_id}'
            yield JsonRequest(url, callback=self.parse_detail, meta=response.meta)

        total = j_obj.get('total', 0)
        total_page = math.ceil(total / 15)
        next_page = response.meta['page'] + 1
        params = response.meta['params']
        if next_page <= total_page:
            yield JsonRequest(
                f'https://mall.labgic-ljk.com/api/mall4cloud_product/ma/spu/ua/search?pageNum={next_page}&pageSize=15',
                data=params, callback=self.parse_list, meta={'page': next_page, 'parent': parent, 'params': params, })

    def extract_property(self, tree, keyword: str, base_xpath: str = None):
        base_xpath = base_xpath or '//'
        temp = tree.xpath(f"{base_xpath}*[contains(text(),'{keyword}')]/text()")
        if temp:
            temp = temp[0]
            return temp.replace(keyword, '')
        return None

    def parse_detail(self, response):
        j_obj = response.json()
        j_obj = j_obj.get('data')
        if img_url := j_obj.get('mainImgUrl'):
            img_url = get_url('https://labgic-prd.oss-cn-hangzhou.aliyuncs.com', img_url)
        sku_list = j_obj.get('skuList')
        product_id = j_obj.get('spuId')
        first_sku = sku_list[0]
        cat_no = first_sku.get('skuCode')
        if not cat_no:
            self.logger.info(f"No cat no found, url:{response.url}")
            return
        brand = self.parse_brand(j_obj.get('brandNameFirst'))

        detail = j_obj.get('detail')
        detail_properties = {}
        if detail:
            tree = lxml.html.fromstring(detail)
            if purity := self.extract_property(tree, '纯度：', ):
                purity = html.unescape(purity)
            mf = None
            if mf_parts := tree.xpath("//*[contains(text(),'分子式：')]//text()"):
                mf = ''.join(mf_parts)
                mf = mf.replace('分子式：', '')
                mf = formula_trans(mf)
            detail_properties = {
                'cas': self.extract_property(tree, 'CAS：', ),
                'mf': mf,
                'mw': self.extract_property(tree, '分子量：', ),
                'purity': purity,
                'appearance': self.extract_property(tree, '外观：', )
            }
        d = {
            "brand": brand,
            "parent": j_obj.get('categoryName') or response.meta.get('parent'),
            "cat_no": cat_no,
            "chs_name": j_obj.get('name'),
            "img_url": img_url,
            'prd_url': f'https://mall.labgic-ljk.com/detail/{product_id}',
            "info2": j_obj.get('saveTemperature'),
        }
        d.update(detail_properties)
        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        yield SupplierProduct(**ddd)

        for sku in first_sku.get('skuUnityDTOList', []):
            if (status := sku.get('status')) != 1:
                continue
            price = sku.get('marketPrice')
            cost = sku.get('costPrice')
            if type(cost) is float and cost <= 0.0:
                cost = None
            attrs = {
                'cost': cost
            }
            if stock_num := first_sku.get("stock"):
                stock_num = str(stock_num)
            dd = {
                "brand": brand,
                "cat_no": d['cat_no'],
                "package": first_sku.get('productFormat'),
                "cost": price,
                "price": price,
                "stock_num": stock_num,
                "currency": self.currency,
                'attrs': json.dumps(attrs, ensure_ascii=False),
            }
            yield ProductPackage(**dd)
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
            yield RawSupplierQuotation(**dddd)
