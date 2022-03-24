import json

import parsel
import scrapy

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class AladdinSpider(BaseSpider):
    """阿拉丁"""
    name = "aladdin"
    start_urls = ["https://www.aladdin-e.com/zh_cn/"]

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
        "accept": "application/json, text/javascript, */*; q=0.01",
        "x-requested-with": "XMLHttpRequest",
    }

    def parse(self, response, **kwargs):
        nodes = response.xpath('//div[@id="store.menu"]//a[not(following-sibling::ul)]')
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
        cn_name = response.xpath("//h1[@class='page-title']/span/text()").get()
        en_name = response.xpath("//div[@class='product-name2-regent']/text()").get()
        purity = response.xpath("//div[@class='product-package']/text()").get()
        cas = response.xpath("//span[contains(text(), ' CAS编号 ')]/a/text()").get()
        mf = ''.join(response.xpath("//th[contains(text(), '分子式')]//following-sibling::td//text()").getall())
        mw = response.xpath("//th[@class='col label molecular_weight']/following-sibling::td/text()").get()
        mdl = response.xpath("//li[contains(text(), ' MDL号 ')]//a/text()").get()
        shipping_info = response.xpath("//th[contains(text(), '运输条件')]/following-sibling::td/text()").get()
        cat_no = response.xpath('//div[@class="product-add-form"]/form/@data-product-sku').get()
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
        packages = {
            tr.xpath("./td[@class='ajaxPrice']/@attr").get(): {
                "package": tr.xpath("./td[position()=1]/a/text()").get(),
                "delivery_time": tr.xpath("./td[position()=2]/text()").get('').strip(),
            }
            for tr in tr_list
        }
        form_data = {f'ajaxUpdatePrice_{_id}': f'ajaxUpdatePrice_{_id}' for _id in packages}
        yield scrapy.FormRequest(
            url='https://www.aladdin-e.com/zh_cn/catalogb/ajax/price/',
            method='POST',
            callback=self.parse_price,
            formdata=form_data,
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
            _, package = cat_no_unit.get("package").rsplit("-", 1)
            delivery_time = cat_no_unit.get("delivery_time")
            price = parsel.Selector(res_obj.get(_id)).xpath("//span[@class='price']//text()").get()
            if price:
                price = price.replace("¥", '')

            dd = {
                "brand": self.name,
                "cat_no": d['cat_no'],
                "package": package,
                "cost": price,
                "delivery_time": delivery_time,
                "currency": "RMB"
            }
            yield ProductPackage(**dd)

