from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url
from product_spider.utils.spider_mixin import BaseSpider


class AlfaChemSpider(BaseSpider):
    name = "alfachem"
    start_urls = ["https://www.alfa-chemistry.com/products.html", ]
    base_url = "https://www.alfa-chemistry.com/"
    brand = 'alfachemistry'
    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        'RETRY_ENABLED': True,
        'RETRY_HTTP_CODES': [403, 202],
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
        rel_urls = response.xpath(
            "//div[@class='side-wrap left-nav']//li/a/@href").getall()
        if not rel_urls:
            self.logger.warning(f'No list url found, http code:{response.status}')
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.request_list_pages)

    def request_list_pages(self, response):
        list_urls = response.xpath(
            "//div[@class='product-tags']//span/a/@href").getall()
        for rel_url in list_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_urls = response.xpath("//div[contains(@class,'row')]//h2/a/@href").getall()
        parent = response.xpath("//div[@class='page-title']//div[contains(@class,'row')]//h1/text()").get()

        if not product_urls:
            return
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, self.parse_detail, meta={"parent": parent})

        next_url = response.xpath("//ul[@class='pagination']/li/a[contains(text(),'»')]/@href").get()
        if next_url:
            next_url = get_url(response.url, next_url)
            yield Request(next_url, self.parse_list)

    def parse_detail(self, response):
        img_url = response.xpath("//div[@class='product-image-wrap']//img/@src").get()
        parent = response.meta.get('parent')
        if img_url:
            img_url = get_url(response.url, img_url)
        d = {
            "brand": self.brand,
            "parent": parent,
            "cat_no": response.xpath(
                "//div[@class='row']/div[contains(.,'Catalog Number')]/following-sibling::*[1]//text()").get(),
            "en_name": response.xpath("//div[@class='page-title']/*/text()").get(),
            "cas": response.xpath("//li[@class='cat']/text()").get(),
            "mf": response.xpath(
                "//div[@class='row']/div[contains(.,'Molecular Formula')]/following-sibling::*[1]//text()").get(),
            "mw": response.xpath(
                "//div[@class='row']/div[contains(.,'Molecular Weight')]/following-sibling::*[1]//text()").get(),
            "img_url": img_url,
            'purity': response.xpath("//li[@class='purity']/text()").get(),
            'prd_url': response.url,
            'appearance': response.xpath(
                "//div[@class='row']/div[contains(.,'Appearance')]/following-sibling::*[1]//text()").get(),
        }
        yield RawData(**d)
