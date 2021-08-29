from product_spider.items import RawData, ProductPackage
import scrapy
from product_spider.utils.spider_mixin import BaseSpider


class A2bchemSpider(BaseSpider):
    name = "a2bchem"
    allow_domain = ["a2bchem.com"]
    start_urls = ["https://www.a2bchem.com/Pharmaceutical-Intermediates.html", ]

    def parse(self, response, **kwargs):
        rows = response.xpath("//table[@class='q_table']/tbody/tr")
        for row in rows:
            url = row.xpath(".//td[7]//a/@href").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail
            )
        next_url = response.xpath("//li[@class='page-item']//a[@rel='next']/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse
            )

    def parse_detail(self, response):
        cat_no = response.xpath("//td[contains(text(), 'Catalog Number:')]/following-sibling::td/text()").get()
        d = {
            "brand": self.name,
            "parent": response.xpath("//div[@class='crumbs']//a[last()]/text()").get(),
            "cat_no": cat_no,
            "en_name": response.xpath("//td[contains(text(), 'Chemical Name:')]/following-sibling::td/text()").get(),
            "cas": response.xpath("//td[contains(text(), 'CAS Number:')]/following-sibling::td/text()").get(),
            "smiles": response.xpath("//td[contains(text(), 'SMILES:')]/following-sibling::td/text()").get(),
            "mf": response.xpath("//td[contains(text(), 'Molecular Formula:')]/following-sibling::td/text()").get(),
            "mw": response.xpath("//td[contains(text(), 'Molecular Weight:')]/following-sibling::td/text()").get(),
            "prd_url": response.url,
            "img_url": response.xpath("//div[@class='pd_f1']/img/@src").get(),
            "info1": response.xpath("//td[contains(text(), 'IUPAC Name:')]/following-sibling::td/text()").get(),
        }
        yield RawData(**d)

        rows = response.xpath("//table[@class='q_table']//tbody//tr[position()>0]")
        for row in rows:
            price = row.xpath(".//td[5]/text()").get()
            price = price.replace("$", '')
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": row.xpath(".//td[1]/text()").get(),
                "price": price,
                "currency": 'USD',

            }
            yield ProductPackage(**dd)
