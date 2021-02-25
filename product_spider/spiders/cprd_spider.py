from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class CPRDSpider(BaseSpider):
    name = "cprd"
    tmp = 'http://c-prd.com/index.php/list-20/page/{page}'
    start_urls = ['http://c-prd.com/index.php/list-20/page/1']
    base_url = "http://c-prd.com/"

    def parse(self, response):
        rel_urls = response.xpath('//h3/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

        next_page = response.xpath('//a[contains(@class, "page-num-current")]/following-sibling::a[text()!="Next"]/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse)

    def parse_detail(self, response):
        tmp = '//strong[contains(text(),{!r})]/following-sibling::text()'
        rel_img = response.xpath('//article//a/img/@src').get()
        d = {
            "brand": "cprd",
            # "parent": response.xpath('//p[@class="catalogue_number"]/a/text()').get(),
            "cat_no": strip(response.xpath(tmp.format("Catalogue Number:")).get()),
            "cas": strip(response.xpath(tmp.format("CAS Number:")).get()),
            "en_name": strip(response.xpath(tmp.format("Chemical Name:")).get()),
            "img_url": rel_img and urljoin(response.url, rel_img),
            "mf": strip(response.xpath(tmp.format("Molecular Formula:")).get()),
            "mw": strip(response.xpath(tmp.format("Molecular Weight:")).get()),
            "prd_url": response.url,
        }
        yield RawData(**d)
