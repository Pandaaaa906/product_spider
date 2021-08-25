from urllib.parse import urljoin

import scrapy
from scrapy.spiders import CrawlSpider

from product_spider.items import RawData, ProductPackage

class AaronchemSpider(CrawlSpider):
    name = "aaronchem"
    allow_domain = ["aaronchem.com"]
    start_urls = ["https://www.aaronchem.com/product.html?page=1", ]
    base_url = 'https://www.aaronchem.com/storage/structure'

    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }

    def parse(self, response):
        nodes = response.xpath('//ul[@class="ul2 "]/li/a')
        for a in nodes:
            parent = a.xpath('./text()').get()
            url = a.xpath('./@href').get()
            yield scrapy.Request(url, callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        parent = response.meta['parent']
        urls = response.xpath("//a[@class='view_detial']/@href").getall()
        for url in urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_detial,
                meta={"parent" : parent}
            )

        next_url = response.xpath('//div[@class="layui-box layui-laypage"]/a[@rel="next"]/@href').get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list,
                meta={"parent":parent}
            )

    def parse_detial(self, response):
        img_url = response.xpath("//div[@class='detail_img']/img/@src").get()

        cat_no = response.xpath("//td[contains(text(), 'Catalog Number')]/following-sibling::td/text()").get()
        d = {
            "brand" : self.name,
            "prd_url" : response.url,
            "en_name" : response.xpath("//div[@class='detail_des']/h2/text()").get(),
            "img_url" : urljoin(self.base_url, img_url),
            "cat_no" : cat_no,
            "mdl" : response.xpath("//td[contains(text(), 'MDL Number')]/following-sibling::td/text()").get(),
            "smiles" : response.xpath("//td[contains(text(), 'SMILES')]/following-sibling::td/text()").get(),
            "parent" : response.xpath("//td[contains(text(), 'Catalog Number')]/following-sibling::td/text()").get(),
            "info1" : response.xpath("//td[contains(text(), 'Chemical Name')]/following-sibling::td/text()").get(),
            "cas" : response.xpath("//td[contains(text(), 'CAS Number')]/following-sibling::td/text()").get(),
            "mf" : response.xpath("//td[contains(text(), 'Molecular Formula')]/following-sibling::td/text()").get(),
            "mw" : response.xpath("//td[contains(text(), 'Molecular Weight')]/following-sibling::td/text()").get(),
        }
        yield RawData(**d)

        rows = response.xpath("//div[@class='detail']//tr[position()>1]")
        for row in rows:
            price = row.xpath('./td[3]/text()').get()
            price = price.replace("$", '')
            dd = {
                "brand" : self.name,
                "cat_no" : cat_no,
                "package" : row.xpath('./td[1]/text()').get(),
                "currency" : "USD",
                "price" : price,
            }
            yield ProductPackage(**dd)