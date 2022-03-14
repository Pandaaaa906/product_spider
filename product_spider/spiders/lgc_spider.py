import json
from urllib.parse import parse_qsl, urlparse
import scrapy
from more_itertools.more import first
from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import JsonSpider


class LGCSpider(JsonSpider):
    name = "lgc"
    allowd_domains = ["lgcstandards.com"]
    start_urls = ["https://www.lgcstandards.com/US/en/search/?text=LGC"]
    base_url = "https://www.lgcstandards.com/US/en"

    def start_requests(self):
        yield scrapy.Request(
            url="https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=LGC%3A:itemtype:LGCProduct:itemtype:ATCCProduct&country=US&lang=en&defaultB2BUnit=",
            callback=self.parse,
        )

    def parse(self, response, **kwargs):
        products = json.loads(response.text).get("products", [])
        if products is []:
            return
        for prd in products:
            cat_no = prd.get("code")
            en_name = prd.get("name")
            img_url = prd.get("analyteImageUrl")
            prd_url = '{}{}'.format(self.base_url, prd.get("url"))
            if (mw := prd.get("listMolecularWeight")) is None:
                mw = []
            mw = ''.join(mw)
            if (mf := prd.get("listMolecularFormula")) is None:
                mf = ''.join([])
            else:
                mf = first(mf).replace(' ', '')

            if (cas := prd.get("listCASNumber")) is None:
                cas = []
            cas = ''.join(cas)
            package = ''.join(prd.get("uom", '').split())
            d = {
                "brand": self.name,
                "cat_no": cat_no,
                "en_name": en_name,
                "mf": mf,
                "cas": cas,
                "mw": mw,
                "prd_url": prd_url,
                "img_url": img_url,
            }
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "currency": "USD",
            }
            yield RawData(**d)
            yield ProductPackage(**dd)
        current_page_num = int(dict(parse_qsl(urlparse(response.url).query)).get('currentPage', None))
        if current_page_num is not None:
            current_page_num = current_page_num + 1
            yield scrapy.Request(
                url=f"https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage={current_page_num}&q=LGC%3A:itemtype:LGCProduct:itemtype:ATCCProduct&country=US&lang=en&defaultB2BUnit=",
                callback=self.parse
            )
