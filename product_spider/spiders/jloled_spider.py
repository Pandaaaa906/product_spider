from product_spider.utils.spider_mixin import BaseSpider


class JLOledSpider(BaseSpider):
    name = "jl-oled"
    start_urls = [
        "https://www.ltom.com/products/1209885185940279296.html"
    ]