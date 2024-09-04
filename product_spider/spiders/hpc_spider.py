import re

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class HPCSpider(BaseSpider):
    name = "hpc"
    base_url = "https://www.hpc-standards.com/"
    start_urls = ["https://www.hpc-standards.com/shop/", ]

    custom_settings = {
        # "DOWNLOADER_MIDDLEWARES": {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        # 'PROXY_POOL_REFRESH_STATUS_CODES': [403, 500, 302],
        'RETRY_TIMES': 20,
        'CONCURRENT_REQUESTS': 16,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/127.0.0.0 Safari/537.36'
        )
    }
    def parse(self, response, **kwargs):
        urls = response.xpath('//li[@class="second-level"]/a/@href').getall()
        for url in urls:
            yield Request(url, callback=self.parse_list, priority=5)

    def parse_list(self, response):
        urls = response.xpath('//td/p/a[@name]/@href').getall()
        parent = response.xpath('//h1/text()').get()
        for url in urls:
            yield Request(url, callback=self.parse_detail, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td//text()'
        cat_no = response.xpath(tmp.format("Item number")).get()
        quantity = response.xpath(tmp.format("Quantity")).get()
        if quantity:
            quantity = re.sub(r'^\d+[Xx]', '', quantity)
        concentration = response.xpath(tmp.format("Concentration")).get()
        solvent = response.xpath(tmp.format("Solvent")).get()
        package = f'{quantity}; {concentration} in {solvent}' if concentration else quantity
        mw = response.xpath(tmp.format("Molecular Weight (g/mol)")).get()
        if not mw:
            mw = response.xpath(tmp.format("Molecular weight")).get()
        d = {
            'brand': self.name,
            'parent': response.meta.get('parent'),
            'cat_no': cat_no,
            'en_name': response.xpath('//h1/text()').get(),
            'cas': response.xpath(tmp.format("CAS")).get(),
            'mf': response.xpath(tmp.format("Formula")).get(),
            'mw': mw,
            'purity': concentration,
            'info2': response.xpath(tmp.format("storage conditions")).get(),
            'info3': package,
            'img_url': response.xpath('//a[@class="fancybox"]/img/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
        dd = {
            'brand': self.name,
            'cat_no': cat_no,
            'package': package,
            'purity': concentration,
        }
        yield ProductPackage(**dd)
