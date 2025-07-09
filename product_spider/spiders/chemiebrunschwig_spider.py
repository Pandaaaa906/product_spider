from scrapy import Request
from scrapy.http import JsonRequest

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import get_url, generate_all_cas_numbers
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class ChemieBrunschwigSpider(BaseSpider):
    name = "chemiebrunschwig"
    start_urls = ["https://www.chemie-brunschwig.ch/	", ]
    base_url = "https://www.chemie-brunschwig.ch/	"
    brand = 'chemiebrunschwig'
    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 6,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
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
    api_url = 'https://www.chemie-brunschwig.ch/actions/sapShop/products/get-products'
    currency = 'EUR'

    def parse(self, response, **kwargs):
        for cas in generate_all_cas_numbers():
            param = {"fulltext": cas, "brandid": "", "skip": 0, "take": 50, "startWithSearch": True,
                     "useOciSession": False}
            yield JsonRequest(self.api_url, data=param, callback=self.parse_list, meta={"cas": cas, 'skip': 0},
                              headers={
                                  'X-Requested-With': "XMLHttpRequest",
                                  'Referer': f"https://www.chemie-brunschwig.ch/shop/?term={cas}&brand=",
                              }, priority=1)

    def parse_list(self, response):
        j_obj = response.json()
        search_cas = response.meta['cas']
        skip = response.meta['skip']

        items = j_obj.get('Items', [])
        self.logger.info(f'item counts:{len(items)} skip:{skip} cas:{search_cas}')
        if not items:
            return

        cas_detail_url = f'https://www.chemie-brunschwig.ch/shop/cas/{search_cas}'
        yield Request(cas_detail_url, callback=self.parse_cas_detail, meta={'items': items, 'cas': search_cas},
                      priority=5, errback=self.handle_no_cas_data)

        skip += len(items)
        param = {"fulltext": search_cas, "brandid": "", "skip": skip, "take": 50, "startWithSearch": False,
                 "useOciSession": False}
        yield JsonRequest(self.api_url, data=param, callback=self.parse_list, meta={"cas": search_cas, 'skip': skip},
                          headers={
                              'X-Requested-With': "XMLHttpRequest",
                              'Referer': f"https://www.chemie-brunschwig.ch/shop/?term={search_cas}&brand=",
                          }, priority=2)

    def extract_item(self, item, cas_data: dict = None):
        if not cas_data:
            cas_data = {}
        brand = item.get('BrandName')
        cat_no = item.get('ItemCode')
        if not brand or not cat_no:
            return None
        package = item.get('Packsize')
        leadtime = item.get('LeadTime')
        delivery_time = None
        if leadtime:
            delivery_time = f'{leadtime} days'
        cas = item['CAS']
        price = item.get('Preis')
        prd_url = f'https://www.chemie-brunschwig.ch/shop/?term={cas}&brand={brand}'
        d = {
            "brand": brand,
            "cat_no": cat_no,
            "en_name": item.get('ItemName'),
            "cas": cas,
            "prd_url": prd_url,
            'mw': cas_data.get("molecular_weight"),
            'mf': cas_data.get("formula"),
            'smiles': cas_data.get("smiles"),
        }
        dd = {
            "brand": brand,
            "cat_no": cat_no,
            "package": package,
            'price': price,
            'cost': price,
            "delivery_time": delivery_time,
            'currency': item.get('Curr'),
        }
        return d, dd

    def handle_no_cas_data(self, failure):
        request = failure.request
        items = request.meta['items']
        for item in items:
            d, dd = self.extract_item(item)
            yield RawData(**d)
            yield ProductPackage(**dd)
            ddd = rawdata_to_supplier_product(d, platform=self.brand, vendor=self.brand)
            yield SupplierProduct(**ddd)
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.brand, vendor=self.brand)
            yield RawSupplierQuotation(**dddd)

    def parse_cas_detail(self, response):
        items = response.meta['items']
        try:
            cas_data: dict = response.json()
        except Exception as e:
            self.logger.error(f'detail response is not json,url:{response.url} response:{response.text[:100]}')
            cas_data = {}
        for item in items:
            d, dd = self.extract_item(item, cas_data)
            yield RawData(**d)
            yield ProductPackage(**dd)
            ddd = rawdata_to_supplier_product(d, platform=self.brand, vendor=self.brand)
            yield SupplierProduct(**ddd)
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.brand, vendor=self.brand)
            yield RawSupplierQuotation(**dddd)
