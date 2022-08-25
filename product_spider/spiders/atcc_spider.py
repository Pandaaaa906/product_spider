import json
from urllib.parse import urlencode, urljoin

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

    def start_requests(self):
        yield scrapy.Request(
            url="https://www.atcc.org/",
            callback=self.parse_catalog
        )

    def parse_catalog(self, response):
        rows = response.xpath("//li[@class='primary-nav__item'][position()<3]/@data-menu").getall()
        for row in rows:
            for url in [urljoin(self.base_url, url) for url in
                        [i.get("url", []) for i in json.loads(row).get("children", [])]]:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse
                )

    def parse(self, response, **kwargs):
        site_core_item_uri = response.xpath("//div[@class='CoveoForSitecoreContext']/@data-sc-item-uri").get()
        site_name = response.xpath("//div[@class='CoveoForSitecoreContext']/@data-sc-site-name").get()
        yield from self._fetch_page(site_core_item_uri, site_name, offset=0)

    def _fetch_page(self, site_core_item_uri, site_name, offset=0, limit=1000):
        yield scrapy.FormRequest(
            url="{}{}".format("https://www.atcc.org/coveo/rest/v2?", urlencode({
                "sitecoreItemUri": site_core_item_uri,
                "siteName": site_name
            })),
            formdata={
                "firstResult": f"{offset * limit}",
                "numberOfResults": f"{limit}",
            },
            callback=self.parse_detail,
            meta={
                "sitecoreItemUri": site_core_item_uri,
                "siteName": site_name,
                "offset": offset,
            },
        )

    def parse_detail(self, response):
        raw_result = json.loads(response.text)
        results = raw_result.get("results", [])
        site_core_item_uri = response.meta.get('sitecoreItemUri', 0)
        site_name = response.meta.get('siteName', 0)
        cur_offset = response.meta.get('offset', 0)

        if not results:
            return
        for res in results:
            en_name = res.get("title", None)
            data = res.get("raw", {})
            parent = first(data.get("productz32xcategory", []), None)
            cat_no = data.get("atccz32xnumber", None)
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

        yield from self._fetch_page(site_core_item_uri, site_name, offset=cur_offset + 1)
