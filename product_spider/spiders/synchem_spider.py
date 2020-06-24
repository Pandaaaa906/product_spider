from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class SynChemSpider(BaseSpider):
    name = "synchem"
    base_url = "https://www.synchem.de/"
    start_urls = ["https://www.synchem.de/shop/", ]

    def parse(self, response):
        urls = response.xpath('//h4[@class="entry-title"]/a/@href').extract()
        for url in urls:
            yield Request(url, callback=self.parse_detail)
        next_page = response.xpath('//a[@class="act"]/following-sibling::a[1]/@href').get()
        if next_page:
            yield Request(next_page, callback=self.parse)

    def parse_detail(self, response):
        d = {
            "brand": "SynChem",
            "parent": ';'.join(response.xpath('//td[@class="product_categories"]//a/text()').getall()),
            "cat_no": response.xpath('//td[@class="product_sku"]//text()').get(),
            "en_name": response.xpath('//h1[@class="product_title entry-title"]/text()').get(),
            "cas": response.xpath('//td[@class="td_value_CAS Number"]//text()').get(),
            "mf": "".join(response.xpath('//td[@class="td_value_Molecular Formula"]//text()').getall()),
            "mw": response.xpath('//td[@class="td_value_Molecular Weight"]//text()').get(),
            "img_url": response.xpath('//figure//a/@href').get(),
            "info1": str.strip(';'.join(response.xpath('//td[@class="td_value_Other Names"]//text()').getall())),
            # "info2": strip(response.xpath(tmp2.format("Storage Conditions")).get()),
            # "smiles": strip(response.xpath(tmp2.format("Smiles")).get()),
            "prd_url": response.request.url,
            "stock_info": str.strip(''.join(response.xpath('//p[@class="price"]//text()').getall())),
        }
        yield RawData(**d)
