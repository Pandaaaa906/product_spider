import re
from urllib.parse import urljoin

from scrapy import Request
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.items import RawData


class FluorochemSpider(BaseSpider):
    name = "fluorochem"
    start_urls = ["http://www.fluorochem.co.uk/", ]
    base_url = "http://www.fluorochem.co.uk/"
    brand = 'fluorochem'

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//ul[@class="sub-menu"]/li[not(ul)]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), self.parse_list)

    def parse_list(self, response):
        rows = response.xpath('//div[@class="product-tile-inner"]')
        tmpl = './/span[text()={!r}]/following-sibling::span/text()'
        for row in rows:
            raw_img = row.xpath('./div[@class="img"]/@style').get()
            img_url = (m := re.search(r'(?<=url\()([^)]+)', raw_img)) and m.group()
            d = {
                "brand": self.name,
                "parent": row.xpath('.//li[@class="full"]/span/text()').get(),
                "cat_no": row.xpath(tmpl.format("Product Code")).get(),
                "en_name": row.xpath(tmpl.format("Product Name")).get(),
                "cas": row.xpath(tmpl.format("CAS")).get(),
                "purity": row.xpath(tmpl.format("Purity")).get(),
                "img_url": img_url,
            }
            yield RawData(**d)
