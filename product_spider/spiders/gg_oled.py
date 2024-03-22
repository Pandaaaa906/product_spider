import json

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class GGOledSpider(BaseSpider):
    name = "gg-oled"
    start_urls = ["https://www.gg-oled.cn/category/oled%e6%9d%90%e6%96%99/"]

    def parse(self, response, **kwargs):
        urls = response.xpath('//div[@class="hover_box hover_box_product"]/a/@href').getall()
        for url in urls:
            yield Request(
                url=url,
                callback=self.parse_detail
            )
        next_page = response.xpath('//span[@aria-current="page"]/following-sibling::a/@href').get()
        if next_page:
            yield Request(
                url=next_page,
                callback=self.parse
            )

    def parse_detail(self, response):
        tmpl = "//*[text()={!r}]/following-sibling::*//text()"
        attrs = {
            "density": response.xpath(tmpl.format("密度")).get(),
            "boiling_point": response.xpath(tmpl.format("沸点")).get(),
            "flash_point": response.xpath(tmpl.format("闪点")).get(),
            "melting_point": response.xpath(tmpl.format("熔点")).get(),
        }
        cas = strip(''.join(response.xpath(tmpl.format("CAS No.")).getall()))
        d = {
            "brand": self.name,
            "cat_no": cas,
            "parent": ";".join(response.xpath('//div[@class="product_meta"]//a/text()').getall()),
            "chs_name": response.xpath(tmpl.format("产品名称")).get(),
            "cas": cas,
            "mf": response.xpath(tmpl.format("分子式")).get(),
            "mw": response.xpath(tmpl.format("分子量")).get(),
            "purity": response.xpath(tmpl.format("纯度")).get(),
            "appearance": response.xpath(tmpl.format("外观")).get(),
            "prd_url": response.url,
            "img_url": response.xpath('//figure//img/@src').get(),
            "attrs": json.dumps(attrs)
        }
        yield RawData(**d)


