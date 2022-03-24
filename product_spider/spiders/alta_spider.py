from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class AltaSpider(BaseSpider):
    name = "alta"
    brand = '阿尔塔'
    base_url = "http://www.altascientific.com/"
    start_urls = ['http://www.altascientific.com/', ]

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//li[position()<7]//li[not(ul)]/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        parent = response.meta.get('parent')
        rel_urls = response.xpath('//a[@class="linkall"]/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = 'normalize-space(//td[contains(div/text(), {!r})]/following-sibling::td/text())'
        rel_img = response.xpath('//div[@class="c_c_p"]//div/img/@src').get()
        cat_no = strip(response.xpath(tmp.format("产品号/Catalog#")).get())
        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': cat_no,
            'en_name': strip(response.xpath(tmp.format("Product Name：")).get()),
            'chs_name': strip(response.xpath(tmp.format("产品名称：")).get()),
            'cas': strip(response.xpath(tmp.format("CAS#：")).get()),
            'mf': strip(response.xpath(tmp.format("分子式/Formula：")).get()),
            'mw': strip(response.xpath(tmp.format("分子量/MW：")).get()),
            'purity': strip(response.xpath(tmp.format("纯度/Purity (%)：")).get()),
            'info1': strip(response.xpath(tmp.format("Synonyms：")).get()),
            'info2': strip(response.xpath(tmp.format("储藏条件/Storage：")).get()),
            'appearance': strip(response.xpath(tmp.format("颜色/Color：")).get()),

            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }
        for k in d:
            d[k] = d[k] if d[k] != 'NA' else None
        yield RawData(**d)
        rows = response.xpath('//table[@class="c_p_size"]//tr[td and td/text()!="NA"]')
        for row in rows:
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': row.xpath('./td[1]/text()').get(),
                'cost': row.xpath('./td[2]/text()').get(),
                'currency': 'RMB',
            }
            yield ProductPackage(**dd)
