import json

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import get_url
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class A2bchemSpider2(BaseSpider):
    name = "a2bchem2"
    brand = "a2bchem"
    allow_domain = ["a2bchem.com"]
    start_urls = ["https://www.a2bchem.com/", ]
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
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }

    def parse(self, response, **kwargs):
        rel_urls = response.xpath(
            "//li[@class='dropdown']/a[text()='PRODUCTS']/following-sibling::*[1]//li/a/@href").getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        product_urls = response.xpath("//tr[contains(@class,'mouse')]/@onclick").getall()
        for product_url in product_urls:
            product_url = product_url.replace("goUrl('", '').replace("')", '')
            yield Request(product_url, self.parse_detail)

    def parse_detail(self, response):
        cat_no = response.xpath("//td[contains(text(), 'Catalog Number:')]/following-sibling::td/text()").get()
        mdl = response.xpath("//td[contains(text(), 'MDL Number:')]/following-sibling::td/text()").get()
        inchl = response.xpath("//td[contains(text(), 'InChl:')]/following-sibling::td/text()").get()
        inchl_key = response.xpath("//td[contains(text(), 'InChl Key:')]/following-sibling::td/text()").get()
        iupac = response.xpath("//td[contains(text(), 'IUPAC Name:')]/following-sibling::td/text()").get()

        prd_attrs = json.dumps({
            "inchl": inchl,
            "inchl_key": inchl_key,
            "iupac": iupac,
        })

        d = {
            "brand": self.brand,
            "parent": response.xpath("//div[@class='crumbs']//a[last()]/text()").get(),
            "cat_no": cat_no,
            "en_name": response.xpath("//td[contains(text(), 'Chemical Name:')]/following-sibling::td/text()").get(),
            "cas": response.xpath("//td[contains(text(), 'CAS Number:')]/following-sibling::td/text()").get(),
            "smiles": response.xpath("//td[contains(text(), 'SMILES:')]/following-sibling::td/text()").get(),
            "mf": response.xpath("//td[contains(text(), 'Molecular Formula:')]/following-sibling::td/text()").get(),
            "mw": response.xpath("//td[contains(text(), 'Molecular Weight:')]/following-sibling::td/text()").get(),
            "prd_url": response.url,
            "img_url": response.xpath("//div[@class='pd_f1']/img/@src").get(),
            "info1": response.xpath("//td[contains(text(), 'IUPAC Name:')]/following-sibling::td/text()").get(),
            "mdl": mdl,
            "attrs": prd_attrs,
        }
        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, platform=self.brand, vendor=self.brand)
        yield SupplierProduct(**ddd)

        rows = response.xpath("//table[@class='q_table']/tbody/tr")
        for row in rows:
            original_price = row.xpath(".//td[4]/text()").get()
            price = row.xpath(".//td[5]/text()").get('')
            stock_info = row.xpath(".//td[3]/text()").get()
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": row.xpath(".//td[1]/text()").get(),
                "cost": parse_cost(price),
                "price": parse_cost(original_price),
                "currency": 'USD',
                "delivery_time": stock_info,
            }
            yield ProductPackage(**dd)

            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.brand, vendor=self.brand)
            yield RawSupplierQuotation(**dddd)
