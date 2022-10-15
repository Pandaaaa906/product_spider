from urllib.parse import urljoin
from string import ascii_lowercase
import json

from scrapy.http import JsonRequest

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class SVAKLifeSciencesSpider(BaseSpider):
    name = "svak"
    start_urls = ["https://www.svaklifesciences.com/products.aspx"]
    base_url = "https://www.svaklifesciences.com/"

    def start_requests(self):
        for char in ascii_lowercase:
            yield JsonRequest(
                url="https://www.svaklifesciences.com/bind.aspx/alphasearch",
                data={"alpha": char},
                callback=self.parse,
            )

    def parse(self, response, **kwargs):
        text = json.loads(response.text).get("d", None)
        if not text:
            return
        result = json.loads(text)
        for res in result:
            catalog_id = res.get("Id", None)
            yield JsonRequest(
                url=f"https://www.svaklifesciences.com/bind.aspx/prodetails",
                data={"catid": catalog_id},
                callback=self.parse_detail,
            )

    def parse_detail(self, response):
        text = json.loads(response.text).get("d", None)
        if not text:
            return
        result = json.loads(text)
        for res in result:
            parent = res.get("CategoryName", None)
            cat_no = res.get("pid", None)
            en_name = res.get("SubCatName", None)
            cas = res.get("CasNo", None)
            mf = res.get("MFormula", '').replace(" ", "")
            mw = res.get("MWeight", None)
            prd_url = urljoin(self.base_url, res.get("seo_url", None))
            img_url = res.get("ImageName", None)
            if img_url:
                img_url = urljoin("https://www.svaklifesciences.com/images/Uploads_Images/", img_url)

            d = {
                "parent": parent,
                "cat_no": cat_no,
                "brand": self.name,
                "en_name": en_name,
                "cas": cas,
                "mf": mf,
                "mw": mw,
                "img_url": img_url,
                "prd_url": prd_url,
            }
            yield RawData(**d)
