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
                "parent": None,
                "cat_no": first(prd.xpath('./Order_Code/text()'), None),
                "cas": first(prd.xpath('./CAS_Registry_Number/text()')),
                "en_name": first(prd.xpath('./Reference_Standard/text()')),
                "img_url": None,
                "mf": None,
                "mw": None,
                "info2": first(prd.xpath('./Storage/text()')),
                "prd_url": f"https://crs.edqm.eu/db/4DCGI/View={prd.xpath('./Order_Code/text()').get()}",
            }
            yield RawData(**d)

