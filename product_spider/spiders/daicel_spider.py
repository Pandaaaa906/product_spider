from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class DaicelSpider(BaseSpider):
    name = "daicel"
    base_url = "http://www.daicelpharmastandards.com/"
    start_urls = ["http://www.daicelpharmastandards.com/products.php", ]

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="Catalogue"]/a/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse)

    def detail_parse(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td/text()'
        img_rel_url = response.xpath('//div[@class="modal-body"]/img/@src').get()
        d = {
            "brand": "Daicel",
            "parent": strip(response.xpath(tmp.format("API Name :")).get()),
            "cat_no": response.xpath('//div[@class="Catalogue"]/text()').get().split(': ')[-1],
            "en_name": response.xpath(tmp.format("Name of Compound :")).get(),
            "cas": strip(response.xpath('//b[text()="CAS number : "]/following-sibling::text()[1]').get()),
            "mf": strip(response.xpath('//b[text()="Mol. Formula : "]/following-sibling::text()[1]').get()),
            "mw": response.xpath(tmp.format("Molecular Weight :")).get(),
            "img_url": img_rel_url and urljoin(self.base_url, img_rel_url),
            "info1": strip(response.xpath(tmp.format('IUPAC Name :')).get()),
            "info2": strip(response.xpath(tmp.format('Storage Condition :')).get()),
            "appearance": strip(response.xpath(tmp.format('Appearance :')).get()),
            "prd_url": response.request.url,
            "stock_info": strip(response.xpath(tmp.format('Stock Status :')).get()),
        }
        yield RawData(**d)


