from string import ascii_uppercase
from urllib.parse import urljoin

from scrapy import Request

from product_spider.utils.spider_mixin import BaseSpider


# TODO No cat_no
class KarpsChemSpider(BaseSpider):
    name = "karpschem"
    allowd_domains = ["http://karpschem.in/"]
    start_urls = [f"http://karpschem.in/products.php?show={a}&page=1&catpage=1" for a in ascii_uppercase]
    base_url = "http://karpschem.in/"

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="pagination row"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list)

    def parse_list(self, response):
        pass
