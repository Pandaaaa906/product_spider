import json
import re
from urllib.parse import urlencode, quote

import scrapy
from jsonpath_ng import parse
from scrapy import Request
from scrapy.http import JsonRequest

from product_spider.items import RawData, SupplierProduct, ProductPackage, RawSupplierQuotation
from product_spider.utils.functions import dumps, first
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider

jk_brands = {"jk"}
brand_mapping = {
    "J&K Scientific": "jk",
    "J&K": "jk",
    "J&K-Abel": "jk",
    "Agilent(安捷伦)": "agilent",
    "Dr. Ehrenstorfer": "dre",
    "EDQM(EP)": "ep",
    "Cambridge Isotope Laboratories（CIL）": "cil",
    "Life Chemicals": "life_chemicals",
    "Rieke Metals": "rieke_metals",
    "Key Organics": "key_organics",
    "Alfa Aesar": "alfa",
    "Polymer Source": "polymer_source",
    "Chem Service": "chemservice",
    "Acanthus Research": "acanthus",
    "NATIONAL INSTITUTE OF STANDARDS AND TECHNOLOGY": "nist",
    "Nu-Chek": "nuchek",
    "Sigma-Aldrich": "sigma",
    "Spectrum Quality Standards": "sqs",
    "Taiwan Algal Science(台湾藻研)": "tas",
}


def parse_brand(brand: str):
    if not brand:
        return
    if brand not in brand_mapping:
        return brand.lower()
    return brand_mapping[brand]


class JkPrdSpider(BaseSpider):
    name = "jk"
    allowed_domains = ["jkchemical.com"]
    base_url = "http://www.jkchemical.com"
    product_url = 'https://www.jkchemical.com/_next/data/o4gC8HmZ5IFTLEhskqrzE/search/{catalog}.json'
    catalog_url = 'https://www.jkchemical.com/_next/data/o4gC8HmZ5IFTLEhskqrzE/product-catalog/{catalog_id}.json'

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'PROXY_POOL_REFRESH_STATUS_CODES': [503, 504, 429],
        'RETRY_TIMES': 10,
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                          'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
            # hardcoding?
            'Authorization': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MCwidW5pdCI6MjQsImd1ZXN0Ijo3NjE2OTUsInVxIjo1'
                             'NCwicm9sZXMiOm51bGwsImlhdCI6MTYyNzk2Njk4NX0.8mea_0U6wOZKvqrb-y6k689j8R1coOcnSUNOIOHyiMo',
        },
    }

    def _start_requests(self):
        d = {
            'language': 196,
            'salesRegion': 1,
        }
        yield JsonRequest(
            'https://shop.jkchemical.com/uq/prod/product/tv/query/GetRootCategory',
            data=d,
            callback=self.parse
        )

    def make_request(self, catalog_id, catalog_name, page: int = 1):
        d = {
            "key": catalog_name,
            "type": 3,
            "page": page,
            "categoryId": catalog_id,
        }
        return Request(
            f"{self.product_url.format(catalog=quote(catalog_name))}?{urlencode(d)}",
            meta={'page': page, 'catalog_id': catalog_id, 'catalog_name': catalog_name},
            callback=self.parse_list
        )

    def catalog_request(self, catalog_id, catalog_name):
        return Request(
            self.catalog_url.format(catalog_id=catalog_id),
            self.parse_catalog,
            meta={"catalog_id": catalog_id, "catalog_name": catalog_name}
        )

    def parse(self, response, **kwargs):
        obj = response.json()
        ret = obj.get('res', '')
        for line in ret.split('\n'):
            m = re.match(r"(\d+)\t(\d+)\t(\S+)", line)
            if not m:
                continue
            catalog_id, _, catalog_name, *_ = m.groups()
            yield self.catalog_request(catalog_id, catalog_name=catalog_name)

    def parse_catalog(self, response):
        obj = response.json()
        if first(parse('$..__N_REDIRECT').find(obj), None):
            catalog_id = response.meta.get("catalog_id")
            catalog_name = response.meta.get("catalog_name")
            yield self.make_request(catalog_id, catalog_name)
            return
        catalogs = parse('$..currCatalog.children[*]').find(obj)
        for m in catalogs:
            catalog = m.value
            yield self.catalog_request(catalog_id=catalog.get("id"), catalog_name=catalog.get("name"))

    def parse_list(self, response):
        obj = response.json()
        prds = parse('$..productlist[*]').find(obj)
        for item in prds:
            if not item or not (t := item.value) or not (prd := t.get("props")):
                continue
            mf = prd.get('molecularFomula')
            d = {
                'brand': parse_brand(prd.get('brandName')),
                'cat_no': prd.get('origin'),
                'en_name': prd.get('englishName'),
                'chs_name': prd.get('chineseName'),
                'cas': cas if (cas := prd.get('cas')) != '0' else None,
                'purity': prd.get('purity'),
                'mf': mf.replace(" ", "") if mf else None,
                'mw': prd.get('molecularWeight'),
                'img_url': (img_url_id := prd.get(
                    'imageUrl')) and f'https://static.jkchemical.com/Structure/{img_url_id[:3]}/{img_url_id}.png',
                'prd_url': (tmp := prd.get('id')) and f'https://www.jkchemical.com/product/{tmp}'
            }

            yield SupplierProduct(**rawdata_to_supplier_product(
                d,
                platform='jk',
                vendor='jk',
            ))
            if not (prd_url := d['prd_url']):
                continue
            yield Request(prd_url, callback=self.parse_package, meta={"prd": d})

        if not prds:
            return

        cur_page = response.meta.get("page")
        catalog_id = response.meta.get("catalog_id")
        catalog_name = response.meta.get("catalog_name")
        yield self.make_request(catalog_id, catalog_name, cur_page + 1)

    def parse_package(self, response):
        d = response.meta.get("prd", {})
        cat_nodes = response.xpath('//div[./div/text()="产品分类"]/following-sibling::div[1]/div')
        categories = [
            "__".join(node.xpath('./span/a/text()').getall())
            for node in cat_nodes
        ]
        attrs = {}
        if categories:
            attrs["categories"] = categories
            d["parent"] = categories[0]
        d['attrs'] = dumps(attrs)
        if d["brand"] in jk_brands:
            yield RawData(**d)
        raw_json = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if not raw_json:
            return
        j_obj = json.loads(raw_json)
        packages = parse('$..product.packages[*]').find(j_obj)
        for m in packages:
            pkg = m.value
            package = f"{pkg.get('radioY')}{pkg.get('unit')}"
            dd = {
                "brand": d.get("brand"),
                "cat_no": d.get("cat_no"),
                "package": package,
                "cost": pkg.get("salesPrice"),
                "price": pkg.get("price"),
                "currency": pkg.get("currency"),
                "attrs": dumps({
                    "inventories": pkg.get("inventories")
                })
            }
            if dd["brand"] in jk_brands:
                yield ProductPackage(**dd)
            yield RawSupplierQuotation(**product_package_to_raw_supplier_quotation(
                d, dd, "jk", "jk",
            ))
