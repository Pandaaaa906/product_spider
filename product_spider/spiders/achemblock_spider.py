import scrapy
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.items import RawData


class AchemblockSpider(BaseSpider):
    name = "achemblock"
    allow_domain = ["achemblock.com"]
    start_urls = ["https://www.achemblock.com/products.html", ]

    def parse(self, response):  ##分类
        urls = response.xpath("//li[@class='level1 nav-1-1 first']/a/@href")
        for url in urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):  ##获取详情页url和next_url
        rows = response.xpath("//div[@class='products wrapper grid products-grid']//li")
        for row in rows:
            href = row.xpath(".//a/@href").get()
            yield scrapy.Request(
                url=href,
                callback=self.parse_detail
            )
        next_url = response.xpath("//li[@class='item pages-item-next']/a[@title='Next']/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        parent = response.xpath("//div[@class='breadcrumbs']//li[last()-1]/a/text()").get()
        en_name = response.xpath("//div[@class='breadcrumbs']//li[last()]/strong/text()").get()
        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": response.xpath(
                "//div[@class='product-info-custom']//span[contains(text(), 'Cat ID')]//following-sibling::span//text()").get(),
            "en_name": en_name,
            "cas": response.xpath(
                "//div[@class='product-info-custom']//span[contains(text(), 'CAS')]//following-sibling::span//text()").get(),
            "smiles": response.xpath(
                "//div[@class='product-info-custom']//span[contains(text(), 'Smiles')]//following-sibling::span//text()").get(),
            "mf": response.xpath(
                "//div[@class='product-info-custom']//span[contains(text(), 'Formula:')]//following-sibling::span//text()").get(),
            "mw": response.xpath(
                "//div[@class='product-info-custom']//span[contains(text(), 'FW:')]//following-sibling::span//text()").get(),
            "purity": response.xpath(
                "//div[@class='product-info-custom']//span[contains(text(), 'Purity:')]//following-sibling::span//text()").get(),
            "appearance": response.xpath(
                "//table[@class='data table additional-attributes']//th[contains(text(), 'Appearances')]//following-sibling::td//text()").get(),
            "img_url": response.xpath("//div[@class='gallery-placeholder _block-content-loading']/img/@src").get(),
            "prd_url": response.url,
            "info1": response.xpath(
                "//div[@class='product-info-custom']//span[contains(text(), 'IUPAC Name:')]//following-sibling::span//text()").get(),
            "info2": response.xpath(
                "//table[@class='data table additional-attributes']//th[contains(text(), 'Storage')]//following-sibling::td//text()").get(),
            "mdl": response.xpath(
                "//div[@class='product-info-custom']//span[contains(text(), 'MDL:')]//following-sibling::span//text()").get(),

        }
        yield RawData(**d)
