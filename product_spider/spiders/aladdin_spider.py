import json
import re

import execjs
import parsel
import requests
import scrapy
from scrapy import Request
from scrapy.http import Response

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


def get_last_part_of_url(url):
    if url.endswith('/'):
        url = url[:-1]
    last_slash_index = url.rfind('/')
    # 截取最后一个 '/' 之后的所有内容
    last_part = url[last_slash_index + 1:]
    return last_part


def get_complete_cookie(url, headers):
    complete_cookie = {}
    # 第一次不带参数访问首页，获取 acw_tc 和 acw_sc__v2
    response = requests.get(url=url, headers=headers)
    complete_cookie.update(response.cookies.get_dict())
    acw_sc__v2 = get_acw_sc_v2(response)
    complete_cookie.update({"acw_sc__v2": acw_sc__v2})
    response2 = requests.get(url=url, headers=headers, cookies=complete_cookie)
    complete_cookie.update(response2.cookies.get_dict())
    return complete_cookie


def get_acw_sc_v2(response):
    arg1 = re.findall("arg1='(.*?)'", response.text)[0]
    with open('product_spider/utils/get_acw_sc_v2.js', 'r', encoding='utf-8') as f:
        acw_sc_v2_js = f.read()
    return execjs.compile(acw_sc_v2_js).call('getAcwScV2', arg1)


class AladdinSpider(BaseSpider):
    """阿拉丁"""
    name = "aladdin"
    start_urls = ["https://www.aladdin-e.com/zh_cn/"]
    base_url = 'https://www.aladdin-e.com'

    headers = {
        "Host": "www.aladdin-e.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
        "Referer": "https://www.aladdin-e.com/"
    }

    cookies = []

    # custom_settings = {
    #     "DOWNLOADER_MIDDLEWARES": {
    #         'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
    #     },
    #     'PROXY_POOL_REFRESH_STATUS_CODES': [403, 504, 503, ],
    #     'RETRY_TIMES': 10,
    # }

    def is_proxy_invalid(self, request, response: Response):
        if response.status in {403, 504}:
            return True
        if 'document.location.reload' in response.text:
            return True
        return False

    def start_requests(self):
        self.cookies = get_complete_cookie(self.base_url, self.headers)
        yield Request(url=self.start_urls[0], cookies=self.cookies, callback=self.parse)

    def parse(self, response, **kwargs):
        nodes = response.xpath(
            '//div[@id="store.menu"]//a[not(following-sibling::ul)'
            ' and not(contains(@href,"faq")) and not(contains(@href,"points-exchange"))]'
        )
        for node in nodes:
            url = node.xpath("./@href").get()
            parent = node.xpath("./span/text()").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                dont_filter=True,
                meta={
                    "parent": parent
                }
            )

    def parse_list(self, response):
        parent = response.meta.get("parent")
        img_url = response.xpath("//img[@class='product-image-photo']/@src").get()
        rows = response.xpath("//div[@class='products wrapper grid products-grid product-cate-grid']//li")
        for row in rows:
            url = row.xpath(".//div[@class='product-item-info']/a/@href").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={
                    "parent": parent,
                    "img_url": img_url,
                }
            )
        next_url = response.xpath("//span[contains(text(), '下一步')]/parent::a/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        parent = response.meta.get("parent")
        img_url = response.meta.get("img_url")
        cn_name = response.xpath("//span[@data-ui-id='page-title-wrapper']/text()").get()
        en_name = strip(response.xpath("//td[@data-th='英文名称']/text()").get())
        purity = response.xpath("//div/strong[contains(text(),'规格或纯度:')]/parent::*/span//text()").get()
        cas = response.xpath("//li[.//text()[contains(., 'CAS编号')]]/span/a/text()").get()
        mf = strip(''.join(response.xpath("//li[.//text()[contains(., '分子式')]]//text()").getall())).strip('分子式:： \n')
        mw = strip(''.join(response.xpath("//li/strong[contains(text(),'分子量')]/parent::*/text()").getall()))
        mdl = response.xpath("//li/strong[contains(text(),'MDL号')]/parent::*/span//text()").get()
        shipping_info = strip(response.xpath("//th[contains(text(), '运输条件')]/following-sibling::td/text()").get())
        cat_no = get_last_part_of_url(response.url).strip('.html').upper()
        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "chs_name": cn_name,
            "en_name": en_name,
            "parent": parent,
            "purity": purity,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "mdl": mdl,
            "prd_url": response.url,
            "img_url": img_url,
            "shipping_info": shipping_info,
        }

        tr_list = response.xpath("//table[@class='table data grouped cart']/tbody/tr")
        package_ids = [x.strip('prompt_box_') for x in
                       response.xpath("//div[contains(@id,'prompt_box_')]/@id").getall()]
        packages = {
            tr.xpath("./td[@class='ajaxPrice']/@attr").get(): {
                "id": package_ids[index],
                "package": tr.xpath("./td[position()=2]/text()").get().strip(),
                "delivery_time": tr.xpath("./td[position()=3]/text()").get('').strip(),
            }
            for index, tr in enumerate(tr_list)
        }
        form_data = {f'ajaxUpdatePrice_{_id}': f'ajaxUpdatePrice_{_id}' for _id in packages}
        yield scrapy.FormRequest(
            url='https://www.aladdin-e.com/zh_cn/catalogb/ajax/price/',
            method='POST',
            callback=self.parse_price,
            formdata=form_data,
            cookies=self.cookies,
            meta={
                "product": d,
                "packages": packages,
            },
            headers=self.headers
        )

    def parse_price(self, response):
        d = response.meta.get("product")
        packages = response.meta.get("packages")
        res_obj = json.loads(response.text)
        yield RawData(**d)
        for _id, cat_no_unit in packages.items():
            package = cat_no_unit.get("package", None)
            if not package:
                continue
            _, package = package.rsplit("-", 1)
            delivery_time = cat_no_unit.get("delivery_time")
            price = parsel.Selector(res_obj.get(_id)).xpath("//span[@class='price']//text()").get()

            dd = {
                "brand": self.name,
                "cat_no": d['cat_no'],
                "package": package,
                "cost": parse_cost(price),
                "delivery_time": delivery_time,
                "currency": "RMB"
            }
            yield ProductPackage(**dd)

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id": f'{self.name}_{d["cat_no"]}_{dd["package"]}',
                "en_name": d["en_name"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                "purity": d["purity"],
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
                'delivery': delivery_time,
                'currency': dd["currency"],
            }
            yield SupplierProduct(**ddd)
            yield RawSupplierQuotation(**dddd)
