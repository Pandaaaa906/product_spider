import json
import re

import execjs
from parsel import Selector
from scrapy import Request, FormRequest
from scrapy.http import Response

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip, dumps
from product_spider.utils.items_translate import product_package_to_raw_supplier_quotation, rawdata_to_supplier_product
from product_spider.utils.spider_mixin import BaseSpider


def get_acw_sc_v2(response):
    arg1 = re.findall("arg1='(.*?)'", response.text)[0]
    with open('product_spider/utils/get_acw_sc_v2.js', 'r', encoding='utf-8') as f:
        acw_sc_v2_js = f.read()
    return execjs.compile(acw_sc_v2_js).call('getAcwScV2', arg1)


class AladdinSpider(BaseSpider):
    """阿拉丁"""
    name = "aladdin"
    home_url = "https://www.aladdin-e.com/zh_cn/"
    start_urls = [home_url, ]
    base_url = 'https://www.aladdin-e.com'

    cookies = {}

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
        yield Request(url=self.home_url, callback=self.set_cookies)

    def set_cookies(self, response):
        acw_sc__v2 = get_acw_sc_v2(response)
        self.cookies["acw_sc__v2"] = acw_sc__v2
        yield Request(url=self.home_url, cookies=self.cookies, callback=self.parse, dont_filter=True)

    def parse(self, response, **kwargs):
        nodes = response.xpath(
            '//div[@id="store.menu"]//a[not(following-sibling::ul)'
            ' and not(contains(@href,"faq")) and not(contains(@href,"points-exchange"))]'
        )
        for node in nodes:
            url = node.xpath("./@href").get()
            parent = node.xpath("./span/text()").get()
            yield Request(
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
            yield Request(
                url=url,
                callback=self.parse_detail,
                meta={
                    "parent": parent,
                    "img_url": img_url,
                }
            )
        next_url = response.xpath("//span[contains(text(), '下一步')]/parent::a/@href").get()
        if next_url:
            yield Request(
                url=next_url,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        tmpl = '//li[strong[contains(text(), {!r})]]//text()[not(parent::strong)]'
        tmpl_table = '//td[@data-th={!r}]/text()'
        attrs = {
            "pubchem_id": response.xpath('//li[strong[contains(text(),"PubChem编号:")]]/a//text()').get(),
        }
        purity = response.xpath("//div[strong[contains(text(),'规格或纯度:')]]/span//text()").get()
        purity_table = strip(response.xpath(tmpl_table.format('规格或纯度')).get())
        d = {
            "brand": self.name,
            "cat_no": (m := re.search(r'"product_sku": \'(.+)\'', response.text)) and m.group(1),
            "chs_name": response.xpath("//span[@data-ui-id='page-title-wrapper']/text()").get(),
            "en_name": strip(response.xpath(tmpl_table.format('英文名称')).get()),
            "parent": response.meta.get("parent"),
            "purity": purity or purity_table,
            "cas": response.xpath("//li[strong[contains(text(), 'CAS编号')]]/span/a/text()").get(),
            "mf": strip(''.join(response.xpath(tmpl.format("分子式:")).getall())),
            "mw": strip(''.join(response.xpath(tmpl.format('分子量:')).getall())),
            "mdl": response.xpath("//li[strong[contains(text(),'MDL号')]]/span//text()").get(),
            "info1": strip(response.xpath(tmpl_table.format('英文别名')).get()),
            "shipping_info": strip(response.xpath(tmpl_table.format('运输条件')).get()),

            "prd_url": response.url,
            "img_url": response.meta.get("img_url"),
            "attrs": dumps({k: v for k, v in attrs.items() if v}),
        }
        yield RawData(**d)
        yield SupplierProduct(**rawdata_to_supplier_product(d, self.name, self.name))

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
        if not packages:
            self.logger.warning(f"prd page have not packages: {response.url}")
            return
        form_data = {f'ajaxUpdatePrice_{_id}': f'ajaxUpdatePrice_{_id}' for _id in packages}
        yield FormRequest(
            url='https://www.aladdin-e.com/zh_cn/catalogb/ajax/price/',
            callback=self.parse_price,
            formdata=form_data,
            meta={
                "product": d,
                "packages": packages,
            },
        )

    def parse_price(self, response):
        d = response.meta.get("product")
        packages = response.meta.get("packages")
        res_obj = json.loads(response.text)

        for _id, cat_no_unit in packages.items():
            package = cat_no_unit.get("package", None)
            if not package:
                continue
            _, package = package.rsplit("-", 1)
            delivery_time = cat_no_unit.get("delivery_time")
            price = Selector(res_obj.get(_id)).xpath("//span[@class='price']//text()").get()

            dd = {
                "brand": self.name,
                "cat_no": d['cat_no'],
                "package": package,
                "cost": parse_cost(price),
                "delivery_time": delivery_time,
                "currency": "RMB"
            }
            yield ProductPackage(**dd)
            if not dd['cost']:
                continue
            yield RawSupplierQuotation(**product_package_to_raw_supplier_quotation(d, dd, self.name, self.name))
