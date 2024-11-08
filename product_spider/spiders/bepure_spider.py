import re
import time
import urllib
from os import getenv
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils import bepure_util
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider

BEPURE_USER = getenv('BEPURE_USER')
BEPURE_PWD = getenv('BEPURE_PWD')


class BepureSpider(BaseSpider):
    name = "bepure"
    base_url = "http://www.bepurestandards.com/"
    api_url = 'http://www.bepurestandards.com/a.aspx?'
    start_urls = [
        "https://list.bepurecrm.com/list_goods/0/1.html",
    ]
    brand = 'bepure'
    currency = 'RMB'

    def start_requests(self):
        yield Request(
            url=self.start_urls[0],
            callback=self.parse,
        )

    def parse(self, response, **kwargs):
        rows = response.xpath("//table[@class='table product_table']/tbody//tr")
        for row in rows:
            url = row.xpath("//a[@class='title-cn goods-detail-a']/@href").get()
            delivery_time = row.xpath("//div[@class='td_time_name']/text()").get().strip()  # 货期
            if url and delivery_time:
                yield Request(urljoin(response.url, url), callback=self.parse_detail,
                              meta={'delivery_time': delivery_time})
            else:
                self.logger.warn(f"url或货期为空 url:{url} delivery_time:{delivery_time}")

        # 切换页码
        current_page = re.search(r'(?<=pno:)\s*\d+(?=,)', response.text)
        total_pages = re.search(r'(?<=total:)\s*\d+(?=,)', response.text)
        next_url = None
        if current_page and total_pages:
            current_page = int(current_page.group().strip())
            # total_pages = int(total_pages.group().strip())
            total_pages = 5
            if current_page < total_pages:
                next_url = f'https://list.bepurecrm.com/list_goods/0/{current_page + 1}.html'
        self.logger.info(f"next_url:{next_url}")
        if next_url:
            yield Request(url=next_url, callback=self.parse)

    def parse_detail(self, response):
        product_id = response.url.split('/')[-1].strip('.html')
        img_rel = re.search(r'(?<=showImg:\s").+(?=")', response.text)
        if img_rel:
            img_rel = img_rel.group()
        info_xpath = "//el-form-item[@label={!r}]/span/text()"
        brand = response.xpath(info_xpath.format('品牌')).get()
        if not brand:
            return
        brand = str(brand).strip().lower()
        if brand != self.brand:
            return

        search_purity = None
        expiry_date = None
        good_obj_str = re.search(r'goodObj:\s?\{([^}]*)}', response.text)
        if good_obj_str:
            good_obj_str = good_obj_str.group().replace(' ', '').replace('\n', '')
            search_exp_date = re.search(r'(?<=date:).+?(?=,)', good_obj_str)
            expiry_date = search_exp_date.group().strip('"').strip() if search_exp_date else None,
            if not expiry_date and len(expiry_date) == 0:
                expiry_date = None
            search_purity = re.search(r'(?<=norm:).+?(?=,)', good_obj_str)
        d = {
            'brand': self.brand,
            'parent': response.xpath("//a[@class='el-breadcrumb__item'][last()]/span/text()").get(),
            'cat_no': response.xpath(info_xpath.format('产品编号')).get(),
            'chs_name': response.xpath("//div/h2[@class='p-right-title']/span/text()").get(),
            'en_name': response.xpath(info_xpath.format('英文名称')).get(),
            'cas': response.xpath(info_xpath.format('CAS号')).get(),
            'mf': formula_trans(response.xpath(info_xpath.format('分子式')).get()),
            'mw': response.xpath(info_xpath.format('分子量')).get(),
            'img_url': img_rel,
            'prd_url': response.url,
            'info1': response.xpath(info_xpath.format('运输条件')).get(),
            'stock_info': response.xpath(info_xpath.format('储存条件')).get(),
            'expiry_date': expiry_date,
            'stock_num': None,
            'purity': search_purity.group() if search_purity else None,
        }
        package = response.xpath(info_xpath.format('规格')).get()
        package = package.strip().lower() if package else None

        _url = "https://item.bepurecrm.com/bms_ec_web/site/front/product/async_get_product_detail_by_id"
        now_timestamp = str(int(time.time() * 1000))
        params = {
            'idStr': product_id,
            'time': now_timestamp,
            'sign': bepure_util.md5(product_id + "GOODS_INFO_CHECK_KEY" + now_timestamp)
        }
        _url = f'{_url}?{urllib.parse.urlencode(params)}'
        yield Request(
            url=_url,
            method='GET',
            meta={
                'product_id': product_id,
                'product': d,
                'package': package,
            },
            callback=self.handle_req_price_and_stock_number,
            headers={'referer': d.get('prd_url')}
        )

    def handle_req_price_and_stock_number(self, response):
        j_obj = response.json().get('body')
        d = response.meta.get('product')
        if not j_obj:
            self.logger.warn(f'Get price and stock number failed, product_id:{response.meta.get("product_id")}')
        else:
            d['stock_num'] = j_obj.get('number')
            response.meta['stock_num'] = j_obj.get('number')
            response.meta['price'] = j_obj.get('price')
            response.meta['sell_price'] = j_obj.get('sellPrice')
        next(self.save_data(response, d))

    def save_data(self, response, d):
        self.logger.info(f'save data, product_id:{response.meta.get("product_id")}')
        package = response.meta['package']
        yield RawData(**d)
        dd = {
            "brand": self.brand,
            "cat_no": d['cat_no'],
            "package": package,
            "price": response.meta.get('sell_price'),
            "cost": response.meta.get('sell_price'),
            "currency": self.currency,
            'stock_num': d.get('stock_num'),
            'purity': d.get('purity'),
            'delivery_time': response.meta.get('delivery_time'),
        }
        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id": f"{self.name}_{d.get('cat_no')}_{package}",
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
            "source_id": f'{self.name}_{d["cat_no"]}',
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'discount_price': dd['cost'],
            'price': dd['cost'],
            'cas': d["cas"],
            'currency': dd["currency"],
        }
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)
