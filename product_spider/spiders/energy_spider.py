import html
import json
import re

from scrapy import Request, FormRequest

from product_spider.items import RawData, SupplierProduct, RawSupplierQuotation, ProductPackage
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class EnergySpiderSpider(BaseSpider):
    name = "energychemical"
    brand = "energychemical"
    start_urls = ["https://www.energy-chemical.com/front/index.htm", ]
    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        'RETRY_ENABLED': True,
        'RETRY_HTTP_CODES': [403],
        'RETRY_TIMES': 10,
        'RETRY_BACKOFF_BASE': 2,
        'RETRY_BACKOFF_MAX': 60,

    }
    num_map = {
        'β': '0',
        '⁄': '1',
        '⁜': '2',
        ':': '3',
        '−': '4',
        'ρ': '5',
        '😕': '6',
        'τ': '7',
        '😀': '8',
        '?': '9',
        '😅': '.',
    }

    def parse(self, response, **kwargs):
        rel_divs = response.xpath(
            "//div[contains(@class,'text-wrapper_15')]/div[contains(@onclick,'getChildrenOrDetail')]")
        for rel_div in rel_divs:
            parent = rel_div.xpath("./@title").get()
            match = re.search(r"'(\d+)'", rel_div.xpath('./@onclick').get())
            if match:
                id_value = match.group(1)
                url = f'https://www.energy-chemical.com/front/search_goodsbyclass.htm?labelId={id_value}'
                yield Request(url, callback=self.parse_list, meta={'parent': parent, 'label_id': id_value})
            else:
                continue

    def parse_list(self, response):
        parent = response.meta.get('parent')
        label_id = response.meta.get('label_id')
        script_text = response.xpath('//script[contains(text(),"tempList")]/text()').get()
        j_text = re.search(r"let tempList = JSON.parse\(JSON.stringify\((.+?)\)\);\s", script_text)
        if j_text is None:
            self.logger.warning(f"No product list json found, url:{response.url}")
            return
        j_text = j_text.group(1)
        j_text = j_text.replace("'", '"')
        try:
            j_obj: dict = json.loads(j_text)
        except Exception as e:
            self.logger.warning(f"Parse product list json error, url:{response.url} err:{e}")
            return
        list_token = re.search(r"let listToken = '(.+?)';", script_text)
        if list_token is None:
            self.logger.warning(f"No product list token found, url:{response.url}")
            return
        list_token = list_token.group(1)
        if not j_obj:
            return
        j_obj = j_obj[0]
        product_list = j_obj.get('list2', [])
        for item in product_list:
            item['parent'] = parent
            item['prd_url'] = response.url
            searchString = {
                'cas': item['cas'],
                'keywords': "",
                'brandBm': {},
                'spec': {},
                'classMap': {},
                'bpbSourcenm': "",
                'deliveryDate': "",
                'labelId': label_id,
                'pattern': '大图模式',
            }
            form = {
                'searchString': json.dumps(searchString),
                'currentPage': '1',
                'groupValue': j_obj.get('groupValue'),
                'listToken': list_token,
            }
            yield FormRequest('https://www.energy-chemical.com/front/searchProductList.htm', callback=self.parse_detail,
                              method='POST', meta={'parent': parent, 'item': item}, formdata=form)

    def parse_stock_num(self, qty_map: dict):
        try:
            if type(qty_map) is not dict:
                return None
            total_qty = sum([float(x[0]) for x in qty_map.values()])
            return total_qty
        except Exception as e:
            self.logger.warning(f"Parse stock number error, qty_map:{qty_map}")
            return None

    def parse_price(self, price_str: str):
        decoded = html.unescape(price_str)
        trans_table = str.maketrans(self.num_map)
        return decoded.translate(trans_table)

    def parse_detail(self, response):
        try:
            product_obj: dict = json.loads(f'[{response.text}]')
        except Exception as e:
            self.logger.error(f"Parse product detail json error, url:{response.url} err:{e}")
            return
        products = product_obj[0].get('resultList')
        if not products:
            return
        item = response.meta.get('item', {})
        cas = products[0].get('list2', [])[0].get('cas')
        products = products[0].get('list2', [])[0].get('mstList', [])
        for p in products:
            d = {
                "brand": self.brand,
                "parent": response.meta.get('parent'),
                "cat_no": p.get('bpmOrgcd'),
                "en_name": item.get('bpsEnm'),
                "chs_name": p.get('bpmNm'),
                "cas": cas,
                "mf": item.get('bpsMf'),
                "mw": item.get('bpsMw'),
                "prd_url": item.get('prd_url'),
                "img_url": item.get('casImg'),
                "mdl": item.get('bpsMDL'),
                "info2": p.get('storageDesc'),
                "purity": p.get('bpacPurity'),
            }
            yield RawData(**d)
            ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
            pkg_list = p.get('pkgList', [])
            yield SupplierProduct(**ddd)
            for pkg in pkg_list:
                price = self.parse_price(pkg.get('price'))
                dd = {
                    "brand": self.name,
                    "cat_no": d['cat_no'],
                    "package": pkg.get('specMap', {}).get('规格'),
                    "cost": price,
                    "price": price,
                    "currency": 'RMB',
                    "delivery_time": pkg.get('specMap', {}).get('货期'),
                    "purity": d['purity'],
                    "stock_num": self.parse_stock_num(pkg.get('qtyMap')),
                }
                yield ProductPackage(**dd)
                dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
                yield RawSupplierQuotation(**dddd)
