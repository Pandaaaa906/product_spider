import json
import time
from urllib.parse import parse_qsl, urlparse
import scrapy
from product_spider.items import RawData, ProductPackage
from product_spider.utils.parsepackage import parse_package
from product_spider.utils.spider_mixin import JsonSpider


def parse_brand(raw_brand):
    if not raw_brand:
        return None
    mapping = {
        "easi-tab™": "easi-tab",
        "dr. ehrenstorfer": "dre",
    }
    brand = mapping.get(raw_brand, raw_brand)
    return brand


class LGCSpider(JsonSpider):
    name = "lgc"
    allowd_domains = ["lgcstandards.com"]
    start_urls = ["https://www.lgcstandards.com/US/en/search/?text=LGC"]
    base_url = "https://www.lgcstandards.com/US/en"

    def start_requests(self):
        yield scrapy.Request(
            url="https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=LGC%3A:itemtype:LGCProduct:itemtype:ATCCProduct&country=US&lang=en&defaultB2BUnit=",
            callback=self.parse,
        )

    def parse(self, response, **kwargs):
        products = json.loads(response.text).get("products", [])
        if products is []:
            return
        for prd in products:
            brand = parse_brand(prd.get("brand", {}).get("name", None).lower())
            cat_no = prd.get("code", None)
            en_name = prd.get("name", None)
            img_url = prd.get("analyteImageUrl", None)
            prd_url = '{}{}'.format(self.base_url, prd.get("url"))

            d = {
                "brand": brand,
                "cat_no": cat_no,
                "en_name": en_name,
                "prd_url": prd_url,
                "img_url": img_url,
            }
            dd = {
                "brand": brand,
                "cat_no": cat_no,
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
                url=f"https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage={current_page_num}&q=LGC%3A:itemtype:LGCProduct:itemtype:ATCCProduct&country=US&lang=en&defaultB2BUnit=",
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

        mw = response.xpath("//*[contains(text(), 'Molecular Weight')]/following-sibling::p/text()").get()

        mf = response.xpath("//*[contains(text(), 'Product Format')]/following-sibling::p/text()").get()
        package = parse_package(response.xpath("//*[contains(text(), 'Pack Size:')]/following-sibling::p/text()").get())

        prd_attrs = json.dumps({
            "api_name": api_name,
            "inchi": inchi,
            "iupac": iupac,
        })
        d["parent"] = parent
        d["info2"] = info2
        d["cas"] = cas
        d["mw"] = mw
        d['mf'] = mf
        d["en_name"] = en_name
        d["shipping_info"] = shipping_info
        d["smiles"] = smiles
        d["attrs"] = prd_attrs
        dd["package"] = package
        dd["stock_num"] = stock_num
        yield RawData(**d)
        yield ProductPackage(**dd)
