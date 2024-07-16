import re
from datetime import timedelta, datetime
from enum import Enum
from io import BytesIO
from typing import Dict
from urllib.parse import urljoin, urlencode
from uuid import uuid4

import psycopg2
import requests
from fontTools.ttLib import TTFont
from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.sql.leyan_sql import sql_trc_cat_nos
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import dumps
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                         'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8'}


class LeyanStrategy(str, Enum):
    WALKTHROUGH = 'WALKTHROUGH'
    TRC_CAT_NO = 'TRC_CAT_NO'


class LeyanSpider(BaseSpider):
    name = "leyan"
    base_url = "http://www.leyan.com/"
    start_urls = ['http://www.leyan.com/product-center.html', ]

    custom_settings = {
        # "DOWNLOADER_MIDDLEWARES": {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        'PROXY_POOL_REFRESH_STATUS_CODES': [503, 504, 429],
        'RETRY_HTTP_CODES': [500, 503, 504, 429],
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

    def __init__(
            self,
            max_split: int = 16, itersize: int = 20000, ignore_days: int = 60,
            strategy: LeyanStrategy = LeyanStrategy.WALKTHROUGH,
            **kwargs):
        self.max_split = max_split
        self.itersize = itersize
        self.ignore_days = ignore_days
        self.strategy = strategy
        super().__init__(**kwargs)

    def start_requests(self):
        if self.strategy == LeyanStrategy.WALKTHROUGH:
            yield from super().start_requests()
        elif self.strategy == LeyanStrategy.TRC_CAT_NO:
            yield from self.start_trc_requests()

    def start_trc_requests(self):
        db_settings = self.settings["DATABASE"]
        now = datetime.now()
        with psycopg2.connect(**db_settings['params']) as conn:
            with conn.cursor(name=f"leyan_{uuid4().hex}") as cur:
                cur.itersize = self.itersize
                cur.execute(sql_trc_cat_nos, [now - timedelta(days=365), now - timedelta(days=self.ignore_days)])
                for (cat_no,) in cur:
                    yield Request(
                        f"https://www.leyan.com/LY-TRC{cat_no}.html", callback=self.parse_detail,
                    )

    def _get_font_map(self, font_name: str):
        font_id = (m := re.search(r'\d+', font_name)) and m.group()
        tried = 0
        r = None
        while tried < 3:
            try:
                r = requests.get(f'https://www.leyan.com/_font_/__font__{font_id}.ttf', headers=headers)
            except Exception as e:
                self.logger.warn(e)
            if r and r.status_code == 200:
                break
        if not r:
            raise ValueError(f"cant get font_map of: {font_name}")
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
        for a in reversed(a_nodes):
            parent = a.xpath('./span/text()').get()
            if parent in {'耗材', '仪器'}:
                continue
            rel = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel), callback=self.parse_list, priority=999)

    def parse_list(self, response):
        category_urls = response.xpath('//div[@class="oneCate-table"]//a/@href').getall()
        if category_urls:
            self.logger.info(f"scraping page of f{response.url}")
        for category_url in category_urls:
            yield Request(urljoin(response.url, category_url), callback=self.parse_list, priority=999)

        rel_urls = response.xpath('//p[@class="products-thumb"]/a/@href').getall()
        for rel in rel_urls:
            yield Request(urljoin(response.url, rel), callback=self.parse_detail)

        next_page = response.xpath('//a[@aria-label="Next"]/@href').get()
        if not next_page:
            return
        yield Request(urljoin(response.url, next_page), callback=self.parse_list)
        max_page = int(response.xpath('//li[a/@aria-label="Next"]/preceding-sibling::li[1]/a/text()').get())
        cur_page = int(response.xpath('//ul[@class="pagination"]/li[@class="active"]/a/text()').get())
        if cur_page != 1 or max_page < 500:
            return
        self.logger.info(
            f"Splitting page for url: {response.url}, max_page: {max_page}, with max_split: {self.max_split}")
        url, query = urljoin(response.url, next_page).split("?")
        for page in range(max_page // self.max_split, max_page, max_page // self.max_split + self.max_split):
            yield Request(f"{url}?{urlencode({'pageNum': page})}", callback=self.parse_list, priority=999)

    def parse_detail(self, response):
        if response.meta.get('redirect_reasons'):
            self.logger.info(f"product not found, url: {response.meta.get('redirect_urls')}")
            return
        search_result = response.xpath('//div[@class="s-details"]/span//li[1]/a/@href').getall()
        if search_result:
            for rel_url in search_result:
                yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)
            return
        brand = response.xpath('//span[@id="bn"]/text()').get()

        tmp = '//div[contains(*/text(), {!r})]/following-sibling::div[1]/*/text()'
        cat_no = response.xpath('//span[@id="catalogNo"]/text()').get()
        if brand and (brand := brand.lower()) != self.name:
            self.logger.debug(f"found brand {brand=}, {cat_no=}")
        if brand == 'trc' and cat_no:
            cat_no = re.sub(r'^LY-TRC', '', cat_no)
        rel_img = response.xpath('//input[@id="image"]/@value').get()
        attrs = {}
        related_categories = [
            '__'.join(breadcrumb.xpath('./li/a/text()').getall())
            for breadcrumb in response.xpath('//div[./h2[text()="相关分类"]]/following-sibling::div//ol')
        ]
        if related_categories:
            attrs["related_categories"] = related_categories
        d = {
            'brand': brand or self.name,
            'parent': '_'.join(response.xpath('//li[@class="active"]/following-sibling::li/a/text()').getall()),
            'cat_no': cat_no,
            'en_name': response.xpath('//h2/span/text()').get(),
            'purity': response.xpath('//span[@class="d-purity"]/text()').get(),
            'cas': response.xpath(tmp.format("CAS 号")).get(),
            'mf': ''.join(
                response.xpath("//div[contains(*/text(), '分子式')]/following-sibling::div/h3//text()").getall()),
            'mw': response.xpath(tmp.format("分子量")).get(),
            'smiles': response.xpath(tmp.format("Smiles Code")).get(),
            'info2': response.xpath(tmp.format("存储条件")).get(),
            'mdl': response.xpath(tmp.format("MDL 号")).get(),

            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
            'attrs': dumps(attrs),
        }
        if d['brand'] == self.name:
            yield RawData(**d)
        yield SupplierProduct(**rawdata_to_supplier_product(d, self.name, self.name))

        rows = response.xpath('//div[@class="table-responsive"]//tr[position()!=1]')
        pkg_idx = response.xpath(
            'count(//div[@class="table-responsive"]//tr/th[text()="规格"]/preceding-sibling::*)+1').get()
        for row in rows:
            if not (package := row.xpath(f'./td[position()={pkg_idx!r}]/text()').get()):
                continue
            price_span = row.xpath('.//*[@class="red" or @class="font-blue"]//span[@class]')
            font_name = price_span.xpath('./@class').get()
            try:
                price = self.decode_price(price_span.xpath('./text()').get(), font_name)
            except Exception as e:
                self.logger.error(e)
                continue
            stock_num = row.xpath('./td[@id="stock"]/text()').get()
            dd = {
                'brand': d['brand'],
                'cat_no': cat_no,
                'package': package,
                'cost': parse_cost(price),
                'currency': 'RMB',
                'delivery_time': 'in-stock' if stock_num == '1' else None,
                'stock_num': row.xpath('./td[@id="stock"]/text()').get(),
            }
            if d['brand'] == self.name:
                yield ProductPackage(**dd)
            if not dd['cost']:
                continue
            yield RawSupplierQuotation(**product_package_to_raw_supplier_quotation(d, dd, self.name, self.name))
