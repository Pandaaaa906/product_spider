import re
from io import BytesIO
from typing import Dict
from urllib.parse import urljoin

import requests
from fontTools.ttLib import TTFont
from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.spider_mixin import BaseSpider


headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                         'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8'}


class LeyanSpider(BaseSpider):
    name = "leyan"
    base_url = "http://www.leyan.com.cn/"
    start_urls = ['http://www.leyan.com.cn/product-center.html', ]

    custom_settings = {
        # "DOWNLOADER_MIDDLEWARES": {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        'RETRY_HTTP_CODES': [503, 504, 429],
        'RETRY_TIMES': 10,

        'CONCURRENT_REQUESTS': 4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'CONCURRENT_REQUESTS_PER_IP': 4,
    }

    _font_mapping: Dict[str, str.maketrans] = {}
    _font_code_mapping = {
        '-1': '.', '-1#1': '/',
        '-1#2': '0', '-1#3': '1', '-1#4': '2', '-1#5': '3', '-1#6': '4',
        '-1#7': '5', '-1#8': '6', '-1#9': '7', '-1#10': '8', '-1#11': '9',
    }

    def _get_font_map(self, font_name: str):
        font_id = (m := re.search(r'\d+', font_name)) and m.group()
        r = requests.get(f'https://www.leyan.com/_font_/__font__{font_id}.ttf', headers=headers)
        font = TTFont(BytesIO(r.content))
        cmap = font.getBestCmap()
        self._font_mapping[font_name] = str.maketrans({chr(k): self._font_code_mapping[v] for k, v in cmap.items()})

    def get_font_map(self, font_name: str):
        if font_name not in self._font_mapping:
            self._get_font_map(font_name)
        return self._font_mapping[font_name]

    def decode_price(self, value: str, font_name):
        if isinstance(value, str):
            return value.translate(self.get_font_map(font_name))
        return value

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//div[@class="row"]/div/a')
        for a in a_nodes:
            parent = a.xpath('./span/text()').get()
            if parent in {'耗材', '仪器'}:
                continue
            rel = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel), callback=self.parse_list)

    def parse_list(self, response):
        category_urls = response.xpath('//x//a/@href').getall()
        for category_url in category_urls:
            yield Request(urljoin(response.url, category_url), callback=self.parse_list)

        rel_urls = response.xpath('//p[@class="products-thumb"]/a/@href').getall()
        for rel in rel_urls:
            yield Request(urljoin(response.url, rel), callback=self.parse_detail)

        next_page = response.xpath('//a[@aria-label="Next"]/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse_list)

    def parse_detail(self, response):
        tmp = '//div[contains(*/text(), {!r})]/following-sibling::div/*/text()'
        cat_no = response.xpath('//span[@id="catalogNo"]/text()').get()
        rel_img = response.xpath('//input[@id="image"]/@value').get()
        d = {
            'brand': self.name,
            'parent': '_'.join(response.xpath('//li[@class="active"]/following-sibling::li/a/text()').getall()),
            'cat_no': cat_no,
            'en_name': response.xpath('//h2/span/text()').get(),
            'purity': response.xpath('//span[@class="d-purity"]/text()').get(),
            'cas': response.xpath(tmp.format("CAS 号")).get(),
            'mf': ''.join(response.xpath("//div[contains(*/text(), '分子式')]/following-sibling::div/h3//text()").getall()),
            'mw': response.xpath(tmp.format("分子量")).get(),
            'smiles': response.xpath(tmp.format("Smiles Code")).get(),
            'info2': response.xpath(tmp.format("存储条件")).get(),
            'mdl': response.xpath(tmp.format("MDL 号")).get(),

            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }
        yield RawData(**d)

        rows = response.xpath('//div[@class="table-responsive"]//tr[position()!=1]')
        for row in rows:
            if not (package := row.xpath('./td[@id="packing"]/text()').get()):
                continue
            price_span = response.xpath('//*[@class="red" or @class="font-blue"]/span[@class]')
            font_name = price_span.xpath('./@class').get()
            price = self.decode_price(price_span.xpath('./text()').get(), font_name)
            stock_num = row.xpath('./td[@id="stock"]/text()').get()
            dd = {
                'brand': self.name,
                'cat_no': cat_no,
                'package': package,
                'cost': price,
                'currency': 'RMB',
                'delivery_time': 'in-stock' if stock_num == '1' else None,
                'stock_num': row.xpath('./td[@id="stock"]/text()').get(),
            }

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id": f'{self.name}_{d["cat_no"]}_{dd["package"]}',
                "parent": d["parent"],
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
            dddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id":  f'{self.name}_{d["cat_no"]}',
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'discount_price': dd['cost'],
                'price': dd['cost'],
                'currency': dd["currency"],
                'delivery': 'in-stock' if stock_num == '1' else None,
                'stock_num': stock_num,
            }
            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)
            yield RawSupplierQuotation(**dddd)
