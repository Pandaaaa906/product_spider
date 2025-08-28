import json

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import get_url
from product_spider.utils.spider_mixin import BaseSpider


class RuiweierSpiderSpider(BaseSpider):
    name = "ruiweier"
    brand = "ruiweier"
    start_urls = ["https://shop.ruiweier.cn/", ]
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
            "//li[@class='dropdown more-menu']/a[@class='dropdown-toggle']/@href").getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        parent = response.xpath("//h2[@class='page-heading']/span/text()").get()
        product_urls = response.xpath("//a[@class='product-image']/@href").getall()
        for product_url in product_urls:
            product_url = get_url(response.url, product_url)
            if product_url:
                yield Request(product_url, self.parse_detail, meta={'parent': parent})

        next_url = response.xpath("//ul[@class='pagination']/li[last()]/a/@href").get()
        next_url = get_url(response.url, next_url)
        if next_url:
            yield Request(next_url, self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        base_xpath = "//div[@id='product_tabs_description']//tr/td[contains(text(), {!r})]/following-sibling::td[1]"
        cas = cat_no = response.url.split('/')[-1].strip(".html")
        if not cas:
            self.logger.warning(f'No cas found in:{response.url}')
            return
        mdl = response.xpath(base_xpath.format('MDL Number')).xpath('string(.)').get()
        inchl_key = response.xpath(base_xpath.format('InChIKey')).xpath('string(.)').get()
        img_url = response.xpath('//img[@id="product-zoom"]/@src').get()
        img_url = get_url(response.url, img_url)
        prd_attrs = json.dumps({
            "inchl_key": inchl_key,
        })
        storage_condition = response.xpath(base_xpath.format('储存条件')).xpath('string(.)').get()
        d = {
            "brand": self.brand,
            "parent": response.meta.get('parent'),
            "cat_no": cat_no,
            "en_name": response.xpath(base_xpath.format('英文名')).xpath('string(.)').get(),
            "chs_name": response.xpath("//div[@class='product-name']").xpath('string(.)').get(),
            "cas": cas,
            "smiles": response.xpath(base_xpath.format('smiles')).xpath('string(.)').get(),
            "mf": response.xpath(base_xpath.format('分子量')).xpath('string(.)').get(),
            "mw": response.xpath(base_xpath.format('分子式')).xpath('string(.)').get(),
            "prd_url": response.url,
            "img_url": img_url,
            "mdl": mdl,
            "attrs": prd_attrs,
            "info2": storage_condition,
        }
        yield RawData(**d)

        # TODO 哪有价格?
