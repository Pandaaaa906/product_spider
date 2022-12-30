import scrapy
from lxml.etree import XML
from more_itertools import first
import json
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.parsepackage import parse_package
from product_spider.utils.spider_mixin import BaseSpider


class EDQMSpider(BaseSpider):
    name = 'ep'
    brand = 'ep'
    start_urls = ["https://crs.edqm.eu/db/4DCGI/web_catalog_XML.xml", ]
    base_url = "https://crs.edqm.eu/"

    def parse(self, response, **kwargs):
        xml = XML(response.body)
        prds = xml.xpath('//Reference')
        for prd in prds:
            cat_no = first(prd.xpath('./Order_Code/text()'), None)
            batch_num = first(prd.xpath("./Batch_No/text()"), None)  # 批号
            prd_url = f"https://crs.edqm.eu/db/4DCGI/View={first(prd.xpath('./Order_Code/text()'), '')}"
            d = {
                "brand": self.brand,
                "cat_no": cat_no,
                "cas": first(prd.xpath('./CAS_Registry_Number/text()'), None),
                "en_name": first(prd.xpath('./Reference_Standard/text()'), None),
                "info2": first(prd.xpath('./Storage/text()'), None),
                "info3": first(prd.xpath('./Quantity_per_vial/text()'), None),
                "info4": first(prd.xpath('./Price/text()'), None),
                "shipping_group": first(prd.xpath('./Shipping_group/text()'), None),
                "sales_unit": first(prd.xpath('./Sale_Unit/text()'), None),
                "prd_url": prd_url,
            }
            yield scrapy.Request(
                url=prd_url,
                callback=self.parse_detail,
                meta={
                    "product": d,
                    "batch_num": batch_num,
                }
            )

    def parse_detail(self, response):
        batch_num = response.meta.get("batch_num", None)
        d = response.meta.get("product", None)

        controlled_drug = response.xpath(
            "//*[contains(text(), 'Sales restriction')]/parent::td/following-sibling::td/font/text()"
        ).get().strip()

        shipping_info = response.xpath(
            "//*[contains(text(), 'Dispatching conditions')]/parent::td/following-sibling::td/font/text()"
        ).get().strip()

        stock_info = response.xpath(
            "//font[contains(text(), 'Availability')]/parent::td/following-sibling::td/font/text()"
        ).get().strip()

        package = response.xpath(
            "//*[contains(text(), 'Unit quantity per vial')]/parent::td/following-sibling::td/font/text()"
        ).get()
        if package is not None:
            package = parse_package(package)

        cost = response.xpath(
            "//*[contains(text(), 'Price*')]/parent::td/following-sibling::td/font[last()-1]/text()"
        ).get()
        if cost is not None:
            cost = cost.strip()

        currency = response.xpath(
            "//*[contains(text(), 'Price*')]/parent::td/following-sibling::td/font[last()]/text()"
        ).get()
        if currency is not None:
            currency = currency.strip()

        sales_unit = d.pop('sales_unit', '1')
        d["shipping_info"] = shipping_info
        d["stock_info"] = stock_info
        d["attrs"] = json.dumps({
            "controlled_drug": controlled_drug,
        })
        yield RawData(**d)

        if not package:
            return

        package = package if sales_unit == '1' else f'{package}*{sales_unit}'
        dd = {
            "brand": self.name,
            "cat_no": d["cat_no"],
            "package": package,
            "cost": cost,
            "currency": currency,
            "attrs": json.dumps({
                "batch_num": batch_num
            })
        }
        yield ProductPackage(**dd)

        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id": f'{self.name}_{d["cat_no"]}_{dd["package"]}',
            "en_name": d["en_name"],
            "cas": d["cas"],
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'cost': dd['cost'],
            "currency": dd["currency"],
            "prd_url": d["prd_url"],
            "stock_info": d["stock_info"],
        }
        dddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id": f'{self.name}_{d["cat_no"]}',
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'discount_price': dd['cost'],
            'price': dd['cost'],
            'cas': d["cas"],
            'currency': dd["currency"],
        }
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)
