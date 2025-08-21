from product_spider.spiders.tansoole_spider import TansooleSpider


class TansooleAdamasSpider(TansooleSpider):
    name = "tansoole_adamas"
    start_urls = [
        "https://www.tansoole.com/search/search.htm?gloabSearchVo.queryString=adamas",
    ]
