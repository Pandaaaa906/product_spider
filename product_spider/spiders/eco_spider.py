from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class ECOSpider(BaseSpider):
    name = "eco_prds"
    start_urls = ["http://eco-canada.com/search/", ]
    base_url = "http://eco-canada.com/"

    def parse(self, response):
        values = tuple(set(response.xpath('//div[@class="pardrug"]//select/option[position()>1]/@value').extract()))
        for value in values:
            url = f"http://eco-canada.com/search/?ptag={value}"
            yield Request(url, meta={"parent": value}, callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//div[contains(@class, "pro_list")]/div[@class="pro_title"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin(self.base_url, url), meta=response.meta, callback=self.detail_parse)

    def detail_parse(self, response):
        tmp = '//span[contains(text(),"{}")]/following-sibling::font/text()'
        d = {
            "brand": "ECO",
            "parent": response.meta.get("parent"),
            "cat_no": response.xpath(tmp.format("Catalogue number")).get(),
            "cas": response.xpath(tmp.format("CAS Number")).get(),
            "en_name": response.xpath('//div[@class="p_vtitle"]/text()').get(),
            "img_url": urljoin(self.base_url,
                               response.xpath('//div[@class="p_viewimg pcshow"]//img/@src').get()),
            "mf": response.xpath(tmp.format("Molecular Formula")).get(),
            "mw": response.xpath(tmp.format("Molecular Weight")).get(),
            "prd_url": response.url,
        }
        yield RawData(**d)

