from product_spider.utils.spider_mixin import BaseSpider
from product_spider.items import RawData


class WellingtonSpider(BaseSpider):
    name = "wellington"
    start_urls = ["https://well-labs.com/products/productsearch/", ]
    base_url = "https://well-labs.com/"
    brand = 'wellington'

    def parse(self, response):
        rows = response.xpath('//table[@id="table"]/tbody/tr')
        for row in rows:
            d = {
                'brand': self.brand,
                'cat_no': row.xpath('./td[1]/text()').get(),
                'en_name': row.xpath('./td[3]/text()').get(),
                'cas': row.xpath('./td[2]/text()').get(),
            }
            yield RawData(**d)
