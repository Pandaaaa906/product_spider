from urllib.parse import urljoin
from scrapy import Request
from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class AnantSpider(BaseSpider):
    name = "anant"
    allowd_domains = ["anantlabs.com"]
    start_urls = ["https://anantlabs.com/categories.php"]
    base_url = "https://anantlabs.com/"
    custom_settings = {
        'CONCURRENT_REQUESTS': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 3,
        'CONCURRENT_REQUESTS_PER_IP': 3,
    }

    def parse(self, response, **kwargs):
        nodes = response.xpath("//div[@class='col-md-12'][position()=1]//a")
        for node in nodes:
            yield Request(
                url=node.xpath('./@href').get(),
                callback=self.parse_v2,
            )

    def parse_v2(self, response, **kwargs):
        nodes = response.xpath("//div[@class='col-md-12'][position()=2]//a")
        for node in nodes:
            yield Request(
                url=urljoin(self.base_url, node.xpath('./@href').get()),
                callback=self.parse_list,
            )

    def parse_list(self, response):
        nodes = response.xpath("//a[contains(text(), 'View Details')]")
        for node in nodes:
            url = node.xpath("./@href").get()
            yield Request(
                url=url,
                callback=self.parse_detail,
            )

    def parse_detail(self, response):
        parent = response.xpath("//div[@class='breadcrumbs']/a[last()]/text()").get()
        cat_no = response.xpath("//th[contains(text(), 'CAT No. :')]/following-sibling::td/text()").get()
        mf = response.xpath("//th[contains(text(), 'Mol. formula : ')]/following-sibling::td/text()").get()
        mw = response.xpath("//th[contains(text(), 'Mol. Weight : ')]/following-sibling::td/text()").get()
        en_name = response.xpath("//div[@class='breadcrumbs']/span[last()]/text()").get()
        cas = response.xpath("//th[contains(text(), 'CAS No. : ')]/following-sibling::td/text()").get()
        img_url = response.xpath("//div[@class='item']/img/@src").get()
        info1 = response.xpath("//th[contains(text(), 'Synonym : ')]/following-sibling::td/text()").get()
        stock_info = response.xpath(
            "//th[contains(text(), 'Inventory Status : ')]/following-sibling::td//b/text()").get()

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": parent,
            "en_name": en_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "info1": info1,
            "stock_info": stock_info,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)

