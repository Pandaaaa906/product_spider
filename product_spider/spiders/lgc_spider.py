import json
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
        "mikromol": "lgc",
    }
    brand = mapping.get(raw_brand, raw_brand)
    return brand


class LGCSpider(JsonSpider):
    name = "lgc"
    allowd_domains = ["lgcstandards.com"]
    start_urls = [
        "https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=&country=US&lang=en&defaultB2BUnit=",
    ]
    base_url = "https://www.lgcstandards.com/US/en"
    custom_settings = {
        'CONCURRENT_REQUESTS': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 3,
        'CONCURRENT_REQUESTS_PER_IP': 3,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 5,
        'AUTOTHROTTLE_MAX_DELAY': 60,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1,
    }

    def parse(self, response, **kwargs):
        products = json.loads(response.text).get("products", [])
        if not products:
            return
        for prd in products:
            brand = parse_brand(prd.get("brand", {}).get("name", None).lower())
            cat_no = prd.get("code", None)
            prd_url = '{}{}'.format(self.base_url, prd.get("url"))

            d = {
                "brand": brand,
                "cat_no": cat_no,
                "en_name": prd.get("name", None),
                "prd_url": prd_url,
                "img_url": prd.get("analyteImageUrl", None),
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
        current_page_num = int(dict(parse_qsl(urlparse(response.url).query)).get('currentPage', None))
        if current_page_num is not None:
            current_page_num = current_page_num + 1
            yield scrapy.Request(
                url=f"https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage={current_page_num}&q=&country=US&lang=en&defaultB2BUnit=",
                callback=self.parse
            )

    def parse_detail(self, response):
        d = response.meta.get("product", None)
        dd = response.meta.get("package", None)

        prd_attrs = json.dumps({
            "api_name": ''.join(response.xpath("//*[contains(text(), 'API Family')]/following-sibling::a/text()").getall()),
            "inchi": response.xpath("//*[contains(text(), 'InChI')]/following-sibling::p/text()").get(),
            "iupac": response.xpath("//*[contains(text(), 'IUPAC')]/following-sibling::p/text()").get(),
            "coa_urls": tuple(response.xpath('//div[@id="PdpDocumentationCoa"]//a[@class="icon download"]/@href').getall())
        })
        d["parent"] = ''.join(
            response.xpath("//*[contains(text(), 'Product Categories')]/following-sibling::p//a/text()").getall())
        d["info2"] = response.xpath("//*[contains(text(), 'Storage Temperature')]/following-sibling::p/text()").get()  # 储存条件
        d["cas"] = response.xpath("//*[contains(text(), 'CAS Number')]/following-sibling::p/text()").get()
        d["mw"] = response.xpath("//*[contains(text(), 'Molecular Weight')]/following-sibling::p/text()").get()
        d['mf'] = response.xpath("//*[contains(text(), 'Product Format')]/following-sibling::p/text()").get()
        d["en_name"] = response.xpath("//*[contains(text(), 'Analyte Name')]/following-sibling::p/text()").get()
        d["shipping_info"] = response.xpath(
            "//*[contains(text(), 'Shipping Temperature')]/following-sibling::p/text()").get()
        d["smiles"] = response.xpath("//*[contains(text(), 'SMILES')]/following-sibling::p/text()").get()
        d["attrs"] = prd_attrs
        yield RawData(**d)

        package = response.xpath("//*[contains(text(), 'Pack Size:')]/following-sibling::p/text()").get()
        if not package:
            return
        dd["package"] = parse_package(package)
        dd["stock_num"] = response.xpath("//*[@class='orderbar__stock-title in-stock-green']/text()").get()
        yield ProductPackage(**dd)
