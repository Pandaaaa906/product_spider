from string import ascii_uppercase
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class SynPharmatechSpider(BaseSpider):
    name = "syn_prds"
    base_url = "http://www.synpharmatech.com"
    start_urls = (f'http://www.synpharmatech.com/products/search.asp?type=sign&twd={char}' for char in
                  ascii_uppercase)

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="submit"]/a[@id="submit3"]/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.detail_parse)

        next_href = response.xpath('//div[@class="fy"]/a[contains(text(), "Next >")]/@href').get()
        if next_href and next_href != "javascript:;":
            yield Request(next_href, callback=self.parse)

    def detail_parse(self, response):
        tmp = 'normalize-space(//div[@class="product1_l"]//span[contains(text(), "{}")]/../text())'
        rel_img = response.xpath('//div[@class="product1"]/img/@src').get()
        d = {
            "brand": "SynPharmaTech",
            "cat_no": strip(response.xpath(tmp.format("Cat. No")).get()),
            "en_name": strip(response.xpath('//div[@class="product1_l"]//h1/text()').get()),
            "info1": strip(response.xpath(tmp.format("Synonyms")).get()),
            "cas": strip(response.xpath(tmp.format("CAS No")).get()),
            "mf": strip(response.xpath(tmp.format("Formula")).get()),
            "mw": strip(response.xpath(tmp.format("F.W")).get()),
            "purity": strip(response.xpath(tmp.format("Purity")).get()),
            "stock_info": strip(response.xpath(
                'normalize-space(//div[@class="product2"]//tr[position()>1]/td[4]/text())').get()) or None,
            "prd_url": response.url,
            "img_url": urljoin(self.base_url, rel_img) if rel_img else None,
        }
        yield RawData(**d)

