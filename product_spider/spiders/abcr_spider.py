from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import get_url
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class AbcrSpider(BaseSpider):
    name = "abcr"
    start_urls = ["https://abcr.com/de_en/products", ]
    base_url = "https://abcr.com/"
    brand = 'abcr'
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
    currency = 'EUR'

    def parse(self, response, **kwargs):
        rel_urls = response.xpath("//ul[contains(@class,'submenu')]/li/a/@href").getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.request_list_pages)

    def request_list_pages(self, response):
        list_urls = response.xpath(
            "//div[@class='subcategories-widget-container']/a/@href").getall()
        for rel_url in list_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_urls = response.xpath("//a[@class='product-item-link']/@href").getall()
        parent = response.xpath("//h1[@id='page-title-heading']/*/text()").get()

        if not product_urls:
            return
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, self.parse_detail, meta={"parent": parent})

        next_url = response.xpath("//li[@class='item pages-item-last']/a/@href").get()
        if next_url:
            next_url = get_url(response.url, next_url)
            yield Request(next_url, self.parse_list)

    def parse_detail(self, response):
        img_url = response.xpath(
            '//*[@id="maincontent"]//div[contains(@class,"fotorama__loaded--img")]/img/@src').get()
        parent = response.meta.get('parent')
        if img_url:
            img_url = get_url(response.url, img_url)

        package_table_trs = response.xpath(
            "//table[@id='super-product-table']//tr")
        if len(package_table_trs) < 2:
            self.logger.warning(f'no package table trs')
            return

        headers = [x.strip() for x in package_table_trs[0].xpath(".//th/text()").getall()]
        property_map = {}
        for index, th in enumerate(headers):
            property_map[th] = index + 1

        cat_no = package_table_trs[1].xpath(f"./td[{property_map.get('Article ID', 0)}]/text()").get()
        cas = package_table_trs[1].xpath(f"./td[{property_map.get('CAS', 0)}]/text()").get()
        mdl = package_table_trs[1].xpath(f"./td[{property_map.get('MDL', 0)}]/text()").get()
        if not cat_no:
            return

        mf = response.xpath("//td[contains(text(),'Sum formula')]/following-sibling::*[1]//text()").getall()
        if mf:
            mf = ''.join(mf)
        else:
            mf = None
        d = {
            "brand": self.brand,
            "parent": parent,
            "cat_no": cat_no,
            "en_name": response.xpath("//div[@class='product-info-main']/div//h2/span/text()").get(),
            "cas": cas,
            "mf": mf,
            "mw": response.xpath(
                "//td[contains(text(),'Molecular weight')]/following-sibling::*[1]//text()").get(),
            "img_url": img_url,
            'prd_url': response.url,
            'mdl': mdl,
            'info2': response.xpath(
                "//td[contains(text(),'Storage temperature')]/following-sibling::*[1]//text()").get(),
        }
        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        yield SupplierProduct(**ddd)

        for tr in package_table_trs[1:]:
            pkg = {
                'package': tr.xpath(f".//td[{property_map.get('Unit', 0)}]/text()").get(),
                'price': tr.xpath(f".//td//span[@class='price']/text()").get(),
            }
            price = pkg['price'].replace('€', '') if pkg['price'] else None
            if not pkg['package']:
                continue

            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": pkg['package'].replace(' ', '') if pkg['package'] else None,
                "cost": price,
                "price": price,
                "currency": self.currency,
            }
            yield ProductPackage(**dd)
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
            yield RawSupplierQuotation(**dddd)
