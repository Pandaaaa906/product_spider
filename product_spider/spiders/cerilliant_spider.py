from urllib.parse import urljoin

from scrapy import Request

from product_spider.utils.spider_mixin import BaseSpider


# TODO the viewstate thing quite annoying
class CerilliantSpider(BaseSpider):
    name = "cerilliant"
    base_url = "https://www.cerilliant.com/"
    start_urls = ["https://www.cerilliant.com/products/catalog.aspx", ]

    def parse(self, response):
        rel_urls = response.xpath('//table[@class="hyperLnkBlackNonUnderlineToBlue"]//a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list)

    def parse_list(self, response):
        rel_urls = response.xpath('//table[@id="ContentPlaceHolder1_gvProdCatList"]//td/a')

    def parse_detail(self, response):
        d = {
            'brand': 'Cerilliant',

        }
