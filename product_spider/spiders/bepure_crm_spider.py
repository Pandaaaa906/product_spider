import hashlib
import re
import time
import urllib
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import strip
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


def number_2_str(_d):
    if _d is None:
        _d = ''
    else:
        _d = str(_d)
    return _d


class BepureSpider(BaseSpider):
    name = "bepure_crm"
    base_url = "http://www.bepurestandards.com/"
    api_package_url = "https://item.bepurecrm.com/bms_ec_web/site/front/product/async_get_product_detail_by_id"
    start_urls = [
        "https://list.bepurecrm.com/list_goods/0/1.html",
    ]
    page_url_pattern = 'https://list.bepurecrm.com/list_goods/0/{!r}.html'
    brand = 'bepure'
    currency = 'RMB'
    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    }

    def parse(self, response, **kwargs):
        rows = response.xpath("//table[contains(@class,'table product_table')]/tbody//tr")
        for row in rows:
            url = row.xpath(".//a[@class='title-cn goods-detail-a']/@href").get()
            delivery_time = row.xpath(".//div[@class='td_time_name']/text()").get()  # 货期
            if url:
                yield Request(
                    urljoin(response.url, url), callback=self.parse_detail,
                    meta={'delivery_time': delivery_time}
                )
            else:
                self.logger.debug(f"产品url为空 row:{row}")

        # 切换页码
        current_page = response.meta.get('current_page', 1)
        total_page = (m := re.search(r'(?<=total:)\s*(\d+)(?=,)', response.text)) and m.group(1)
        next_url = None
        if current_page and total_page:
            current_page = int(current_page)
            total_page = int(total_page)
            if current_page < total_page:
                next_url = self.page_url_pattern.format(current_page + 1)
        if next_url:
            yield Request(
                url=next_url, callback=self.parse,
                meta={'current_page': current_page + 1, 'total_page': total_page},
                errback=self.handle_error_page
            )

    def handle_error_page(self, failure):
        err_page = failure.request.meta.get('current_page')
        self.logger.warn(f"Get page:{err_page} err, url:{failure.request.url}")
        req = failure.request.copy()
        req.dont_filter = True
        yield req

        total_page = failure.request.meta.get('total_page')
        next_url = self.page_url_pattern.format(err_page + 1)
        yield Request(
            url=next_url, callback=self.parse,
            meta={'current_page': err_page + 1, 'total_page': total_page},
            errback=self.handle_error_page
        )

    def parse_detail(self, response):
        product_id = response.url.split('/')[-1].strip('.html')
        img_rel = (m := re.search(r'(?<=showImg:\s").+(?=")', response.text)) and m.group()
        info_xpath = "//el-form-item[@label={!r}]/span/text()"

        good_obj_str = (m := re.search(r'goodObj:\s?\{([^}]*)}', response.text)) and m.group()
        brand = (m := re.search(r'(?<=brand_name:)\s*"(.+?)"(?=,)', good_obj_str)) and m.group(1)
        expiry_date = (m := re.search(r'(?<=date:)\s*"(.+?)"(?=,)', good_obj_str)) and m.group(1)
        purity = (m := re.search(r'(?<=norm:)\s*"(.+?)"(?=,)', good_obj_str)) and m.group(1)
        delivery_time = (m := re.search(r'(?<=time_name:)\s*"(.+?)"(?=,)', good_obj_str)) and m.group(1)

        parent = response.xpath("//a[@class='el-breadcrumb__item'][last() and position() != 1]/span/text()").get()

        d = {
            'brand': brand,
            'parent': parent,
            'cat_no': (m := re.search(r'(?<=code:)\s*"(.+?)"(?=,)', good_obj_str)) and m.group(1),
            'chs_name': response.xpath("//div/h2[@class='p-right-title']/span/text()").get(),
            'en_name': response.xpath(info_xpath.format('英文名称')).get(),
            'cas': (m := re.search(r'(?<=cas_code:)\s*"(.+?)"(?=,)', good_obj_str)) and m.group(1),
            'mf': formula_trans(response.xpath(info_xpath.format('分子式')).get()),
            'mw': response.xpath(info_xpath.format('分子量')).get(),
            'img_url': img_rel,
            'prd_url': response.url,
            'info1': response.xpath(info_xpath.format('运输条件')).get(),
            'stock_info': response.xpath(info_xpath.format('储存条件')).get(),
            'expiry_date': expiry_date,
            'stock_num': None,
            'purity': purity,
        }
        package = (m := re.search(r'(?<=spec:)\s*"(.+?)"(?=,)', good_obj_str)) and m.group(1)

        yield self.make_package_request(product_id, callback=self.parse_package_info, meta={
            'product': d,
            'package': package,
            'delivery_time': delivery_time,
        })

    def make_package_request(self, product_id, *, callback, meta: dict = None):
        if meta is None:
            meta = {}
        meta["product_id"] = product_id
        now_timestamp = str(int(time.time() * 1000))
        sign_str = f"{product_id}GOODS_INFO_CHECK_KEY{now_timestamp}"
        params = {
            'idStr': product_id,
            'time': now_timestamp,
            'sign': hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        }
        return Request(
            url=f'{self.api_package_url}?{urllib.parse.urlencode(params)}',
            callback=callback,
            meta=meta
        )

    def parse_package_info(self, response):
        j_obj = j.get('body') if (j := response.json()) else None
        d = response.meta.get('product')
        if not j_obj:
            # self.logger.warn(
            #     f'Get price and stock number failed, cat_no: {d.get("cat_no")}, url:{response.request.url} res:{j}'
            # )
            product_id = response.meta.get('product_id')
            meta = response.meta
            meta["retry_times"] = meta.get("retry_times", 0)
            req = self.make_package_request(product_id=product_id, callback=self.parse_package_info, meta=meta)
            req.priority = 999999
            yield req
            return
        d['stock_num'] = number_2_str(j_obj.get('number'))
        sell_price = number_2_str(j_obj.get('sellPrice'))
        package = response.meta.get('package')

        dd = {
            "brand": d['brand'],
            "cat_no": d.get('cat_no'),
            "package": package,
            "price": sell_price,
            "cost": sell_price,
            "currency": self.currency,
            'stock_num': d.get('stock_num'),
            'purity': d.get('purity'),
            'delivery_time': response.meta.get('delivery_time'),
        }
        ddd = rawdata_to_supplier_product(d, self.name, self.name)
        dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
        if self.brand in d['brand']:
            yield RawData(**d)
            yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)
