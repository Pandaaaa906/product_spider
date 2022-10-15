import json
import time
from urllib.parse import parse_qsl, urlparse

import scrapy
from more_itertools import first

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class DRESpider(BaseSpider):
    name = "dre"
    allowd_domains = ["lgcstandards.com"]
    start_urls = ["https://www.lgcstandards.com/US/en/search/?text=dre"]
    base_url = "https://www.lgcstandards.com/US/en"

    def start_requests(self):
        yield scrapy.Request(
            url='https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=dre%3A:itemtype:LGCProduct:itemtype:ATCCProduct&country=US&lang=en&defaultB2BUnit=',
            callback=self.parse,
        )

    def parse(self, response, **kwargs):
        products = json.loads(response.text).get("products", [])
        if products is []:
            return
        for prd in products:
            cat_no = prd.get("code")
            en_name = prd.get("name")
            img_url = prd.get("analyteImageUrl")
            prd_url = '{}{}'.format(self.base_url, prd.get("url"))
            if (mw := prd.get("listMolecularWeight")) is None:
                mw = []
            mw = ''.join(mw)
            if (mf := prd.get("listMolecularFormula")) is None:
                mf = ''.join([])
            else:
                mf = first(mf).replace(' ', '')

            package = ''.join(prd.get("uom", '').split())
            d = {
                "brand": self.name,
                "cat_no": cat_no,
                "en_name": en_name,
                "mf": mf,
                "mw": mw,
                "prd_url": prd_url,
                "img_url": img_url,
            }
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "currency": "USD",
            }
            yield scrapy.Request(
                url=prd_url,
                callback=self.parse_detail,
                meta={
                    "product": d,
                    "package": dd,
                }
            )
        time.sleep(5)
        current_page_num = int(dict(parse_qsl(urlparse(response.url).query)).get('currentPage', None))
        if current_page_num is not None:
            current_page_num = current_page_num + 1
            yield scrapy.Request(
                url=f'https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage={current_page_num}&q=dre%3A:itemtype:LGCProduct:itemtype:ATCCProduct&country=US&lang=en&defaultB2BUnit=',
                callback=self.parse
            )

    def parse_detail(self, response):
        time.sleep(3)
        d = response.meta.get("product", None)
        dd = response.meta.get("package", None)
        info2 = response.xpath("//*[contains(text(), 'Storage Temperature')]/following-sibling::p/text()").get()  # 储存条件
        shipping_info = response.xpath(
            "//*[contains(text(), 'Shipping Temperature')]/following-sibling::p/text()").get()
        smiles = response.xpath("//*[contains(text(), 'SMILES')]/following-sibling::p/text()").get()
        cas = response.xpath("//*[contains(text(), 'CAS Number')]/following-sibling::p/text()").get()
        stock_num = response.xpath("//*[@class='orderbar__stock-title in-stock-green']/text()").get()
        en_name = response.xpath("//*[contains(text(), 'Analyte Name')]/following-sibling::p/text()").get()
        inchi = response.xpath("//*[contains(text(), 'InChI')]/following-sibling::p/text()").get()
        iupac = response.xpath("//*[contains(text(), 'IUPAC')]/following-sibling::p/text()").get()

        api_name = ''.join(response.xpath("//*[contains(text(), 'API Family')]/following-sibling::a/text()").getall())

        parent = ''.join(
            response.xpath("//*[contains(text(), 'Product Categories')]/following-sibling::p//a/text()").getall())

        prd_attrs = json.dumps({
            "api_name": api_name,
            "inchi": inchi,
            "iupac": iupac,
        })
        d["parent"] = parent
        d["info2"] = info2
        d["cas"] = cas
        d["en_name"] = en_name
        d["shipping_info"] = shipping_info
        d["smiles"] = smiles
        d["attrs"] = prd_attrs
        dd["stock_num"] = stock_num
        yield RawData(**d)
        yield ProductPackage(**dd)
