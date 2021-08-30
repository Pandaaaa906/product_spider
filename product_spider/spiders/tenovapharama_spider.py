from urllib.parse import urljoin
from more_itertools import first
from scrapy import Request
from product_spider.items import RawData, ProductPackage
import re
from product_spider.utils.spider_mixin import BaseSpider


class TenovapharmalSpider(BaseSpider):
    name = "tenovapharma"
    allow_domain = ["tenovapharma.com"]
    start_urls = ["https://tenovapharma.com/collections/all/", ]
    base_url = "https://tenovapharma.com/collections/all"

    def parse(self, response, **kwargs):
        pro_list = response.xpath(
            '//a[@title="Products"]/following-sibling::ul//li[@role="menuitem"]/a[@title and not(following-sibling::ul)]')
        for pro in pro_list:
            url = pro.xpath("./@href").get()
            parent = pro.xpath("./@title").get()
            url = urljoin(response.url, url)
            yield Request(
                url=url,
                callback=self.parse_list,
                meta={'parent': parent}
            )

    def parse_list(self, response):
        parent = response.meta.get('parent')
        urls = response.xpath("//div[@class='relative']/a/@href").getall()
        for url in urls:
            url = urljoin(self.base_url, url)
            yield Request(
                url=url,
                callback=self.parse_detail,
                meta={'parent': parent}
            )

        next_url = response.xpath('//div[@class="pagination"]//a[@class="next"]/@href').get()
        if next_url:
            next_url = urljoin(self.base_url, next_url)
            yield Request(
                url=next_url,
                callback=self.parse,
                meta={'parent': parent}
            )

    def parse_detail(self, response):
        parent = response.meta.get('parent')
        cat_no = response.xpath("//span[@class='variant-sku']//text()").get()
        cat_no = first(re.findall(r'SKU:(.+)-', cat_no), None)
        d = {
            "brand": self.name,
            "parent": parent,
            "en_name": response.xpath("//h1[@class='product-header']/text()").get(),
            "cat_no": cat_no,
            "prd_url": response.url,
            "mf": response.xpath('//td[contains(text(), "Molecular Formula:")]/following-sibling::td/text()').get(),
            "mw": response.xpath('//td[contains(text(), "Molecular Weight:")]/following-sibling::td/text()').get(),
            "cas": response.xpath('//td[contains(text(), "CAS Number:")]/following-sibling::td/text()').get(),
            "smiles": response.xpath('//td[contains(text(), "SMILES:")]/following-sibling::td/text()').get(),
            "purity": response.xpath('//td[contains(text(), "Purity (HPLC):")]/following-sibling::td/text()').get(),
            "info1": response.xpath('//td[contains(text(), "Synonyms:")]/following-sibling::td/text()').get(),
            "info2": response.xpath('//td[contains(text(), "Storage Conditions:")]/following-sibling::td/text()').get(),
            "img_url": (m := response.xpath('//noscript/img/@src').get()) and urljoin(response.url, m),
        }
        yield RawData(**d)

        rows = response.xpath('//select[@id="product-select-product-template"]/option/text()').getall()
        for row in rows:
            package, price = row.split("-")
            price = price.replace("$", '')
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "currency": "USD",
                "price": price
            }
            yield ProductPackage(**dd)
