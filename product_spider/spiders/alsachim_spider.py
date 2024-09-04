from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class AlsachimSpider(BaseSpider):
    name = "alsachim"
    start_urls = ["https://www.alsachim.com/en/33-products"]

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//a[text()="Details"]/@href').getall()
        for rel_url in rel_urls:
            yield Request(
                url=urljoin(response.url, rel_url),
                callback=self.parse_detail,
            )

        next_page = response.xpath('//a[@rel="next" and not(contains(@class, "disable"))]/@href').get()
        if next_page:
            yield Request(
                url=urljoin(response.url, next_page),
                callback=self.parse,
            )

    def parse_detail(self, response):
        tmpl = '//li[contains(strong/text(), {!r})]//text()[not(parent::strong)]'

        img_url = response.xpath('//a[@id="single_image"]/img/@src').get()
        cat_no = response.xpath(tmpl.format("Product number:")).get()
        if not cat_no:
            cat_no = response.xpath(tmpl.format("Produit number:")).get()
        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "en_name": ''.join(response.xpath('//h1//text()').getall()),
            "cas": response.xpath(tmpl.format("CAS number:")).get(),
            "mf": ''.join(response.xpath(tmpl.format("Molecular formula:")).getall()),
            "mw": ''.join(response.xpath(tmpl.format("Molecular weight:")).getall()),
            "purity": ''.join(response.xpath(tmpl.format("Min. purity:")).getall()),
            "info1": ''.join(response.xpath(tmpl.format("Synonyms:")).getall()),
            "img_url": urljoin(response.url, img_url) if img_url else None,
            "prd_url": response.url,
        }
        yield RawData(**d)

