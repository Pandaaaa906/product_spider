import re

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import get_url, is_valid_element
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider
import json


class BwrmSpider(BaseSpider):
    name = "bwrm"
    start_urls = ["https://cdn.bzwzzx.com/product/list/all/1.html", ]
    base_url = "https://cdn.bzwzzx.com/"
    brand = '河南万佳'
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
        script_text: str = response.xpath("//script[contains(text(),'paging-resultbox')]/text()").get()
        page_match = re.search(r"pages:\s?(\d+)", script_text)
        total_page = page_match.group(1) if page_match is not None else 1
        self.logger.info(f'Total page:{total_page}')
        yield from self.parse_list(response)
        for i in range(2, int(total_page) + 1):
            next_url = f'https://cdn.bzwzzx.com/product/list/all/{i}.html'
            yield Request(next_url, self.parse_list, )

    def parse_list(self, response):
        self.logger.info(f'Parse list:{response.url}')
        product_urls = response.xpath("//table[@class='tab-resultbox']/tbody/tr//a/@href").getall()
        for product_url in set(product_urls):
            _product_url = get_url(response.url, product_url)
            if _product_url:
                yield Request(_product_url, self.parse_detail, )

    def parse_detail(self, response):
        cat_no = response.xpath("//dt[contains(text(),'编号')]/following-sibling::*[1]//text()").get()
        if not cat_no:
            self.logger.warning(f'No cat_no found in page:{response.url}')
            return
        img_url = response.xpath("//div[@class='product-lfpic']/img/@src").get()
        if img_url:
            img_url = get_url(response.url, img_url)
        d = {
            "brand": self.brand,
            "parent": response.xpath("//div[@class='contain-crumb']/a[position()=last()]//text()").get(),
            "cat_no": cat_no,
            "chs_name": response.xpath("//div[@class='product-itemname']//text()").get(),
            "cas": response.xpath("//dt[contains(text(),'CAS')]/following-sibling::*[1]//text()").get(),
            "prd_url": response.url,
            "img_url": img_url,
            'info2': response.xpath("//dt[contains(text(),'保存条件')]/following-sibling::*[1]//text()").get(),
            'purity': response.xpath("//dt[contains(text(),'标\u00A0准')]/following-sibling::*[1]//text()").get(),
        }
        yield RawData(**d)
        package = response.xpath("//dt[contains(text(),'产品规格')]/following-sibling::*[1]//text()").get()
        price = response.xpath("//dt[contains(text(),'价格')]/following-sibling::*[1]/span/text()").get()
        if price:
            price = price.replace('￥', '')
        dd = {
            "brand": d['brand'],
            "cat_no": d['cat_no'],
            "package": package,
            "cost": price,
            "price": price,
            "currency": self.currency,
            'purity': d['purity'],
            'stock_num': response.xpath("//dt[contains(text(),'库存状态')]/following-sibling::*[1]//text()").get(),
        }
        yield ProductPackage(**dd)
