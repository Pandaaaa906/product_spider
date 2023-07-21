from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class HuiChengChemSpider(BaseSpider):
    name = "huichengchem"
    start_urls = ["https://www.huichengchem.com/col.jsp?id=134"]
    allowed_domains = ["huichengchem.com"]

    def parse(self, response, **kwargs):
        prd_urls = response.xpath('//a[@target="_blank"]/@href').getall()
        for prd_url in prd_urls:
            yield Request(
                url=urljoin(response.url, prd_url),
                callback=self.parse_detail,

            )

        rel_urls = response.xpath('//td[@class="g_foldContainerContentCenter"]//a/@href').getall()
        for rel_url in rel_urls:
            yield Request(
                url=urljoin(response.url, rel_url),
                callback=self.parse,
            )

    def _parse_value(self, response, name):
        v = response.xpath('//*[contains(text(), {!r})]/text()'.format(name)).get()
        if not v:
            return
        return v.strip(name)

    def parse_detail(self, response):
        img_url = response.xpath('//td/img[not(@border)]/@src').get()
        cas = self._parse_value(response, "CAS号：")
        d = {
            "brand": self.name,
            "cat_no": strip(self._parse_value(response, "编号：")) or cas,
            "chs_name": ''.join(response.xpath('//strong[@class="proname"]//text()').getall()),
            "mf": ''.join(response.xpath('//td[contains(text(), "化学式")]/following-sibling::td//text()').getall()),
            "mw": ''.join(response.xpath('//td[contains(text(), "分子量")]/following-sibling::td//text()').getall()),
            "cas": cas,
            "prd_url": response.url,
            "img_url": img_url and urljoin(response.url, img_url),
        }
        yield RawData(**d)
