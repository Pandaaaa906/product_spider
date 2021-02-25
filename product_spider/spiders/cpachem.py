from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class CPAChemSpider(BaseSpider):
    name = "cpachem"
    start_urls = ["https://www.cpachem.com/shop/", ]
    base_url = "https://www.cpachem.com/"

    def parse(self, response):
        rel_urls = response.xpath('//ul[@id="cat0"]/li/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list)

    def parse_list(self, response):
        rel_urls = response.xpath('//div[@class="row shop_products"]/div[2]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail)

        next_page = response.xpath('//li[@class="active current"]/following-sibling::li[not(@class)]/a/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse_list)

    def parse_detail(self, response):
        tmp = '//b[text()={!r}]/following-sibling::text()'
        catagory = strip(response.xpath('//b[text()="Category:"]/following-sibling::a/text()').get())
        d = {
            'brand': 'cpachem',
            'parent': catagory,
            'cat_no': strip(response.xpath(tmp.format("Ref Num:")).get()),
            'en_name': strip(response.xpath(tmp.format("Full Name:")).get()),
            'info2': strip(response.xpath(tmp.format("Shelf Life on Ship Date:")).get()),
            'info3': strip(response.xpath(tmp.format("Vol.:")).get()),
            'info4': strip(response.xpath('//h3[contains(text(), "Price:")]/text()').get()).lstrip('Price: '),
            'stock_info': strip(response.xpath('//p[@style="padding:15px 0px 5px 0px;"]/text()').get()),
            'prd_url': response.url,
        }
        yield RawData(**d)
