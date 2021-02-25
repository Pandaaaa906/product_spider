from string import ascii_uppercase
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
    start_urls = [f"http://anaxlab.com/DrugImpuritiesindex?Index={a}/" for a in ascii_uppercase]
    base_url = "http://anaxlab.com/"

    def parse(self, response):
        parents = response.xpath('//option[position()>1]/text()').getall()
        for parent in parents:
            url = f'http://anaxlab.com/parent-api/{parent.lower().replace(" ", "-")}'
            yield Request(url, callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        rel_urls = response.xpath('//h2[@class="title"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail, meta=response.meta)

    def parse_detail(self, response):
        tmp_cat_no = '//b[contains(text(), "Product Code")]/../following-sibling::li[1]/text()'
        tmp = '//b[contains(text(), {!r})]/../following-sibling::li[1]//span[@itemprop]/text()'
        rel_img = response.xpath('//img[@class="productDetailsImage"]/@src').get()
        d = {
            'brand': "anaxlab",
            'en_name': response.xpath('//h1[@class="title"]/text()').get(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': cus_strip(response.xpath(tmp_cat_no).get()),
            'cas': cus_strip(response.xpath(tmp.format('CAS Number')).get()),
            'mf': cus_strip(response.xpath(tmp.format('Molecular Formula')).get()),
            'mw': cus_strip(response.xpath(tmp.format('Molecular Weight')).get()),
            'smiles': response.xpath('//li[contains(text(), "Smile Code")]/following-sibling::li[1]/text()').get(),
            'info1': cus_strip(response.xpath(tmp.format('Synonyms')).get()),
            'parent': response.meta.get('parent'),
            'img_url': rel_img and urljoin(self.base_url, rel_img),
        }
        yield RawData(**d)
