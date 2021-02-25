from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class AcanthusSpider(BaseSpider):
    name = "acanthus"
    allowd_domains = ["acanthusresearch.com"]
    start_urls = ["http://acanthusresearch.com/products/", ]
    base_url = "http://www.acanthusresearch.com/"

    def parse(self, response):
        prd_urls = response.xpath('//ul[@class="products"]/li//div[@class="prod-detail"]//h2/a/@href').extract()
        for prd_url in prd_urls:
            yield Request(prd_url, callback=self.detail_parse)
        next_page_url = response.xpath('//a[@class="next page-numbers"]/@href').get()
        if next_page_url:
            yield Request(next_page_url, callback=self.parse)

    def detail_parse(self, response):
        tmp_xpath = '//span[@class="spec" and contains(text(), {0!r})]/following-sibling::span//text()'

        raw_mf = response.xpath(tmp_xpath.format("Molecular Formula")).extract()
        en_name = response.xpath('//h1[contains(@class, "product_title")]/text()').get(default="").strip()
        cas = response.xpath(tmp_xpath.format("CAS Number")).get(default="N/A").strip()
        d = {
            'brand': "acanthus",
            'cat_no': response.xpath(tmp_xpath.format("Product Number")).get("").strip(),
            'en_name': en_name,
            'prd_url': response.request.url,  # 产品详细连接
            'cas': cas == "NA" and "N/A" or cas,
            'mf': ''.join(raw_mf),
            'mw': None,
            'info1': response.xpath('//div[@class="tags"]/a/text()').get("").strip() or None,
            'stock_info': "".join(
                response.xpath('//div[@class="row"]//div[contains(@class, "stock-opt")]//text()').extract()).strip(),
            'parent': response.xpath(tmp_xpath.format("Parent Drug")).get("").strip(),
            'img_url': urljoin(self.base_url, response.xpath('//div[@class="row"]//img/@src').get()),
        }
        yield RawData(**d)

