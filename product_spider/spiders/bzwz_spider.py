from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url
from product_spider.utils.spider_mixin import BaseSpider


class BzwzSpider(BaseSpider):
    name = "bzwz"
    start_urls = ["https://www.bzwz.com/", ]
    base_url = "https://www.bzwz.com/"
    brand = '北方伟业'
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
        target_nav_words = ['标准物质目录', '专项标准物质', '微生物质控品']
        rel_urls = set()
        for target in target_nav_words:
            rel_urls.update(response.xpath(f"//ul[@id='topNav']//li[contains(.,'{target}')]//a/@href").getall())
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        product_urls = response.xpath("//ul[contains(@class,'product_list')]/li//a/@href").getall()
        parent = response.xpath(
            "//div[contains(@class,'pro_li')]/a[position()=last()]/text() | "
            "//div[contains(@class,'pro_category_list') and position()=last()]/a/text()").get()
        for product_url in set(product_urls):
            product_url = get_url(response.url, product_url)
            yield Request(product_url, self.parse_detail, meta={'parent': parent})

        next_url = response.xpath("//a[@title='下一页']/@href").get()
        if next_url:
            next_url = get_url(response.url, next_url)
            if next_url:
                yield Request(next_url, self.parse_list)

    def parse_detail(self, response):
        cat_no = response.xpath(
            "//div[@class='ly_comment_prd_detail']//li[span[contains(text(),'编号')]]/text()[normalize-space()]").get()
        if not cat_no:
            self.logger.warning(f'No cat_no found in page:{response.url}')
            return
        img_url = response.xpath("//div[@class='prd-img']/img/@src").get()
        if img_url:
            img_url = get_url(response.url, img_url)
        d = {
            "brand": self.brand,
            "parent": response.meta.get("parent"),
            "cat_no": cat_no,
            "chs_name": response.xpath("//div[contains(@class,'ly_productdetail_right')]/h1/text()").get(),
            "en_name": response.xpath(
                "//div[contains(@class,'ly_productdetail_right')]/h1/following-sibling::div[1]/text()").get(),
            "cas": response.xpath(
                "//div[@class='ly_comment_prd_detail']//li[span[contains(text(),'CAS')]]/text()[normalize-space()]").get(),
            "prd_url": response.url,
            "img_url": img_url,
            'info2': response.xpath("//td[contains(text(),'存储条件')]/following-sibling::td[1]/text()").get(),
        }
        yield RawData(**d)
        price = response.xpath("//span[@id='product_out_price']/text()").get()
        if price:
            price = price.replace('￥', '')
        package = response.xpath("//li[@id='lot_0']/text()").getall()
        if package:
            package = ''.join(package)
        else:
            return
        dd = {
            "brand": d['brand'],
            "cat_no": d['cat_no'],
            "package": package,
            "cost": price,
            "price": price,
            "currency": self.currency,
        }
        yield ProductPackage(**dd)
