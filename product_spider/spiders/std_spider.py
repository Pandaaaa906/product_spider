import re
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class STDSpider(BaseSpider):
    name = "std"
    start_urls = ["http://www.standardpharm.com/portal/list/index/id/11.html", ]
    base_url = "http://www.standardpharm.com/"

    def parse(self, response):
        a_nodes = response.xpath('//ul[@class="pro"]/li/a')
        for a in a_nodes:
            url = urljoin(self.base_url, a.xpath('./@href').get(""))
            parent = getattr(re.search(r'.+(?=\s\()', a.xpath('./text()').get()), "group")()
            yield Request(url, callback=self.list_parse, meta={"parent": parent})

    def list_parse(self, response):
        nodes = response.xpath('//ul[@class="pro"]/li')
        tmp = './/*[contains(text(),{!r})]/text()'
        for node in nodes:
            d = {
                "brand": "STD",
                "parent": response.meta.get('parent'),
                "cat_no": node.xpath(tmp.format("STD No.")).get("").replace("STD No.", "").strip(),
                "cas": node.xpath(tmp.format("CAS No.")).get("").replace("CAS No.", "").strip(),
                "en_name": node.xpath('./h3//p/text()').get(),
                "img_url": urljoin(self.base_url, node.xpath('./span/img/@src').get()),
                "mf": node.xpath(tmp.format("Chemical Formula")).get("").replace("Chemical Formula :", "").strip(),
                "prd_url": urljoin(self.base_url, node.xpath('./a/@href').get('')),
            }
            yield RawData(**d)

