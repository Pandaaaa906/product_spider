from scrapy import Request
from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class AcintsSpider(BaseSpider):
    name = "acints"
    allowed_domains = ["acints.com"]
    start_urls = ["https://www.acints.com/products", ]

    def parse(self, response, **kwargs):
        urls = response.xpath("//ul[@class='productList']//p[position()>1]/a/@href").getall()
        for url in urls:
            if url:
                yield Request(
                    url=url,
                    callback=self.parse_detail
                )
        next_url = response.xpath("//div[@class='middle']//p[last()]//a[last()-1]/@href").get()

        if next_url:
            yield Request(
                next_url,
                callback=self.parse
            )

    def parse_detail(self, response):
        cat_no = response.xpath("//div[@id='primary']//span[contains(text(), 'Product Code:')]//parent::p/text()").get()

        d = {
            "brand": self.name,
            "en_name": response.xpath("//div[@id='primary']/h1/text()").get(),
            "cat_no": cat_no,
            "cas": response.xpath("//div[@id='primary']//span[contains(text(), 'CAS No:')]//parent::p/text()").get(),
            "mf": response.xpath("//span[@class='pParam'][contains(text(), 'Molecular Formula:')]/parent::p/text()").get(),
            "mw": response.xpath("//div[@id='primary']//span[contains(text(), 'Molecular Weight:')]//parent::p/text()").get(),
            "purity": response.xpath("//div[@id='primary']//span[contains(text(), 'Purity:')]//parent::p/text()").get(),
            "prd_url": response.url,
            "img_url": response.xpath("//div[@class='productImg']//img/@src").get(),
            "mdl": response.xpath("//div[@id='primary']//span[contains(text(), 'MDL No:')]//parent::p/text()").get()
        }

        yield RawData(**d)

        rows = response.xpath("//form[@class='cartform ajaxform']//p")
        for row in rows:
            price = row.xpath('//span[@class="baseprice"]/text()').get()
            price = price.replace("£", '')
            package = row.xpath("//label[@for='qty1']//span[@class='pParam']/text()").get()
            package = package.split(" ")[-1]

            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "cost": price,
                "currency": "GBP"  # Great Britain Pound
            }
            yield ProductPackage(**dd)
