from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class VivanSpider(BaseSpider):
    name = "vivan"
    allowd_domains = ["vivanls.com/"]
    start_urls = ["https://vivanls.com/products/all/all/default"]
    base_url = "https://vivanls.com/"

    def parse(self, response):
        rel_urls = response.xpath('//h5/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(url=urljoin(self.base_url, rel_url), callback=self.parse_detail)
        next_page = response.xpath('//li[@aria-current]/following-sibling::li/a/@href').get()
        if next_page:
            yield Request(next_page, callback=self.parse)

    def parse_detail(self, response):
        tmp = '//h4[contains(text(), {!r})]/following-sibling::p/text()'
        rel_img = response.xpath('//div[contains(@class, "product-detail-image")]/figure/img/@src').get()
        sym = response.xpath('//ul[contains(@class, "synmlist")]/li/text()').getall()
        sym = filter(bool, map(str.strip, sym))
        d = {
            'brand': 'Vivan',
            'cat_no': response.xpath(tmp.format('Catalogue No.:')).get(),
            'en_name': response.xpath('//div[@class="product-detail"]//h2/text()').get(),
            'cas': response.xpath(tmp.format('CAS No. :')).get(),
            'mf': formula_trans(response.xpath(tmp.format('Mol. Formula :')).get()),
            'mw': response.xpath(tmp.format('Mol. Weight :')).get(),
            'img_url': rel_img and urljoin(self.base_url, rel_img),
            'info1': ';'.join(sym),
            'prd_url': response.url,
        }
        yield RawData(**d)
