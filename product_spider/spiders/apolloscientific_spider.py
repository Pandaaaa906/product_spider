from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url
from product_spider.utils.spider_mixin import BaseSpider


class ApolloScientificSpider(BaseSpider):
    name = "apolloscientific"
    start_urls = ["https://www.apolloscientific.co.uk/	", ]
    base_url = "https://www.apolloscientific.co.uk/	"
    brand = 'apolloscientific'
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
    currency = 'GBP'

    def parse(self, response, **kwargs):
        rel_urls = response.xpath(
            "//a[contains(.,'Products')]/following-sibling::ul/li/ul/li[contains(@class,'menu-item')]/a/@href").getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.request_list_pages)

    def request_list_pages(self, response):
        rel_urls = response.xpath(
            "//div[contains(@class,'list-group')]/a/@href").getall()
        # 爬取其他列表页的
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

        # 爬取本列表页的
        self.parse_list(response)

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_urls = response.xpath("//div[@class='row']/div/h2/a/@href").getall()
        parent = response.xpath("//div[@class='card-header']/*/text()").get()

        if not product_urls:
            return
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, self.parse_detail, meta={"parent": parent})

        next_url = response.xpath("//li[@class='page-item']/a[@rel='next']/@href").get()
        if next_url:
            yield Request(next_url, self.parse_list)

    def parse_detail(self, response):
        img_url = response.xpath("//img[@itemprop='image']/@src").get()
        parent = response.meta.get('parent')
        if img_url:
            img_url = get_url(response.url, img_url)
        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": response.xpath(
                "//span[@class='product-catalogue-number']//text()").get(),
            "en_name": response.xpath("//h1[@itemprop='name']/text()").get(),
            "cas": response.xpath(
                "//*[@itemprop='productID']/text()").get(),
            "img_url": img_url,
            'mdl': response.xpath(
                "//dt[contains(text(),'MDL Number')]/following-sibling::*[1]//text()").get(),
            'purity': response.xpath("//dt[contains(text(),'Purity')]/following-sibling::*[1]//text()").get(),
            'prd_url': response.url,
        }
        yield RawData(**d)

        package_table_trs = response.xpath("//div[@id='product-pack-table']//div/form/div")

        for tr in package_table_trs:
            stock_items = tr.xpath(".//div/span[contains(@class,'text-color-light-grey')]/text()").getall()[:2]
            stock = ""
            if len(stock_items) == 2:
                stock = f"UK:{stock_items[0].strip()} US:{stock_items[1].strip()}"
            pkg = {
                'package': tr.xpath(f".//*[@itemprop='sku']/text()").get(),
                'price': tr.xpath(f".//*[@itemprop='Price']/text()").get(),
            }
            price = pkg['price'].replace('£', '') if pkg['price'] else None
            if not price:
                continue
            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": pkg['package'].replace(' ', '') if pkg['package'] else None,
                "cost": price,
                "price": price,
                "stock_num": stock,
                "currency": self.currency,
            }
            yield ProductPackage(**dd)
