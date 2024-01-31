import re
from io import BytesIO
from time import time
from typing import Dict
from urllib.parse import urlencode, urljoin

import requests
import scrapy
from fontTools.ttLib import TTFont
from scrapy import Request, FormRequest

from product_spider.items import SupplierProduct, RawSupplierQuotation
from product_spider.utils.spider_mixin import BaseSpider


brands_mapping = {
    "dre.e": "dre"
}
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                         'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8'}


class TansooleSpider(BaseSpider):
    name = "tansoole"
    start_urls = ["https://www.tansoole.com/search/search.htm?gloabSearchVo.queryString=dr.e"]
    base_url = "https://www.tansoole.com/"
    url_search_api = "https://www.tansoole.com/search/search-result.htm"
    url_search_html = "https://www.tansoole.com/search/search.htm"

    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                          'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
            'Accept-Encoding': 'gzip, deflate, br', 'Accept': '*/*', 'Connection': 'keep-alive',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        },
        # "DOWNLOADER_MIDDLEWARES": {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
    }

    _font_mapping: Dict[str, str.maketrans] = {}
    _font_code_mapping = {
        '-1': '.', '-1#1': '/',
        '-1#2': '0', '-1#3': '1', '-1#4': '2', '-1#5': '3', '-1#6': '4',
        '-1#7': '5', '-1#8': '6', '-1#9': '7', '-1#10': '8', '-1#11': '9',
        '.null': '0', 'obreve': '0'
    }
    _font_unicode_mapping = {

    }

    def _get_font_map(self, font_name: str, t='202310171242361743134'):
        r = requests.get(f'https://www.tansoole.com/font/{font_name}/font/tansoole.ttf?{t}', headers=headers)
        font = TTFont(BytesIO(r.content))
        cmap = font.getBestCmap()
        self._font_mapping[font_name] = str.maketrans({chr(k): chr(font.getGlyphID(v) + 43) for k, v in cmap.items()})

    def get_font_map(self, font_name: str):
        if font_name not in self._font_mapping:
            self._get_font_map(font_name)
        return self._font_mapping[font_name]

    def decode_price(self, value: str, font_name):
        if isinstance(value, str):
            return value.translate(self.get_font_map(font_name))
        return value

    def is_proxy_invalid(self, request, response):
        if "系统繁忙" in response.text:
            self.log(f"系统繁忙: {response.url}")
            return True
        return False

    @staticmethod
    def _parse_brand(brand: str, default=None):
        # TODO Move to pipeline
        if not brand:
            return default
        if (brand := brand.lower()) in brands_mapping:
            return brands_mapping[brand]
        return brand

    @staticmethod
    def _get_search_params(response):
        cur_page_no = (
                response.xpath('//input[@id="gloabSearchVo_page_currentPageNo"]/@value').get()
                or response.xpath('//input[@id="currentPageNo"]/@value').get()
                or '1'
        )
        page_size = (
                response.xpath('//input[@id="gloabSearchVo_page_pageSize"]/@value').get()
                or response.xpath('//input[@id="pageSize"]/@value').get()
                or '50'
        )
        d = {
            "gloabSearchVo.queryString": response.xpath('//input[@name="gloabSearchVo.queryString"]/@value').get(''),
            "gloabSearchVo.sortField": response.xpath('//input[@name="gloabSearchVo.sortField"]/@value').get(
                'cn_len'),
            "gloabSearchVo.asc": response.xpath('//input[@name="gloabSearchVo.asc"]/@value').get('true'),
            "token": response.xpath('//input[@id="gloabSearchVo_token"]/@value').get(''),
            "page.currentPageNo": cur_page_no,
            "page.pageSize": page_size,
            "gloabSearchVo.rkey": response.xpath('//input[@name="gloabSearchVo.rkey"]/@value').get(),
            "gloabSearchVo.fontClassName": response.xpath('//input[@name="gloabSearchVo.fontClassName"]/@value').get(),
            "t": str(int(time() * 1000), ),
            "pci": "4896,4897",
        }
        if pro_title := response.xpath('//input[@name="proTitle"]/@value').get():
            d["proTitle"] = pro_title
        if pro := response.xpath('//input[@name="pro"]/@value').get():
            d["pro"] = pro
        return d

    def parse(self, response, **kwargs):
        d = self._get_search_params(response)
        yield FormRequest(
            f"{self.url_search_api}?t{int(time() * 1000)}",
            formdata=d,
            callback=self.parse_list,
        )

    def parse_list(self, response, **kwargs):
        """dre价格在泰坦官网获取"""
        if "非法请求" in response.text:
            self.log(f"非法请求: {response.url}")
        rows = response.xpath("//ul[@class='show-list show-list-head']/following-sibling::ul/li[position()=1]")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_package
            )
        # 获取下一页
        d = self._get_search_params(response)
        cur_page = int(d["page.currentPageNo"])
        total_page = int(response.xpath('//input[@id="pageTotalPageCount"]/@value').get('1'))
        if cur_page >= total_page:
            return
        d["page.currentPageNo"] = str(cur_page + 1)
        yield Request(
            f"{self.url_search_html}?{urlencode(d)}",
            callback=self.parse,
        )

    def parse_package(self, response):
        prd_num = response.xpath("//input[@id='productNumEntryId']/@value").get()
        token = response.xpath("//input[@id='productNumTokenEntry']/@value").get()
        r_key = response.xpath("//input[@id='rkeyIdHidden']/@value").get()
        raw_font_name = response.xpath('//input[@id="fontclassNameHidden"]/@value').get('')
        font_name = (m := re.search(r'font(\w+)', raw_font_name)) and m.group(1)

        yield scrapy.FormRequest(
            url="https://www.tansoole.com/detail/loadone.htm",
            formdata={
                "productNum": prd_num,
                "tokenEntry": token,
                "province": "4896",
                "city": "4897",
                "area": '',
                "rkey": r_key,
                "t": f"{(time()*1000):.0f}",
            },
            callback=self.parse_cost,
            meta={"prd_url": response.url, "font_name": font_name}
        )

    def parse_cost(self, response):
        prd_url = response.meta.get("prd_url", None)
        font_name = response.meta.get("font_name", None)
        res = response.json().get("data", None)
        if not res:
            return
        source_id = res.get("id", None)
        cat_no = res.get("oldNum", None)
        chs_name = res.get("productName", None)
        package = res.get("packType", None)
        expiry_date = res.get("expireDate", None)
        delivery = res.get("deliveryDay", None)
        raw_cas = (chs_name and (m := re.search(r'(?<=\|)\d+-\d{2}-\d(?=\|)', chs_name)) and m.group())
        cas = res.get("cas", None) or raw_cas

        price = res.get("productEntryPrice", None)
        price = self.decode_price(price, font_name)
        cost = res.get("entryPrice", None)
        cost = self.decode_price(cost, font_name)

        stock_num = res.get("transportDesc", None)
        if stock_num == '现货':
            delivery = '现货'
        brand = self._parse_brand(res.get('brand'))
        ddd = {
            "platform": "tansoole",
            "source_id": source_id,
            "vendor": "tansoole",
            "brand": brand,
            "cat_no": cat_no,
            "chs_name": chs_name,
            "cas": cas,
            "package": package,
            "prd_url": prd_url,
            "price": price,
            "cost": cost,
            "stock_num": stock_num,
            "delivery": delivery,
            "expiry_date": expiry_date,
            "currency": "RMB",
        }

        dddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": brand,
            "source_id": f'{brand}_{cat_no}',
            'cat_no': cat_no,
            "cas": cas,
            'package': package,
            'discount_price': cost,
            'price': price,
            'delivery': delivery,
            'currency': ddd["currency"],
        }
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)
