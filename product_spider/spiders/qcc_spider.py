from string import ascii_uppercase
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class QCCSpider(BaseSpider):
    name = "qcc"
    start_urls = (f"http://www.qcchemical.com/index.php/Index/api?letter={c}&mletter={c}" for c in ascii_uppercase)
    base_url = "http://www.qcchemical.com/"

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//div[@id="pros"]/ul/a')
        for a in a_nodes:
            url = urljoin(self.base_url, a.xpath('./@href').get())
            parent = a.xpath('./li/text()').get()
            yield Request(url, callback=self.list_parse, meta={"parent": parent and parent.strip()})
        next_page = response.xpath('//a[text()=">"]/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse)

    def list_parse(self, response):
        rel_urls = response.xpath('//div[@id="list"]//a[contains(text(), "Details")]/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse, meta=response.meta)

    def detail_parse(self, response):
        tmp = '//td[contains(descendant-or-self::text(), "{}")]//following-sibling::td/text()'
        d = {
            "brand": "qcc",
            "parent": response.meta.get('parent'),
            "cat_no": response.xpath(tmp.format("QCC Cat No.:")).get(),
            "cas": strip(response.xpath(tmp.format("CAS No.:")).get()),
            "en_name": strip(response.xpath(tmp.format("Chemical Name:")).get()),
            "info1": strip(response.xpath(tmp.format("Synonyms:")).get()),
            "mf": strip(response.xpath(tmp.format("Molecular Formula:")).get()),
            "mw": strip(response.xpath(tmp.format("Molecular Weight:")).get()),
            "prd_url": response.url,
        }
        img_url = urljoin(self.base_url, response.xpath('//table//td/div[@style and not(div)]//img/@src').get())
        if img_url and not img_url.endswith('Uploads/'):
            d['img_url'] = img_url
        yield RawData(**d)

