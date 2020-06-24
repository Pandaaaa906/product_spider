# TODO https://www.hpc-standards.com/
from product_spider.utils.spider_mixin import BaseSpider


class HPCSpider(BaseSpider):
    name = "hpc"
    base_url = "https://www.hpc-standards.com/"
    start_urls = ["https://www.hpc-standards.com/shop/", ]

    def parse(self, response):
        pass
