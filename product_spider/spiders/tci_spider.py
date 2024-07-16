from itertools import chain
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class TCISpider(BaseSpider):
    """
    有时它就是慢，第一页拿不到，就会超时，整个退出，scraped 0 items，重新跑就好，不需要改代码
    """
    name = "tci"
    base_url = "https://www.tcichemicals.com"
    start_urls = ['https://www.tcichemicals.com/CN/zh/', ]
    brand = 'tci'

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'PROXY_POOL_REFRESH_STATUS_CODES': [403, 504, 503, ],
        'RETRY_TIMES': 10,
        'CONCURRENT_REQUESTS': 8,
        'USER_AGENT': (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
    }

    def parse(self, response, **kwargs):
        rel_urls = response.xpath(
            '//a[@title="产品"]/following-sibling::ul[1]/li[position()>1]/a/@href'
        ).getall()

        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_cat_list)

    def parse_cat_list(self, response):
        rel_urls = response.xpath('//div[@class="card-header"]/a/@href').getall()
        rel_urls_v2 = response.xpath('//ul[contains(@class, "mark")]/li/a/@href').getall()
        for rel_url in chain(rel_urls, rel_urls_v2):
            yield Request(urljoin(response.url, rel_url), callback=self.parse_cat_list)

        nodes = response.xpath("//div[@id = 'product-list-wrap']/div")
        for node in nodes:
            url = node.xpath(".//a/@href").get()
            yield Request(
                url=urljoin(response.url, url),
                callback=self.parse_detail
            )
        if not nodes and rel_urls and rel_urls_v2:
            self.logger.warning(f"没考虑到该页面情况: {response.url}")

    def parse_detail(self, response):
        tmp = '//span[@class={!r}]/text()'
        tmp2 = '//td[contains(text(), {!r})]/following-sibling::td/text()'
        cat_no = response.xpath(tmp.format("code productVal")).get()
        mw = strip(response.xpath(tmp2.format("分子式/分子量")).get())
        img_rel = response.xpath('//div[@data-attr]/@data-attr').get()
        d = {
            'brand': self.brand,
            'parent': '_'.join(response.xpath(
                '//div[@class="subCategory clearfix"][1]//span[@class="startPoint"]//a/text()').getall()),
            'cat_no': cat_no,
            'en_name': ''.join(response.xpath('//h1[@class="name"]//text()').getall()),
            'cas': response.xpath(tmp.format("cas productVal")).get(),
            'mf': ''.join(response.xpath('//span[@id="molecularFormula"]//text()').getall()).replace('_', ''),
            'mw': mw and mw.replace('=', ''),
            'purity': response.xpath(tmp2.format("纯度/分析方法")).get(),
            'appearance': response.xpath(tmp2.format("外观与形状")).get(),
            'info2': response.xpath(tmp2.format("储存温度")).get(),
            'mdl': response.xpath(tmp2.format("MDL编号")).get(),

            'img_url': img_rel and urljoin(self.base_url, img_rel),
            'prd_url': response.url,
        }
        ddd = rawdata_to_supplier_product(d, self.name, self.name)
        yield RawData(**d)
        yield SupplierProduct(**ddd)

        rows = response.xpath('//table[@id="PricingTable"]/tbody/tr')
        for row in rows:
            stock_num = strip(row.xpath('./td[3]/text()').get())
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': row.xpath('./td[1]/text()').get(),
                'delivery_time': '现货' if stock_num != '0' else None,
                'cost': parse_cost(strip(row.xpath('./td[2]/div/text()').get())),
                'stock_num': stock_num,
                'currency': 'RMB',
            }

            yield ProductPackage(**dd)
            if dd.get("cost"):
                dddd = product_package_to_raw_supplier_quotation(d, dd, self.name, self.name)
                yield RawSupplierQuotation(**dddd)
