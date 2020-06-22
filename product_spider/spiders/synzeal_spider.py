import re
from string import ascii_uppercase

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class SynzealSpider(BaseSpider):
    name = "synzeal"
    allowd_domains = ["synzeal.com"]
    base_url = "https://www.synzeal.com"
    start_urls = map(lambda x: f"https://www.synzeal.com/category/{x}", ascii_uppercase)

    def parse(self, response):
        l_url = response.xpath("//h4[@class='title']/a/@href").extract()
        for rel_url in l_url:
            yield Request(self.base_url + rel_url, callback=self.list_parse, meta=response.meta, headers=self.headers)

    def list_parse(self, response):
        urls = response.xpath('//div[@class="product-item"]//h2/a/@href').extract()
        for rel_url in urls:
            yield Request(self.base_url + rel_url, callback=self.detail_parse, meta=response.meta, headers=self.headers)

    def detail_parse(self, response):
        en_name = response.xpath('//h1[@class="titleproduct"]/text()').get(default="")
        en_name = re.sub(r'\r?\n', "", en_name)
        d = {
            'brand': "SynZeal",
            'en_name': en_name.strip(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': response.xpath('//span[contains(@id,"sku")]/text()').get(default=""),
            'cas': response.xpath('//span[contains(@id,"mpn")]/text()').get(default=""),
            'stock_info': response.xpath('//span[contains(@id,"ProductInstockStatus")]/text()').get(
                default=""),
            'mf': response.xpath(
                '//span[contains(text(),"Molecular Formula")]/following-sibling::span/text()').get(
                default=""),
            'mw': response.xpath(
                '//span[contains(text(),"Molecular Weight")]/following-sibling::span/text()').get(default=""),
            'info1': response.xpath('//b[contains(text(),"Synonyms")]/following-sibling::span/text()').get(
                default="").strip(),
            'parent': response.xpath('//div[contains(@class, "cath1title")]/h1/text()').get(default=""),
            'img_url': response.xpath(
                '//div[@class="maindiv-productdetails"]//div[@class="picture"]//img/@src').get(),
        }
        yield RawData(**d)

