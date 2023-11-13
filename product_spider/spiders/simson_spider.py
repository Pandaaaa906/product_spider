from string import ascii_lowercase
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class SimsonSpider(BaseSpider):
    name = "simson"
    allowed_domains = ["simsonpharma.com"]
    base_url = "http://simsonpharma.com"
    start_urls = [f'https://www.simsonpharma.com/products-list/{a}' for a in ascii_lowercase]

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//ul[@id="product-section"]//a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list)

    def parse_list(self, response):
        rel_urls = response.xpath('//div[@class="card"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

    def parse_detail(self, response):
        tmpl = '//li[contains(text(), {!r})]/span/text()'
        img = response.xpath('//section[contains(@class, "products-details-section")]//picture/img/@src').get()
        d = {
            "brand": self.name,
            "parent": response.xpath('//ol[@class="breadcrumb"]/li[position()=last()-1]/a/text()').get(),
            "cat_no": response.xpath(tmpl.format("CAT. No.")).get(),
            "en_name": response.xpath('//section[contains(@class, "products-details-section")]//div/h1/text()').get(),
            "cas": response.xpath(tmpl.format("CAS. No.")).get(),
            "mf": formula_trans(response.xpath(tmpl.format("Mol. F.")).get()),
            "mw": response.xpath(tmpl.format("Mol. Wt.")).get(),
            "stock_info": response.xpath(tmpl.format("Stock Status")).get(),
            "info1": response.xpath(tmpl.format("Chemical Name:")).get(),

            "img_url": img and urljoin(response.url, img),
            "prd_url": response.url,
        }
        yield RawData(**d)
