from product_spider.utils.spider_mixin import BaseSpider


# TODO
class IsosciencesSpider(BaseSpider):
    name = "isosciences"
    base_url = "https://isosciences.com/"
    start_urls = ['https://isosciences.com/', ]

    def parse(self, response):
        pass
