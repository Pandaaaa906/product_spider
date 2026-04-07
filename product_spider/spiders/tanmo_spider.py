import hashlib
import re
import time
from ast import literal_eval
from os import getenv
from urllib.parse import urlencode

from demjson3 import decode
import execjs
from lxml import etree
from more_itertools import first
from scrapy import Request, FormRequest

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.middlewares.handle521 import get_params, encrypt_cookies, hash_d
from product_spider.utils.functions import strip
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider

TANMO_USER = getenv('TANMO_USER')
TANMO_PWD = getenv('TANMO_PWD')

TANMO_OTHER_BRANDS = {
    '上海计量院',
    '中国农业科学院',
    '中国计量院',
    '四川中测',
    '国家地质中心',
    '国家有色金属',
    '天津农业部',
    '安科院',
    '核工业部',
    '水科院',
    '海洋二所',
    '海洋环境',
    '环保标样所',
    '科工委',
    '中国'
}


def is_tanmo(brand: str):
    if not brand:
        return False
    return brand == 'tanmo' or '坛墨' in brand or brand.lower().startswith('tm')


class TanmoSpider(BaseSpider):
    name = "tanmo"
    base_url = "https://www.gbw-china.com/"
    start_urls = ["https://www.gbw-china.com/", ]
    login_url = 'https://www.gbw-china.com/official_web/customer_front/contacts_login/do_login_password'
    other_brands = set()

    handle_httpstatus_list = [521]

    # custom_settings = {
    #     'DOWNLOADER_MIDDLEWARES': {
    #         'product_spider.middlewares.handle521.Cookie521Middleware': 100,
    #     }
    # }
    def _start_requests(self):
        if TANMO_USER and TANMO_PWD:
            yield FormRequest(
                self.login_url,
                formdata={
                    'phone': TANMO_USER,
                    'password': TANMO_PWD,
                },
                callback=self.after_login,
            )
        else:
            yield from super().start_requests()

    def after_login(self, response):
        yield from super().start_requests()

    def parse(self, response, **kwargs):
        a_nodes = response.xpath(
            '//a[parent::dd|parent::dt[not(following-sibling::dd/a)]][contains(@href, "list_good")]')
        for a in a_nodes:
            url = a.xpath('./@href').get()
            yield Request(url, callback=self.parse_list)

    def handle_521(self, response, callback):
        n = response.meta.get('n', 0)
        if 'document.cookie' in response.text:
            js_clearance = re.findall('cookie=(.*?);location', response.text)[0]
            result = execjs.eval(js_clearance).split(';')[0]
            k, v, *_ = result.split('=')
            yield Request(response.url, callback=callback, cookies={k: v}, meta={'n': n + 1},
                          dont_filter=True)
        else:
            params = get_params(response)
            chars = params['chars']
            bts = params['bts']
            ha = params['ha']
            ct = params['ct']
            hash_func = hash_d[ha]
            clearance = encrypt_cookies(chars, bts, ct, hash_func)
            yield Request(response.url, callback=callback,
                          cookies={'__jsl_clearance_s': clearance}, meta={'n': n + 1}, dont_filter=True
                          )

    def parse_list(self, response):
        if response.status == 521:
            yield from self.handle_521(response, self.parse_list)
            return
        rows = response.xpath('//table[@id="product_table"]/tbody/tr')
        for row in rows:
            url = row.xpath('./td[1]//a/@href').get()
            yield Request(url, callback=self.parse_detail)

        cur_page = first(re.findall(r'pno: (\d+),', response.text), None)
        total_page = first(re.findall(r'total: (\d+),', response.text), None)
        if cur_page is None or total_page is None:
            return
        if int(cur_page) >= int(total_page):
            return
        next_page = re.sub(r'\d+(?=\.html)', str(int(cur_page) + 1), response.url)
        yield Request(next_page, callback=self.parse_list)

    def parse_detail(self, response):
        time.sleep(3)
        if response.status == 521:
            yield from self.handle_521(response, callback=self.parse_detail)
            return
        parent = strip(response.xpath("//a[@class='el-breadcrumb__item'][last()]//span/text()").get(), '')
        tmp = '//el-form-item[contains(@label, {!r})]/span/text()'
        brand = strip(response.xpath(tmp.format("品牌")).get(), "").lower()
        if is_tanmo(brand):
            brand = self.name
        cat_no = strip(response.xpath(tmp.format("产品编号")).get())

        good_obj_raw_str = first(re.findall(r'goodObj: ({[^}]+}),', response.text), '{}')
        try:
            good_obj = decode(good_obj_raw_str)
        except Exception as e:
            # handle illegal quoted like： spec: "1mg*("*"指规格随批次变化)",
            good_obj_raw_str = re.sub(r'(?<!: )"(.*?)(?=")', lambda m: '{}'.format(m.group(0).replace('"', r'\"')),
                                      good_obj_raw_str)
            good_obj = decode(good_obj_raw_str)

        chs_name = strip(''.join(response.xpath('//h2[@class="p-right-title"]//text()').getall()))
        cas = strip(response.xpath(tmp.format("CAS号")).get())
        stock_info = good_obj.get('number', 0)
        expiry_date = good_obj.get('date', 0)

        purity = strip(response.xpath(tmp.format("标准值")).get())
        info2 = strip(response.xpath(tmp.format("储存条件")).get())
        package = strip(response.xpath(tmp.format("规格")).get(''))
        info4 = good_obj.get('price', '咨询')
        cost = good_obj.get('sell_price', '咨询')

        d = {
            'brand': brand,
            'cat_no': cat_no,
            'chs_name': chs_name,
            'cas': cas,
            'parent': parent,
            'stock_info': stock_info,
            'expiry_date': expiry_date,
            'purity': purity,
            'info2': info2,
            'info3': package,
            'info4': info4,
            'prd_url': response.url,
        }

        dd = {
            'brand': brand,
            'cat_no': cat_no,
            'package': package,
            'cost': cost or info4,
            'currency': 'RMB',
            'stock_num': good_obj.get('number'),
            'delivery_time': good_obj.get('time_name'),
        }

        # 25/01/09 fix: Get stock number from api
        product_id = good_obj.get('id')
        if product_id:
            yield from self.get_stock_num(str(product_id), d, dd)

        t = first(re.findall(r"certInfo: ?('.+'),", response.text), None)
        if t is not None:
            t = literal_eval(t)
            ret = re.sub(r"\\", "", t)
            html = etree.HTML(ret)
            d['mw'] = first(html.xpath('//span[text()="Mol. Weight"]/following-sibling::span//text()'), None)
            d['mf'] = ''.join(html.xpath('//span[text()="Mol. Formula"]/following-sibling::span//text()')) or None
            d['en_name'] = first(html.xpath('//span[text()="Product Name"]/following-sibling::span//text()'), None)
            d['appearance'] = first(html.xpath('//span[text()="Appearance"]/following-sibling::span//text()'), None)
            d['img_url'] = first(html.xpath("//div[@class='boxcenterch']//img/@src"), None)
        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        # dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)

        yield SupplierProduct(**ddd)
        # yield RawSupplierQuotation(**dddd)
        if not is_tanmo(brand) and brand not in TANMO_OTHER_BRANDS:
            self.other_brands.add(brand)
            return
        yield RawData(**d)
        # yield ProductPackage(**dd)

    def closed(self, reason):
        self.logger.info(f'其他品牌: {self.other_brands}')

    def get_stock_num(self, id_str: str, d: dict, dd: dict):
        base_url = 'https://item.gbw-china.com/official_web/product_front/front/product/async_get_product_detail_by_id'
        _time = int(time.time() * 1000)
        _sign_str = f"{id_str}GOODS_INFO_CHECK_KEY{_time}"
        sign = hashlib.md5(_sign_str.encode('utf-8')).hexdigest()
        params = {
            'idStr': id_str,
            'time': _time,
            'sign': sign,
        }
        url = f"{base_url}?{urlencode(params)}"
        yield Request(url, meta={'dd': dd, 'd': d},
                      callback=self.handle_get_stock_num_result)

    def handle_get_stock_num_result(self, response):
        meta = response.meta
        dd = meta['dd']
        d = meta['d']
        stock_num = None
        if json_obj := response.json():
            if good_obj := json_obj.get('body'):
                stock_num = good_obj.get('number')

        if stock_num is not None:
            dd['stock_num'] = str(stock_num)
        else:
            self.logger.warn(f'Error fetch stock number response_url:{response.url}')
        yield ProductPackage(**dd)
        dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
        yield RawSupplierQuotation(**dddd)
