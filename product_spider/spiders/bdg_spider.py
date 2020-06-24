import re
from string import ascii_lowercase

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


p_cas = re.compile(r'\d+-\d{2}-\d\b')


class BDGSpider(BaseSpider):
    name = "bdg"
    base_url = "https://bdg.co.nz/"
    start_urls = [f"https://bdg.co.nz/product-category/{a}/" for a in ascii_lowercase]

    def parse(self, response):
        urls = response.xpath('//h4/a/@href').extract()
        for url in urls:
            yield Request(url, callback=self.parse_detail)
        next_page = response.xpath('//div[@class="pages"]/span/following-sibling::a[1]/@href').get()
        if next_page:
            yield Request(next_page, callback=self.parse)

    def parse_detail(self, response):
        r_cas = response.xpath('//strong[contains(text(),"CAS Number: ")]/text()').get()
        l_cas = p_cas.findall(r_cas)
        cas = None if not l_cas else first(l_cas)
        d = {
            "brand": "BDG",
            "parent": ';'.join(response.xpath('//span[@class="posted_in"]/a/text()').getall()) or None,
            "cat_no": response.xpath('//span[@class="sku"]/text()').get(),
            "en_name": response.xpath('//h1[@itemprop="name"]/text()').get(),
            "cas": cas,
            "mf": ''.join(response.xpath('//strong[text()="Molecular Formula"]/../following-sibling::td//text()').getall()),
            "mw": ''.join(response.xpath('//strong[text()="Molecular Weight"]/../following-sibling::td//text()').getall()),
            "img_url": response.xpath('//img[@class="wp-post-image"]/@src').get(),
            "prd_url": response.request.url,
        }
        yield RawData(**d)
