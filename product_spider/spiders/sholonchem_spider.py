from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class SholonChemSpider(BaseSpider):
    name = "sholonchem"
    start_urls = ["https://www.sholonchem.com/listing/29.html"]

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//div[@class="list-pro-nav row"]//a')
        for a_node in a_nodes:
            rel_url = a_node.xpath('./@href').get()
            parent = strip(a_node.xpath('./text()').get())
            yield Request(
                url=urljoin(response.url, rel_url),
                callback=self.parse_list,
                meta={"parent": parent}
            )

    def parse_list(self, response):
        rows = response.xpath('//ul[@class="list-pro-sb"]')
        for row in rows:
            cas = row.xpath('./li[2]/p/text()').get()
            img_url = row.xpath('.//img/@src').get()
            d = {
                "brand": self.name,
                "parent": response.meta.get("parent"),
                "cat_no": cas,
                "cas": cas,
                "en_name": row.xpath('./li[3]/p/text()').get(),
                "chs_name": row.xpath('./li[4]/p/text()').get(),
                "img_url": img_url and urljoin(response.url, img_url,)
            }
            yield RawData(**d)

