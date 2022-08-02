import json
from urllib.parse import urlencode

import scrapy
from more_itertools import first

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class ATCCSpider(BaseSpider):
    name = "atcc"
    start_urls = [
        "https://www.atcc.org/cell-products#t=productTab&numberOfResults=24",
        "https://www.atcc.org/microbe-products#t=productTab&numberOfResults=24",
    ]
    base_url = "https://www.atcc.org/"

    def parse(self, response, **kwargs):
        site_core_item_uri = response.xpath("//div[@class='CoveoForSitecoreContext']/@data-sc-item-uri").get()
        site_name = response.xpath("//div[@class='CoveoForSitecoreContext']/@data-sc-site-name").get()

        # TODO
        for i in range(0, 1000):
            yield scrapy.FormRequest(
                url="{}{}".format("https://www.atcc.org/coveo/rest/v2?", urlencode({
                    "sitecoreItemUri": site_core_item_uri,
                    "siteName": site_name
                })),
                formdata={
                    "firstResult": f"{i*24}",
                    "numberOfResults": "1000",
                },
                callback=self.parse_detail,
                meta={
                    "sitecoreItemUri": site_core_item_uri,
                    "siteName": site_name,
                    "prd_url": response.url
                },
            )

    def parse_detail(self, response):
        results = json.loads(response.text).get("results", [])
        if not results:
            return
        for res in results:
            en_name = res.get("Title", None)
            data = res.get("raw", {})
            parent = first(data.get("productz32xcategory", []), None)
            cat_no = data.get("z95xname", None)
            bio_level = data.get("biosafetyz32xlevel", None)  # 生物安全等级
            prd_url = f"https://www.atcc.org/products/{cat_no}"

            prd_attrs = json.dumps({
                "bio_level": bio_level
            })

            d = {
                "brand": self.name,
                "parent": parent,
                "en_name": en_name,
                "cat_no": cat_no,
                "prd_url": prd_url,
                "attrs": prd_attrs,
            }

            yield RawData(**d)
