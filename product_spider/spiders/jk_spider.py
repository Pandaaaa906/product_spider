import json
import re
from string import ascii_uppercase
from time import time
from urllib.parse import urljoin

import scrapy
from more_itertools import first
from scrapy import Request

from product_spider.items import JkProduct, JKPackage
from product_spider.utils.functions import strip


class JkPrdSpider(scrapy.Spider):
    name = "jk"
    allowed_domains = ["jkchemical.com"]
    base_url = "http://www.jkchemical.com"
    start_urls = map(lambda x: "http://www.jkchemical.com/CH/products/index/ProductName/{0}.html".format(x),
                     ascii_uppercase)
    prd_size_url = "http://www.jkchemical.com/Controls/Handler/GetPackAgeJsonp.ashx?callback=py27&value={value}&cid={cid}&type=product&_={ts}"

    def parse(self, response):
        for xp_url in response.xpath("//div[@class='yy toa']//a/@href"):
            tmp_url = self.base_url + xp_url.extract()
            yield Request(tmp_url.replace("EN", "CH"), callback=self.parse_list)

    def parse_list(self, response):
        xp_boxes = response.xpath("//table[@id]//div[@class='PRODUCT_box']")
        for xp_box in xp_boxes:
            div = xp_box.xpath(".//div[2][@class='left_right mulu_text']")
            brand = strip(div.xpath('.//li[@id="ctl00_cph_Content_li_lt_Brand"]/text()').get(), '')
            rel_url = div.xpath('.//a[@class="name"]/@href').get()
            img_url = div.xpath('.//img/@src').get()
            d = {
                'brand': brand.replace('-', '') or None,
                "purity": div.xpath(".//li[1]/text()").get('').split(u"：")[-1].strip(),
                "cas": strip(div.xpath(".//li[2]//a/text()").get()),
                "cat_no": div.xpath(".//li[4]/text()").get().split(u"：")[-1].strip(),
                "en_name": strip(xp_box.xpath(".//a[@class='name']/text()").get()),
                "cn_name": strip(xp_box.xpath(".//a[@class='name']//span[1]/text()").get()),
                'prd_url': rel_url and urljoin(response.url, rel_url),
                'img_url': img_url and urljoin(response.url, img_url),
            }
            data_jkid = xp_box.xpath(".//div[@data-jkid]/@data-jkid").get()
            data_cid = xp_box.xpath(".//div[@data-cid]/@data-cid").get()

            yield Request(self.prd_size_url.format(value=data_jkid, cid=data_cid, ts=int(time())),
                          body=u"",
                          meta={"prd_data": d},
                          callback=self.parse_package)

        next_page = response.xpath('//a[contains(text(), "下一页")]/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse_list)

    def parse_package(self, response):
        s = re.findall(r"(?<=\().+(?=\))", response.text)[0]
        packages = json.loads(s)
        d = response.meta.get('prd_data', {})
        package = first(packages, {})
        if package:
            d['brand'] = d['brand'] or package.get('Product', {}).get('BrandName')
        yield JkProduct(**d)
        for package_obj in packages:
            catalog_price = package_obj.get("CatalogPrice", {})
            dd = {
                'brand': d.get('brand'),
                'cat_no': d.get('cat_no'),
                'package': package_obj.get("stringFormat"),
                'price': catalog_price and catalog_price.get('Value'),
                'currency': catalog_price and strip(catalog_price.get('Currency')),
                'attrs': json.dumps(package_obj),
            }
            yield JKPackage(**dd)
