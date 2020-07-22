from lxml.etree import XML
from more_itertools import first

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class EDQMSpider(BaseSpider):
    name = "ep"
    start_urls = ["https://crs.edqm.eu/db/4DCGI/web_catalog_XML.xml", ]
    base_url = "https://crs.edqm.eu/"

    def parse(self, response):
        xml = XML(response.body)
        prds = xml.xpath('//Reference')
        for prd in prds:
            d = {
                "brand": "EP",
                "cat_no": first(prd.xpath('./Order_Code/text()'), None),
                "cas": first(prd.xpath('./CAS_Registry_Number/text()'), None),
                "en_name": first(prd.xpath('./Reference_Standard/text()'), None),
                "info2": first(prd.xpath('./Storage/text()'), None),
                "prd_url": f"https://crs.edqm.eu/db/4DCGI/View={first(prd.xpath('./Order_Code/text()'), '')}",
            }
            yield RawData(**d)

