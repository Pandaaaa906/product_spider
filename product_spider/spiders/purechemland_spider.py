from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import get_url
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class PurechemlandSpider(BaseSpider):
    name = "purechemland"
    start_urls = ["https://purechemland.com/", ]
    base_url = "https://purechemland.com/"
    brand = 'purechemland'
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
    currency = 'RMB'

    def parse(self, response, **kwargs):
        rel_urls = response.xpath("//ul/li/a[contains(@href,'/product_types/')]/@href").getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        product_trs = response.xpath("//div[@class='table_form']/table/tbody/tr")
        parent = response.xpath("//div[@class='txt']/h3//text()").get()

        headers = response.xpath("//div[@class='table_form']/table/thead//th/text()").getall()
        headers = [x.strip() for x in headers]
        property_map = {}
        for index, th in enumerate(headers):
            property_map[th] = index

        if not product_trs:
            return
        for tr in product_trs:
            tds = tr.xpath('./td')
            cat_no: str = tds[property_map.get('货号')].xpath('.//text()').get()

            if cat_no:
                cat_no = cat_no.replace('PCL-#-', '')
            else:
                self.logger.warning('Cat No Not found!')
                continue
            d = {
                "brand": self.brand,
                "parent": parent,
                "cat_no": cat_no,
                "chs_name": f'{tds[property_map.get("产品名称")].xpath('.//text()').get()} {tds[property_map.get("产品描述")].xpath('.//text()').get()}',
                "cas": tds[property_map.get('CAS号')].xpath('.//text()').get(),
                'prd_url': response.url,
            }
            yield RawData(**d)
            package = tds[property_map.get('规格')].xpath('.//text()').get()
            if package:
                packages = package.split(',')
                for p in packages:
                    dd = {
                        "brand": self.brand,
                        "cat_no": d['cat_no'],
                        "package": p,
                        "currency": self.currency,
                    }
                    yield ProductPackage(**dd)

        next_url = response.xpath("//li[@class='pageItem pageItemActive']/following-sibling::li[1]/a/@href").get()
        if next_url:
            next_url = get_url(response.url, next_url)
            yield Request(next_url, self.parse_list)
