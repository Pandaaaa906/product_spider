import scrapy
from lxml.etree import XML
from more_itertools import first
import json
from product_spider.items import RawData, ProductPackage
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

        prd_attrs = json.dumps({
            "controlled_drug": controlled_drug,
        })
        package_attrs = json.dumps({
            "batch_num": batch_num
        })
        dd = {"brand": self.name, "cat_no": d["cat_no"], "package": package, "cost": cost, "currency": currency}
        d["shipping_info"] = shipping_info
        d["attrs"] = prd_attrs
        dd["attrs"] = package_attrs

        yield RawData(**d)
        yield ProductPackage(**dd)
