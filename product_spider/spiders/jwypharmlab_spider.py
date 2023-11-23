import json
import re
from urllib.parse import urljoin

from jsonpath_ng.ext import parse
from scrapy import Request
from scrapy.http import JsonRequest

from product_spider.items import RawData, ProductPackage, RawSupplierQuotation, SupplierProduct
from product_spider.utils.items_translate import product_package_to_raw_supplier_quotation, rawdata_to_supplier_product
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.json_path import json_nth_value


class JWYSpider(BaseSpider):
    name = "jwy"
    base_url = "https://www.jwypharmlab.com.cn/"
    package_api = "https://www.jwypharmlab.com.cn/ajaxpro/Web960.Web.index,Web960.Web.ashx"
    start_urls = [
        "https://www.jwypharmlab.com.cn/"
    ]

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//a[@title="产品中心"]/following-sibling::ul//a/@href').getall()

        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_category)

    def parse_category(self, response):
        rel_urls = response.xpath('//div[@id="mainarea"]//div/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list)

    def parse_list(self, response):
        rel_urls = response.xpath('//div[@class="kj-pro-list-item-cas"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

        next_page = response.xpath(
            '//ul[contains(@class, "pagination")]/li[@class="active"]/following-sibling::li/a/@href'
        ).get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse_list)

    def parse_detail(self, response):
        tmpl = "//td[text()={!r}]/following-sibling::td/span//text()"
        rel_img = response.xpath('//div[@role="listbox"]//img/@src').get()
        d = {
            "brand": self.name,
            "parent": response.xpath('//ol[@class="breadcrumb"]//li[a][position()=last()]/a/text()').get(),
            "cat_no": response.xpath(tmpl.format("产品编号")).get(),
            "en_name": response.xpath(tmpl.format("产品名称")).get(),
            "cas": response.xpath(tmpl.format("CAS号")).get(),
            "mf": ''.join(response.xpath(tmpl.format("分子式")).getall()),
            "mw": response.xpath(tmpl.format("分子量")).get(),
            "purity": response.xpath(tmpl.format("纯度")).get(),
            "img_url": rel_img and urljoin(response.url, rel_img),
            "prd_url": response.url,
        }
        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, self.name, self.name)
        yield SupplierProduct(**ddd)

        prd_id = response.xpath('//input[@id="nowproductid"]/@value').get()
        if not prd_id:
            return

        yield JsonRequest(
            self.package_api,
            data={"pd_id": prd_id},
            headers={"X-Ajaxpro-Method": "LoadGoods"},
            callback=self.parse_package,
            meta={"prd": d}
        )

    def parse_package(self, response):
        d = response.meta.get('prd')
        j = json.loads(re.sub(r'(?<=});/\*$', '', response.text))
        j = json.loads(j.get("ObjResult"))
        rows = parse('$.*[*]').find(j)
        for row in rows:
            goods_info = json.loads(json_nth_value(row, '@.Goods_info'))
            stock_num = json_nth_value(row, '@.Inventores[*].Amount', 0)

            dd = {
                "brand": self.name,
                "cat_no": d["cat_no"],
                "package": json_nth_value(goods_info, '$.goodsinfo.packaging'),
                "currency": json_nth_value(row, '@.MoneyUnit'),
                "cost": json_nth_value(row, '@.Goods_Price'),
                "price": json_nth_value(row, '@.Goods_Price'),
                "stock_num": stock_num,
                "delivery_time": "现货" if isinstance(stock_num, (int, float)) and stock_num > 0 else "定制",
            }
            yield ProductPackage(**dd)
            dddd = product_package_to_raw_supplier_quotation(d, dd, self.name, self.name)
            yield RawSupplierQuotation(**dddd)
