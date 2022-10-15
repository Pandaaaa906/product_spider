import json
import logging
import re
from urllib.parse import urljoin, urlencode
import scrapy
from more_itertools import first
import jsonpath
from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.spider_mixin import BaseSpider


class ChromaDexSpider(BaseSpider):
    name = "chromadex"
    start_urls = (f"https://standards.chromadex.com/{x}" for x in
                  ("reference-standard-material", "botanical-reference-material", "kits")
                  )
    base_url = "https://standards.chromadex.com/"
    brand = "chromadex"
    cat_no_set = set()

    def parse(self, response, **kwargs):
        rows = response.xpath("//span[@itemprop='name']/parent::a")
        for row in rows:
            url_component = row.xpath("./@href").get()
            url = urljoin(self.base_url, url_component)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={
                    "url_component": url_component,
                }
            )
        next_url = urljoin(self.base_url,
                           response.xpath("//ul[@class='global-views-pagination-links ']/li[last()]/a/@href").get())
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
            )

    def parse_detail(self, response):
        url_component = response.meta.get("url_component")
        d = {
            "prd_url": response.url,
        }
        params = {
            "c": "5337332",
            "country": "US",
            "currency": "USD",
            "fieldset": "details",
            "include": "facets",
            "language": "en",
            "n": "2",
            "pricelevel": "5",
            "url": url_component,
            "use_pcv": "F",
        }
        url = '{}{}'.format("https://standards.chromadex.com/api/cacheable/items?", urlencode(params))
        yield scrapy.Request(
            url=url,
            callback=self.parse_package,
            meta={
                "product": d,
            },
        )

    def parse_package(self, response):
        d = response.meta.get("product", '')
        j_obj = json.loads(response.text)
        parent = sorted(jsonpath.jsonpath(j_obj, '$..facets[1]..values..url'))
        d["parent"] = '_'.join(parent)
        item = first(j_obj.get("items"), None)
        if item is None:
            logging.info("没有找到item！")
            return None
        d["brand"] = self.name
        d["info2"] = item.get("custitem_cdc_storage_condition", None)  # 储存条件
        d["grade"] = item.get("custitem_cdx_grade", None)
        d["shipping_info"] = item.get("custitem_shipping_conditions", None)
        d["purity"] = item.get("custitem_purity", None)
        d["appearance"] = item.get("custitem_appearance", None)
        d["mw"] = item.get("custitem_formula_weight", '')
        d['mf'] = item.get("custitem_chemical_formula", None)
        d['einecs'] = item.get("custitem_einecs", None)
        d["en_name"] = item.get("displayname", None)
        d["cas"] = item.get("custitem_cd_cas_number", '')
        d["img_url"] = None
        if d["cas"] is not None and d["cas"] != '' and d['cas'] != 'NULL':
            d["img_url"] = f"https://standards.chromadex.com/Images/Product%20Images/{d['cas']}.01.jpg"
        melting_point = item.get("custitem_melting_point", '')  # 熔点
        prd_attrs = json.dumps({
            "melting_point": melting_point,
        })
        d["attrs"] = prd_attrs

        if "matrixchilditems_detail" not in item:
            raw_cat_no = re.match(r'[A-Z]{3}-\d+', item.get("itemid", ''))
            if raw_cat_no:
                d["cat_no"] = raw_cat_no.group()
                yield RawData(**d)
        res = item.get("matrixchilditems_detail", [])
        if not res:
            return None
        for i in res:
            cat_no = re.match(r'[A-Z]{3}-\d+', i.get("itemid", '')).group()
            package_grade = i.get("custitem_gradeoption", '')
            package = i.get("custitem_sizeoption", '')
            cost = first(jsonpath.jsonpath(i.get("onlinecustomerprice_detail", []), '$..onlinecustomerprice'), '')
            package_attrs = json.dumps({
                "package_grade": package_grade
            })
            d["cat_no"] = cat_no
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "cost": cost,
                "currency": "USD",
                "attrs": package_attrs,
            }

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "parent": d["parent"],
                "en_name": d["en_name"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
                "img_url": d["img_url"],
                "prd_url": d["prd_url"],
            }

            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)
            if cat_no not in self.cat_no_set:
                yield RawData(**d)
                self.cat_no_set.add(cat_no)

    def close(self, spider, reason):
        print(self.cat_no_set)
