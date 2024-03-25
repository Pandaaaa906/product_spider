import json

import scrapy
from jsonpath_ng import parse
from scrapy import Request
from scrapy.http import JsonRequest

from product_spider.items import RawData, SupplierProduct, ProductPackage, RawSupplierQuotation
from product_spider.utils.functions import dumps
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation

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


class JkPrdSpider(scrapy.Spider):
    name = "jk"
    allowed_domains = ["jkchemical.com"]
    base_url = "http://www.jkchemical.com"
    prd_url = 'https://web.jkchemical.com/api/product-catalog/{catalog_id}/products/{page}'

    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                          'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
            # hardcoding?
            'Authorization': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MCwidW5pdCI6MjQsImd1ZXN0Ijo3NjE2OTUsInVxIjo1'
                             'NCwicm9sZXMiOm51bGwsImlhdCI6MTYyNzk2Njk4NX0.8mea_0U6wOZKvqrb-y6k689j8R1coOcnSUNOIOHyiMo',
        }
    }

    def start_requests(self):
        d = {
            'language': 196,
            'salesRegion': 1,
        }
        yield JsonRequest(
            'https://shop.jkchemical.com/uq/prod/product/tv/query/GetRootCategory',
            data=d,
            callback=self.parse
        )

    def make_request(self, catalog_id, page: int = 1):
        return Request(
            self.prd_url.format(catalog_id=catalog_id, page=page),
            meta={'page': page, 'catalog_id': catalog_id},
            callback=self.parse_list
        )

    def parse(self, response, **kwargs):
        obj = response.json()
        ret = obj.get('res', '')
        for line in ret.split('\n'):
            catalog_id, *_ = line.split('\t')
            yield self.make_request(catalog_id)

    def parse_list(self, response):
        obj = response.json()
        prds = obj.get('hits', [])
        for prd in prds:
            if not prd:
                continue
            d = {
                'brand': parse_brand(prd.get('brand', {}).get('name')),
                'cat_no': prd.get('origin'),
                'en_name': prd.get('description'),
                'chs_name': prd.get('descriptionC'),
                'cas': cas if (cas := prd.get('CAS')) != '0' else None,
                'purity': prd.get('purity'),
                'mdl': prd.get('mdlnumber'),
                'img_url': (img_url_id := prd.get('imageUrl')) and f'https://static.jkchemical.com/Structure/{img_url_id[:3]}/{img_url_id}.png',
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
        yield self.make_request(catalog_id, cur_page + 1)

    def parse_package(self, response):
        tmpl = '//div[text()={!r}]/following-sibling::div[1]//text()'
        d = response.meta.get("prd", {})
        cat_nodes = response.xpath('//div[./div/text()="产品分类"]/following-sibling::div[1]/div')
        categories = [
            "__".join(node.xpath('./span/a/text()').getall())
            for node in cat_nodes
        ]
        d["mf"] = response.xpath(tmpl.format("分子式")).get()
        d["mw"] = response.xpath(tmpl.format("分子量")).get()
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

