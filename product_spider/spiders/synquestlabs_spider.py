from urllib.parse import urlencode

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import get_url
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class SynquestlabsSpider(BaseSpider):
    name = "synquestlabs"
    start_urls = ["https://synquestlabs.com/", ]
    base_url = "https://synquestlabs.com/"
    brand = 'synquestlabs'
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
    currency = 'USD'

    def parse(self, response, **kwargs):
        'https://synquestlabs.com/ProductV2/SearchResults?page=2&pageSize=20&SearchText=41-'
        for i in range(0, 100):
            for j in range(0, 10):
                keyword = f'{i:02}-{j}'
                params = {
                    'SearchText': keyword,
                    'page': 1,
                    'pageSize': 20,
                }
                yield Request(f'https://synquestlabs.com/ProductV2/SearchResults?{urlencode(params)}',
                              callback=self.parse_list, )

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_urls = response.xpath("//div[@class='row']//a[@class='stretched-link']/@href").getall()
        if not product_urls:
            return
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, self.parse_detail)

        next_url = response.xpath('//a[@class="page-link" and contains(text(),"Next")]/@href').get()
        if next_url:
            next_url = get_url(response.url, next_url)
            yield Request(next_url, self.parse_list)

    def parse_detail(self, response):
        img_url = response.xpath(
            '//div[@id="productImage"]/img/@src').get()
        cas = response.xpath("//td[text()='CAS']/following-sibling::td[1]/span/text()").get()
        cat_no = response.xpath("//td[text()='Product Number']/following-sibling::td[1]/span/text()").get()
        if not cat_no:
            return

        if purity := response.xpath("//td[text()='Purity']/following-sibling::td[1]/span/text()").get():
            purity = purity.replace(' &percnt;', '%')
        d = {
            "brand": self.brand,
            "cat_no": cat_no,
            "en_name": response.xpath("//div[contains(@class,'product-details')]/h2/text()").get(),
            "cas": cas,
            "mf": response.xpath("//td[text()='Molecular Formula']/following-sibling::td[1]/span/text()").get(),
            "purity": purity,
            "mdl": response.xpath("//td[text()='MDL Number']/following-sibling::td[1]/span/text()").get(),
            "mw": response.xpath("//td[text()='Molecular Weight']/following-sibling::td[1]/span/text()").get(),
            "img_url": img_url,
            'prd_url': response.url,
        }
        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        yield SupplierProduct(**ddd)

        headers = response.xpath("//*[@id='pills-pricing']//thead/tr/th/text()").getall()
        headers = [x.strip() for x in headers]
        property_map = {}
        for index, th in enumerate(headers):
            property_map[th] = index + 1
        package_table_trs = response.xpath("//*[@id='pills-pricing']//tbody/tr")
        for tr in package_table_trs:
            price = tr.xpath(f"./td[{property_map.get('Price (USD)', 0)}]//text()").get() or ''
            price = price.strip()
            if not price:
                continue

            package = tr.xpath(f"./td[{property_map.get('Units', 0)}]//text()").get()
            stock_num = tr.xpath(f"./td[{property_map.get('Availability', 0)}]/*/text()").get()

            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": package,
                "cost": price,
                "price": price,
                "stock_num": stock_num,
                "currency": self.currency,
            }
            yield ProductPackage(**dd)
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
            yield RawSupplierQuotation(**dddd)
