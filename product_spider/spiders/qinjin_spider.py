import re
import time
from hashlib import md5
from urllib.parse import urlencode

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import get_url, is_valid_element
from product_spider.utils.spider_mixin import BaseSpider
import json


class QinjinSpider(BaseSpider):
    name = "qinjin"
    start_urls = ["https://list.qjbzwz.com/list_goods/0/1.html", ]
    base_url = "https://www.qjbzwz.com/"
    brand = '秦境'
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
        rel_urls = response.xpath("//ul[@class='jspop box']//a[contains(@href,'/list_goods/')]/@href").getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        product_urls = response.xpath("//table[@id='product_table']//tr/td/div/a/@href").getall()
        parent = response.xpath(
            "//div[@class='el-breadcrumb']/a[@class='el-breadcrumb__item' and position()=last()]//text()").get()
        for product_url in product_urls:
            product_url = get_url(response.url, product_url)
            yield Request(product_url, self.parse_detail, meta={'parent': parent})

        next_url = response.xpath("//a[@title='下一页']/@href").get()
        if next_url:
            next_url = get_url(response.url, next_url)
            yield Request(next_url, self.parse_list)

    def parse_detail(self, response):
        cat_no = response.xpath("//el-form-item[contains(@label,'产品编号')]/span/text()").get()
        if not cat_no:
            self.logger.warning(f'No cat_no found in page:{response.url}')
            return
        img_url = response.xpath("//div[@class='p-left-top']/img/@src").get()
        if img_url:
            img_url = get_url(response.url, img_url)
        good_obj_raw_str = first(re.findall(r'goodObj: ({[^}]+}),', response.text), '{}')
        d = {
            "brand": self.brand,
            "parent": response.meta.get("parent"),
            "cat_no": cat_no,
            "chs_name": response.xpath(
                "//div[contains(@class,'product_table')]/h2[@class='p-right-title']/span/text()").get(),
            "cas": response.xpath("//el-form-item[contains(@label,'CAS号')]/span/text()").get(),
            "prd_url": response.url,
            "img_url": img_url,
            'purity': response.xpath("//el-form-item[contains(@label,'标准值')]/span/text()").get(),
            'shipping_info': response.xpath("//el-form-item[contains(@label,'运输条件')]/span/text()").get(),
            'info2': response.xpath(
                "//el-form-item[contains(@label,'储存条件')]/span/text()").get(),
            'expiry_date': first(re.findall(r'date:\s?([\d-]+),', good_obj_raw_str), None),
        }
        yield RawData(**d)
        price = first(re.findall(r'sell_price:\s?"?([\d.]+)"?', good_obj_raw_str), None)
        package = response.xpath("//el-form-item[contains(@label,'规格')]/span/text()").get()
        product_id = first(re.findall(r'id:\s?"?(\d+)"?', good_obj_raw_str), None)

        dd = {
            "brand": self.name,
            "cat_no": d['cat_no'],
            "package": package,
            "cost": price,
            "price": price,
            "currency": self.currency,
            'purity': d['purity'],
        }
        if not product_id:
            yield ProductPackage(**d)
        else:
            timestamp = int(time.time() * 1000)
            sign = self.get_sign(product_id, timestamp)
            params = {
                'idStr': product_id,
                'time': timestamp,
                'sign': sign,
            }
            stock_url = f'https://item.qjbzwz.com/official_web/product_front/front/product/async_get_product_detail_by_id?{urlencode(params)}'
            yield Request(url=stock_url, meta={'dd': dd}, callback=self.handle_get_stock_num)

    @staticmethod
    def get_sign(product_id: str, timestamp: int) -> str:
        return md5(f"{product_id}GOODS_INFO_CHECK_KEY{timestamp}".encode()).hexdigest()

    def handle_get_stock_num(self, response):
        dd = response.meta.get('dd')
        try:
            body = response.json().get('body')
        except Exception as e:
            self.logger.warning(f'Get stock num error, url:{response.url}, err:{response.text[:100]}')
            yield ProductPackage(**dd)
            return
        dd['stock_num'] = body.get('number')
        yield ProductPackage(**dd)
