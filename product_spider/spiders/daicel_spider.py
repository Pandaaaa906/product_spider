from urllib.parse import urljoin
from scrapy import Request
from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class DaicelSpider(BaseSpider):
    name = "daicel"
    base_url = "https://daicelpharmastandards.com/"
    base_url_v2 = "https://daicelpharmastandards.com/categories/"
    start_urls = ["https://daicelpharmastandards.com/zh/categories/", ]

    def parse(self, response, **kwargs):
        rows = response.xpath("//ul[@class='az-links']//li//a")
        for row in rows:
            yield Request(
                url=urljoin(self.base_url_v2, row.xpath("./@href").get()),
                callback=self.parse_v2
            )

    def parse_v2(self, response, **kwargs):
        rows = response.xpath("//div[@class='elementor-container elementor-column-gap-default dddd']/div")
        for row in rows:
            url = row.xpath(".//a/@href").get()
            yield Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        rows = response.xpath("//ul[@class='products columns-3']//li")
        for row in rows:
            yield Request(
                url=row.xpath("./a/@href").get(),
                callback=self.parse_detail
            )
        next_url = response.xpath("//ul[@class='page-numbers']/li[last()]/a/@href").get()
        if next_url:
            yield Request(
                url=urljoin(self.base_url, next_url),
                callback=self.parse_list
            )

    def parse_detail(self, response):
        parent = response.xpath("//nav[@class='woocommerce-breadcrumb']/a[last()]/text()").get()
        cat_no = response.xpath("//th[contains(text(), 'CAT Number')]/following-sibling::td/p/text()").get()
        en_name = response.xpath("//th[contains(text(), 'API Category')]/following-sibling::td/p/text()").get()
        cas = response.xpath("//th[contains(text(), 'CAS Number')]/following-sibling::td/p/text()").get()
        mf = response.xpath("//th[contains(text(), 'Molecular Formula')]/following-sibling::td/p/text()").get()
        mw = response.xpath("//th[contains(text(), 'Molecular Weight')]/following-sibling::td/p/text()").get()
        info1 = response.xpath("//th[contains(text(), 'IUPAC Name')]/following-sibling::td/p/text()").get()
        appearance = response.xpath("//th[contains(text(), 'Appearance')]/following-sibling::td/p/text()").get()
        info2 = response.xpath("//th[contains(text(), 'Storage Condition ')]/following-sibling::td/p/text()").get()
        img_url = response.xpath("//figure[@class='woocommerce-product-gallery__wrapper']//a/@href").get()

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": parent,
            "en_name": en_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "appearance": appearance,
            "info1": info1,
            "info2": info2,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)


