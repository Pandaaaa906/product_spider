import json
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


def cus_strip(s):
    if s is None:
        return
    return s.strip(':').strip()


class AnaxlabSpider(BaseSpider):
    name = "anaxlab"
    allowd_domains = ["anaxlab.com"]
    start_urls = ["https://www.anaxlab.com/products"]
    base_url = "http://anaxlab.com/"

    def parse(self, response, **kwargs):
        rows = response.xpath("//div[@class='field-content']/a/@href").getall()
        for url in rows:
            yield Request(
                url=urljoin(self.base_url, url),
                callback=self.parse_list,
            )

    def parse_list(self, response):
        parent = response.xpath("//*[@class='title page-title']/text()").get()
        rows = response.xpath("//h6/a/@href").getall()
        for url in rows:
            yield Request(
                url=urljoin(self.base_url, url),
                callback=self.parse_detail,
                meta={"parent": parent},
            )
        next_url = response.xpath("//*[contains(text(), 'Next page')]/parent::a/@href").get()
        if next_url:
            yield Request(
                url=urljoin(response.url, next_url),
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        parent = response.meta.get("parent", None)
        tmp_xpath = "//*[contains(text(), {!r})]/parent::td/following-sibling::td/text()"

        prd_attrs = json.dumps({
            "synonyms": response.xpath(tmp_xpath.format("Synonyms")).get(),
        })

        d = {
            "brand": "anaxlab",
            "parent": parent,
            "en_name": response.xpath("//*[@class='title page-title']/span/text()").get(),
            "cat_no": response.xpath(tmp_xpath.format("Product Code")).get(),
            "cas": response.xpath(tmp_xpath.format("CAS Number")).get(),
            "mf": response.xpath(tmp_xpath.format("Molecular Formula")).get(),
            "mw": response.xpath(tmp_xpath.format("Molecular Weight")).get(),
            "purity": response.xpath(tmp_xpath.format("Purity")).get(),
            "mdl": response.xpath(tmp_xpath.format("MDL No.")).get(),
            "smiles": ''.join(response.xpath(tmp_xpath.format("Smile Code")).getall()),
            "attrs": prd_attrs,
            "prd_url": response.url,
            "img_url": urljoin(self.base_url, response.xpath("//*[@class='field__item']/img/@src").get())
        }
        yield RawData(**d)
