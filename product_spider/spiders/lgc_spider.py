import json
import re
from itertools import chain
from os import getenv
from urllib import parse
from urllib.parse import urljoin

from scrapy import Request, FormRequest

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import strip, dumps
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.jsonpath import jsonpath_query_nth, jsonpath_query_all
from product_spider.utils.spider_mixin import JsonSpider

LGC_USER = getenv('LGC_USER', 'g.m.office@cato-chem.com')
LGC_PWD = getenv('LGC_PWD', '6vS-!_hizfLJ7iS')
LGC_BRANDS = {'trc', 'lgc', 'dre', 'easi-tab'}


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
    allowed_domains = ["lgcstandards.com"]
    start_urls = [
        "https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=%3A%3AmanufacturerName%3ATRC%3Aitemtype%3ALGCProduct%3Aitemtype%3AATCCProduct&country=US&lang=en&defaultB2BUnit=",
        "https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=MM%3A%3AmanufacturerName%3AMikromol%3AmanufacturerName%3AMikromol%25E2%2584%25A2%3Aitemtype%3ALGCProduct%3Aitemtype%3AATCCProduct&country=US&lang=en&defaultB2BUnit=",
        "https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=DRE%3A%3AmanufacturerName%3ADr.%2BEhrenstorfer%3Aitemtype%3ALGCProduct%3Aitemtype%3AATCCProduct&country=US&lang=en&defaultB2BUnit=",
    ]
    base_url = "https://www.lgcstandards.com/CA/en"
    custom_settings = {
        'CONCURRENT_REQUESTS': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 3,
        'CONCURRENT_REQUESTS_PER_IP': 3,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 5,
        'AUTOTHROTTLE_MAX_DELAY': 60,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1,
        'COOKIES_ENABLED': True,
        'COOKIES_DEBUG': True,
    }

    def start_requests(self):
        # perform login
        yield Request(self.base_url, callback=self.login)

    def login(self, response):
        csrf_token = response.xpath('//input[@name="CSRFToken"]/@value').get()
        yield FormRequest(
            'https://www.lgcstandards.com/CA/en/j_spring_security_check',
            formdata={
                "j_username": LGC_USER,
                "j_password": LGC_PWD,
                "CSRFToken": csrf_token,
            },
            callback=self.real_start_requests,
            meta={
                "handle_httpstatus_all": True,
            },
        )

    def real_start_requests(self, response, post_request=None):
        # check login status
        # start default
        yield from super().start_requests()

    def parse(self, response, **kwargs):
        products = json.loads(response.text).get("products", [])
        if not products:
            return
        for prd in products:
            brand = parse_brand((brand := (prd.get("brand", {}).get("name", None))) and brand.lower())
            cat_no = prd.get("code", None)
            prd_url = '{}{}'.format(self.base_url, prd.get("url"))

            d = {
                "brand": brand,
                "cat_no": cat_no,
            }
            yield Request(
                url=prd_url,
                callback=self.parse_detail,
                meta={"product": d}
            )
        parsed_url = parse.urlparse(response.url)
        query_d = dict(parse.parse_qsl(parsed_url.query))
        current_page_num = query_d.get('currentPage', None)
        if current_page_num is not None:
            current_page_num = int(current_page_num) + 1
            query_d['currentPage'] = current_page_num
            parsed_url = list(parsed_url)
            parsed_url[4] = parse.urlencode(query_d)
            yield Request(
                url=parse.urlunparse(parsed_url),
                callback=self.parse
            )

    def parse_detail(self, response):
        tmpl = "//*[contains(text(), {!r})]/following-sibling::p/text()"
        brand = jsonpath_query_nth(response.meta, '$.product.brand')
        cat_no = jsonpath_query_nth(response.meta, '$.product.cat_no')
        if brand == 'trc' and cat_no:
            cat_no = (m := re.search(r'[A-Z]\d+(-KIT)?', cat_no)) and m.group()
        api_name = ''.join(response.xpath("//*[contains(text(), 'API Family')]/following-sibling::a/text()").getall())
        t = response.xpath('//div[@class="product__details-left"]/script/text()').get()
        raw_product = (m := re.search(r'var PARENT_PRODUCT = (\{.+});', t)) and m.group(1)
        try:
            product = json.loads(raw_product)
        except Exception as e:
            product = {}
        raw_packages = (m := re.search(r'var PACK_SIZE_PRODUCTS = (\[\{.+}]);', t)) and m.group(1)
        try:
            packages = json.loads(raw_packages)
        except Exception as e:
            self.logger.warning(e)
            packages = []

        coa_urls = list(chain.from_iterable(d.keys() for d in jsonpath_query_all(packages, '$[*]..coaURLs') if d))
        categories = ''.join(
            response.xpath("//*[contains(text(), 'Product Categories')]/following-sibling::p//a/text()").getall())
        prd_attrs = {
            "api_name": strip(api_name),
            "inchi": strip(response.xpath(tmpl.format('InChI')).get()),
            "iupac": strip(response.xpath(tmpl.format('IUPAC')).get()),
            "coa_urls": coa_urls,
            "impact_product_type": product.get('impactProductTypes')
        }
        img_url = response.xpath('//zoom-image/@image-src').get()

        d = {
            "brand": brand,
            "cat_no": cat_no,
            "prd_url": response.url,
            "img_url": img_url and urljoin(response.url, img_url),

            "parent": api_name or categories,
            "info2": response.xpath(tmpl.format('Storage Temperature')).get(),
            # 储存条件
            "cas": response.xpath("//*[contains(text(), 'CAS Number')]/following-sibling::p/a/text()").get(),
            "mw": response.xpath(tmpl.format('Molecular Weight')).get(),
            'mf': response.xpath(tmpl.format('Molecular Formula')).get(),
            "en_name": response.xpath(tmpl.format('Analyte Name')).get(),
            "shipping_info": response.xpath(tmpl.format('Shipping Temperature')).get(),
            "smiles": response.xpath(tmpl.format('SMILES')).get(),
            "attrs": dumps({k: v for k, v in prd_attrs.items() if v}),
        }
        if d['brand'] in LGC_BRANDS:
            yield RawData(**d)
        yield SupplierProduct(**rawdata_to_supplier_product(d, self.name, self.name))

        for pkg in packages:
            dd = {
                "brand": d["brand"],
                "cat_no": d["cat_no"],
                "package": pkg.get('packSize'),
                "cat_no_unit": pkg.get('code'),
                "delivery_time": jsonpath_query_nth(pkg, '$.stock.message.title1Msg'),
            }
            yield Request(
                f"https://www.lgcstandards.com/CA/en/prices?{parse.urlencode({'productCodeList': dd['cat_no_unit']})}",
                callback=self.parse_prise,
                meta={"pkg": dd, "product": d}
            )

    def parse_prise(self, response):
        dd = response.meta.get("pkg")
        d = response.meta.get("product")

        j_obj = json.loads(response.text)
        pkg_data = j_obj.get(dd['cat_no_unit'], {})
        cost = jsonpath_query_nth(pkg_data, f"$.price.value")
        dd = {
            **dd,
            "cost": cost,
            "price": cost,
            "currency": jsonpath_query_nth(pkg_data, f"$.price.currencyIso"),
        }
        if dd['brand'] in LGC_BRANDS:
            yield ProductPackage(**dd)
        if not dd['cost']:
            return
        yield RawSupplierQuotation(**product_package_to_raw_supplier_quotation(d, dd, self.name, self.name))
