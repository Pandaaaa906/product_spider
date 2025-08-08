from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url
from product_spider.utils.spider_mixin import BaseSpider


class CombiBlocksSpider(BaseSpider):
    name = "combiblocks"
    start_urls = ["https://combi-blocks.com/", ]
    base_url = "https://combi-blocks.com/"
    brand = 'combiblocks'
    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'CONCURRENT_REQUESTS_PER_IP': 8,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        'RETRY_HTTP_CODES': [403],
        'RETRY_TIMES': 10,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }
    currency = 'USD'

    def parse(self, response, **kwargs):
        rel_urls = response.xpath(
            "//ul[contains(@class,'multi-column-dropdown')]/li/a/@href").getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_urls = response.xpath("//table[@id='listing']/tbody/tr//a/@href").getall()
        parent = response.xpath("//*[@class='content-head']//text()").get()

        if not product_urls:
            return
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, self.parse_detail, meta={"parent": parent})

        next_url = response.xpath("//ul[@class='pagination']/li/a[contains(text(),'»')]/@href").get()
        if next_url:
            yield Request(next_url, self.parse_list)

    def parse_detail(self, response):
        img_url = response.xpath("//td[@class='structure']/img/@src").get()
        parent = response.meta.get('parent')
        if img_url:
            img_url = get_url(response.url, img_url)
        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": response.xpath(
                "//td[contains(.,'Catalog No.')]/following-sibling::*[1]//text()").get(),
            "en_name": response.xpath("//td[contains(.,'Name')]/following-sibling::*[1]//text()").get(),
            "cas": response.xpath(
                "//td[contains(text(),'CAS number')]/following-sibling::*[1]//text()").get(),
            "mf": response.xpath("//td[contains(text(),'Formula')]/following-sibling::*[1]//text()").get(),
            "mw": response.xpath("//td[contains(text(),'FW')]/following-sibling::*[1]//text()").get(),
            "img_url": img_url,
            'purity': response.xpath("//td[contains(text(),'Purity')]/following-sibling::*[1]//text()").get(),
            'shipping_info': response.xpath("//td[contains(text(),'Shipping')]/following-sibling::*[1]//text()").get(),
            'info2': response.xpath("//td[contains(text(),'Storage')]/following-sibling::*[1]//text()").get(),
            'mdl': response.xpath("//td[contains(text(),'MFCD number')]/following-sibling::*[1]//text()").get(),
            'prd_url': response.url,
        }
        yield RawData(**d)

        package_table_trs = response.xpath("//table[@id='price-table']//tr")

        headers = [x.strip() for x in package_table_trs[0].xpath(".//th/text()").getall()]
        property_map = {}
        for index, th in enumerate(headers):
            property_map[th] = index + 1

        for tr in package_table_trs[1:]:
            pkg = {
                'package': tr.xpath(f".//td[{property_map.get('Unit', 0)}]/text()").get(),
                'price': tr.xpath(f".//td[{property_map.get('Price $', 0)}]/text()").get(),
                'stock': tr.xpath(f".//td[{property_map.get('Stock', 0)}]/*/text()").get(),
            }
            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": pkg['package'].replace(' ', '') if pkg['package'] else None,
                "cost": pkg['price'],
                "price": pkg['price'],
                "stock_num": pkg['stock'],
                "currency": self.currency,
            }
            yield ProductPackage(**dd)
