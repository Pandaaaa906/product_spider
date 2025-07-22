import re

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import get_url, is_valid_element
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider
import json


class BolindaSpider(BaseSpider):
    name = "bolinda"
    start_urls = ["https://www.bolinda.shop/products", ]
    base_url = "https://www.bolinda.shop"
    brand = 'bolinda'
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
        rel_urls = response.xpath(
            "//div[contains(@class,'allcate')]//li/a[contains(@href,'types')]/@href").getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        self.logger.info(f'url:{response.url}')
        product_urls = response.xpath(
            "//div[contains(@class,'product-container')]/div[@class='item-pic']/a/@href").getall()
        parent = response.xpath('//th[text()="类别"]/following-sibling::td[1]/a/text()').get()
        for product_url in product_urls:
            product_url = get_url(response.url, product_url)
            yield Request(product_url, self.parse_detail, meta={'parent': parent})

        next_url = response.xpath("//i[@class='tcfont icon-xiangyoujiantou']/parent::a[1]/@href").get()
        if next_url:
            next_url = get_url(response.url, next_url)
            yield Request(next_url, self.parse_list)

    def validate_mf(self, mf: str, title: str):
        for c in ['X', 'D', 'J', 'Q']:
            if c in mf.upper():
                mf = None
                break
        if mf:
            mf = formula_trans(mf)
        if mf and len(mf) <= 2 and not is_valid_element(mf):
            mf = None
        if mf == 'H' and 'pH' in title:
            mf = None
        if mf == 'B' and '硼' not in title:
            mf = None
        return mf

    def parse_detail(self, response):
        script_text = response.xpath("//script[contains(text(),'window.CurrentProduct = ')]/text()").get()
        j_text = re.search(r"window.CurrentProduct = (.+?);\s+yhsd.ready", script_text)
        if j_text is None:
            self.logger.warning(f'No product info found in page:{response.url}')
            return
        try:
            j_obj: dict = json.loads(j_text.group(1))
        except Exception as e:
            self.logger.warning(f'Parse product info error in page:{response.url}', exc_info=e)
            return

        title = j_obj.get('page_title')
        mf_match = re.search(r"((([A-Z][a-z]?)([₀₁₂₃₄₅₆₇₈₉]+)?([.·]\d?)?)+)(?=[\s】]|$)", title)
        mf = mf_match.group(1) if mf_match else None
        if not mf:
            mf_match = re.search(
                r"(((\(([A-Za-z₀₁₂₃₄₅₆₇₈₉]+)+\)[₁₂₃₄₅₆₇₈₉])?[A-Za-z₀₁₂₃₄₅₆₇₈₉]+)+(\(([A-Za-z₀₁₂₃₄₅₆₇₈₉]+)+\)[₁₂₃₄₅₆₇₈₉]))",
                title)
            mf = mf_match.group(1) if mf_match else None
        if mf:
            mf = self.validate_mf(mf, title)

        cas_match = re.search(r"CAS[:：]([\d\-]+)", title)
        cas = cas_match.group(1) if cas_match else None
        image = None
        if images := j_obj.get('images'):
            image = images[0].get('src', '').strip('//')
            if not image.startswith('http'):
                image = "https://" + image
        d = {
            "brand": self.brand,
            "parent": response.meta.get("parent"),
            "cat_no": j_obj.get('handle'),
            "chs_name": j_obj.get('name'),
            "cas": cas,
            'mf': mf,
            "prd_url": response.url,
            "img_url": image,
        }
        yield RawData(**d)
        for v in j_obj.get('variants', []):
            purity = v.get('option_1')
            if not purity or '定制' in purity:
                continue
            package = f'{v.get("option_2")} {purity}'
            price = v.get('price', 0) / 100
            dd = {
                "brand": self.name,
                "cat_no": 'cat_no',
                "package": package,
                "cost": price,
                "price": price,
                "currency": self.currency,
                'purity': purity,
                'stock_num': v.get('stock'),
            }
            yield ProductPackage(**dd)
