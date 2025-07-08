from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import get_url, generate_all_cas_numbers
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class ChemtronicaSpider(BaseSpider):
    name = "chemtronica"
    start_urls = ["https://chemtronica.com/", ]
    base_url = "https://chemtronica.com/"
    brand = 'chemtronica'
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
    currency = 'EUR'

    def parse(self, response, **kwargs):
        for cas in generate_all_cas_numbers():
            url = f'https://chemtronica.com/en/chemicals?cas_number={cas}'
            yield Request(url, callback=self.parse_list, meta={"cas": cas})

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_divs = response.xpath("//div[contains(@class,'result') and @data-result-view-type='regular']")

        for index, div in enumerate(product_divs):
            extra_div = response.xpath(f"//div[@id='extras-{index}']")
            cat_no: str = div.xpath(".//div[text()='Article']/following-sibling::div[1]/text()").get()
            if not cat_no:
                continue
            package = div.xpath(".//div[text()='Unit size']/following-sibling::div[1]/text()").get()
            delivery = div.xpath(".//div[text()='Estimated Delivery Time']/following-sibling::div[1]/text()").get(),
            price: str = div.xpath(".//div[text()='Price']/following-sibling::div[1]/text()").get()
            if price:
                price = price.split(' ')[0]

            d = {
                "brand": self.brand,
                "cat_no": cat_no,
                "en_name": div.xpath(".//div[text()='Description']/following-sibling::div[1]/text()").get(),
                "cas": response.meta['cas'],
                'prd_url': response.url,
            }
            if extra_div:
                supplier = extra_div.xpath(".//div[text()='Supplier']/following-sibling::div[1]/text()").get()
                if supplier and supplier != '-':
                    d['brand'] = supplier
                mdl = extra_div.xpath(".//div[text()='MFCD']/following-sibling::div[1]/text()").get()
                if mdl and mdl != '-':
                    d['mdl'] = mdl
                mf = extra_div.xpath(".//div[text()='Molecular formula']/following-sibling::div[1]/text()").get()
                if mf and mf != '-':
                    d['mf'] = mf
                smiles = extra_div.xpath(".//div[text()='Synonym']/following-sibling::div[1]/text()").get()
                if smiles and smiles != '-':
                    d['smiles'] = smiles
                mw = extra_div.xpath(".//div[text()='Molecular weight']/following-sibling::div[1]/text()").get()
                if mw and mw != '-':
                    d['mw'] = mw.replace(',', '.')
                storage = extra_div.xpath(".//div[text()='Risks, storage']/following-sibling::div[1]/text()").get()
                if storage and storage != '-':
                    d['info2'] = storage

            yield RawData(**d)
            ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
            yield SupplierProduct(**ddd)

            dd = {
                "brand": d['brand'],
                "cat_no": d['cat_no'],
                "package": package,
                "cost": price,
                "price": price,
                "delivery_time": delivery,
                "currency": self.currency,
            }
            yield ProductPackage(**dd)
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
            yield RawSupplierQuotation(**dddd)

        next_url = response.xpath(
            "//span[contains(@class,'page active')]/parent::*[1]/following-sibling::a[1]/@href").get()
        if next_url:
            next_url = get_url(response.url, next_url)
            yield Request(next_url, self.parse_list, meta={'cas': response.meta['cas']})
