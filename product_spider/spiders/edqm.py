from lxml.etree import XML
from more_itertools import first

from product_spider.items import RawData, ProductPackage
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
            d = {
                "brand": self.brand,
                "cat_no": cat_no,
                "cas": first(prd.xpath('./CAS_Registry_Number/text()'), None),
                "en_name": first(prd.xpath('./Reference_Standard/text()'), None),
                "info2": first(prd.xpath('./Storage/text()'), None),
                "info3": first(prd.xpath('./Quantity_per_vial/text()'), None),
                "info4": first(prd.xpath('./Price/text()'), None),
                "shipping_group": first(prd.xpath('./Shipping_group/text()'), None),
                "prd_url": f"https://crs.edqm.eu/db/4DCGI/View={first(prd.xpath('./Order_Code/text()'), '')}",
            }
            yield RawData(**d)

            price = first(prd.xpath('./Price/text()'), None)
            yield ProductPackage(
                brand=self.brand,
                cat_no=cat_no,
                package=first(prd.xpath('./Quantity_per_vial/text()'), None),
                price=price and price.replace('€', ''),
                currency='EUR',
            )

