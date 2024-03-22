import json
from urllib.parse import urlencode
import jsonpath
import scrapy
from more_itertools import first

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class CaymanchemPrdSpider(BaseSpider):
    """caymanchem"""
    name = 'caymanchem'
    base_url = "https://www.caymanchem.com/"
    start_urls = ["https://www.caymanchem.com/products/categories", ]

    def start_requests(self):
        yield scrapy.Request(
            url="https://www.caymanchem.com/solr/cchRAPTA/select?q=*:*&rows=99999&wt=json",
            callback=self.parse,
        )

    def parse(self, response, *args, **kwargs):
        j_obj = json.loads(response.text)
        _ids = jsonpath.jsonpath(j_obj, '$..response..docs..id')
        for _id in _ids:
            yield scrapy.Request(
                url=f"https://www.caymanchem.com/search?fq=raptas:{_id}",
                callback=self.parse_list,
                meta={
                    "_id": _id,
                },
            )

    def parse_list(self, response):
        _id = response.meta.get("_id")
        params = {
            "q": "*:*",
            "qf": "catalogNum^2000 exactname^5000 exactSynonyms^4000 edgename^4000 synonymsPlain^2000 formalNameDelimited^1500 vendorItemNumber^4000 casNumber^10000 name^1500 ngram_name^1000 delimited_name^1500 tagline^0.01 keyInformation^0.01 keywords^200 inchi^20000 inchiKey^20000 smiles^20000 ngram_synonym^400 ngram_general^0.01",
            "rows": "30000",
            "defType": "edismax",
            "q.op": "AND",
            "enableElevation": "true",
            "bq": '',
            "facet": "true",
            "facet.field": "newProduct",
            "facet.field": "raptas",
            "facet.limit": "100000",
            "facet.mincount": "1",
            "wt": "json",
            "fq": f"(websiteNotSearchable:false AND europeOnly:false AND  !raptas:RAP000101) AND (raptas:{_id})",
            "start": "0",
            "bust": "lfnojz440ga",
            "version": "2.2",
            "sort": "activationDate desc",
        }
        url = '{}{}'.format("https://www.caymanchem.com/solr/cchProduct/select?", urlencode(params))
        yield scrapy.Request(
            url=url,
            callback=self.parse_detail,
        )

    def parse_detail(self, response):
        j_obj = json.loads(response.text)
        rows = first(jsonpath.jsonpath(j_obj, '$..response..docs'), [])
        for row in rows:
            cat_no = row.get("catalogNum", None)
            info1 = row.get("formalName", None)
            info2 = row.get("storageTemp", None)
            coa_url = '{}{}'.format("https://cdn.caymanchem.com/cdn/insert/", row.get("productInsert", None))
            grade = row.get("itemGroupId", None)
            en_name = row.get("name", None)
            img_url = '{}{}'.format("https://cdn2.caymanchem.com/cdn/productImages/", row.get("productImage", None))
            purity = row.get("purity", None)
            smiles = row.get("smiles", None)
            mw = row.get("formulaWeight", None)
            inchi = row.get("inchi", None)
            inchiKey = row.get("inchiKey", None)
            shipping_info = row.get("shippingInstructions", None)
            cas = row.get("casNumber", None)
            safety_data_sheet = f"https://cdn.caymanchem.com/cdn/msds/{cat_no}m.pdf"
            prd_url = f"https://www.caymanchem.com/product/{cat_no}"

            prd_attrs = json.dumps({
                "inchi": inchi,
                "inchiKey": inchiKey,
            })

            d = {
                "brand": self.name,
                "cat_no": cat_no,
                "info1": info1,
                "info2": info2,
                "cas": cas,
                "mw": mw,
                "smiles": smiles,
                "purity": purity,
                "en_name": en_name,
                "img_url": img_url,
                "grade": grade,
                "shipping_info": shipping_info,
                "attrs": prd_attrs,
                "prd_url": prd_url,
            }
            yield RawData(**d)
            package_url = f"https://www.caymanchem.com/solr/cchProductVariant/select?q=catalogNum:({cat_no})"
            yield scrapy.Request(
                url=package_url,
                callback=self.parse_package,
                meta={
                    "product": d,
                    "coa_url": coa_url,
                    "safety_data_sheet": safety_data_sheet,
                },
            )

    def parse_package(self, response):
        d = response.meta.get("product")
        coa_url = response.meta.get("coa_url")
        safety_data_sheet = response.meta.get("safety_data_sheet")
        package_attrs = json.dumps({
            "coa_url": coa_url,
            "safety_data_sheet": safety_data_sheet,
        })
        j_obj = json.loads(response.text)
        packages = jsonpath.jsonpath(j_obj, '$..response..docs..name')
        if not packages:
            return
        for package in packages:
            dd = {
                "brand": self.name,
                "cat_no": d["cat_no"],
                "package": package.replace(" ", ''),
                "currency": 'USD',
                "attrs": package_attrs,
            }
            yield ProductPackage(**dd)
