from urllib.parse import urljoin

from scrapy import Request
import re
from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class WitegaSpider(BaseSpider):
    name = "witega"
    base_url = "https://auftragssynthese.com/"
    start_urls = ["https://auftragssynthese.com/en/nitrofuran-metabolites/", ]

    def parse(self, response, *args, **kwargs):
        rel_urls = response.xpath('//ul[@id="menu-kategorie"]//a/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.list_parse)

    def list_parse(self, response):
        rel_urls = response.xpath('//div[@class="the_excerpt"]/a/@href').extract()
        parent = re.search(r"(?<=https://auftragssynthese.com/en/).*(?=/)", response.url).group()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail, meta={"parent": parent})

    def parse_detail(self, response):
        parent = response.meta.get("parent", '')
        tmp = '//li[contains(@class, {!r})]/span[@class="attribute-value"]/text()'
        cat_no = response.xpath('//span[@class="sku"]/text()').get()
        d = {
            "brand": "witega",
            "cat_no": cat_no,
            "parent": parent,
            "en_name": ''.join(response.xpath('//div[@class="summary entry-summary"]/h2//text()').getall()),
            "cas": response.xpath(tmp.format("cas-number")).get(),
            'info1': ''.join(response.xpath('//h5//text()').getall()) or None,
            'prd_url': response.url,
            'img_url': response.xpath('//a/img/@data-src').get(),
        }
        yield RawData(**d)
        packages = response.xpath("//*[contains(text(), 'Offer')]/parent::span/following-sibling::span/text()").get()
        if packages is None:
            return
        packages = packages.replace(" ", '').split(',')
        for package in packages:
            dd = {
                "brand": "witega",
                "cat_no": cat_no,
                "package": package,
                "currency": "USD",
            }
            yield ProductPackage(**dd)
