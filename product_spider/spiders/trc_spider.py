# TODO easily get blocked
import re
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.functions import strip
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


p_reversed_pkg = re.compile(r'^[mM][gGlL]\d+(\.\d+)?$')
p_normalize_pkg = re.compile(r'([mM][gGlL])(\d+(\.\d+)?)')


class TRCSpider(BaseSpider):
    name = "trc"
    brand = 'trc'
    allow_domain = ["trc-canada.com", ]
    start_urls = ["https://www.trc-canada.com/products-listing/", ]
    search_url = "https://www.trc-canada.com/products-listing/?"
    base_url = "https://www.trc-canada.com"

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

    def is_proxy_invalid(self, request, response):
        if response.status in {403, }:
            return True
        return False

    def parse(self, response, **kwargs):
        parent = response.meta.get('parent')
        rel_urls = response.xpath(
            '//div[@class="chemCard"]/a[not(@data-lity)]/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse, meta={"parent": parent})

        next_page = response.xpath('//li[contains(@class, "active")]/following-sibling::li/a[not(i)]/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse, meta={"parent": parent})

    def detail_parse(self, response):
        tmp_format = '//td[contains(text(), {!r})]/following-sibling::td/text()'
        cat_no = strip(response.xpath(tmp_format.format("Catalogue Number")).get())
        rel_img = response.xpath('//div[@id="productImage"]/img/@src').get()
        d = {
            "brand": self.brand,
            # 'parent': response.meta.get("parent"),
            'cat_no': cat_no,
            "en_name": response.xpath(tmp_format.format('Chemical Name')).get(),
            'cas': response.xpath(tmp_format.format('CAS Number')).get(),
            'mf': formula_trans(response.xpath(tmp_format.format('Molecular Formula')).get()),
            'mw': response.xpath(tmp_format.format('Molecular Weight')).get(),
            'stock_info': strip(response.xpath('//li[text()="Inventory Status : "]/b/text()').get()),
            'info1': response.xpath(tmp_format.format('Synonyms')).get(),
            'tags': response.xpath(tmp_format.format('Category')).get(),
            'info5': response.xpath(tmp_format.format('Applications')).get(),

            'img_url': rel_img and urljoin(self.base_url, rel_img),
            'prd_url': response.request.url,  # 产品详细连接
        }
        yield RawData(**d)

        rows = response.xpath('//table[@id="orderProductTable"]/tbody/tr')
        for row in rows:
            package = strip(row.xpath('./td[1]/text()').get())
            if not package:
                continue
            if package == 'Exact Weight Packaging':
                continue
            if p_reversed_pkg.match(package):
                package = p_normalize_pkg.sub(r'\2\1', package)
            cost = strip(row.xpath('./td[3]/text()').get())

            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': package,
                'cost': cost,
                'currency': 'USD',
            }

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                # "parent": d["parent"],
                "en_name": d["en_name"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
                "img_url": d["img_url"],
                "prd_url": d["prd_url"],
            }

            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)
