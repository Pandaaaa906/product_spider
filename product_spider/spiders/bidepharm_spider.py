import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class BidepharmSpider(BaseSpider):
    name = "bidepharm"
    start_urls = ["https://www.bidepharm.com/", ]
    base_url = "https://www.bidepharm.com/"

    def parse(self, response):
        rel_urls = response.xpath('//a[text()="更多+"]/@href').getall()

        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_cat_list)

    def parse_cat_list(self, response):
        a_nodes = response.xpath('//ul[@class="float-L"]/li/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            parent = first(re.findall(r'(\w+)\(', parent), parent)
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        parent = response.meta.get('parent')
        rel_urls = response.xpath('//div[@class="border-B product-name"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//div[@class="page"]/a[./i[@class="iconfont icon-gengduo"]]/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td//text()'
        cat_no = response.xpath('//input[@id="catNum"]/@value').get()
        if not cat_no:
            return

        d = {
            'brand': '毕得',
            'parent': response.meta.get('parent'),
            'cat_no': cat_no,
            'en_name': response.xpath('//span[@class="sp_pro_name_en"]/text()').get(),
            'chs_name': response.xpath('//span[@class="sp_pro_name_cn"]/text()').get(),
            'cas': response.xpath(tmp.format("CAS号：")).get(),
            'mf': ''.join(response.xpath(tmp.format("分子式：")).getall()),
            'mw': response.xpath(tmp.format("分子量：")).get(),

            'purity': response.xpath('//span[@id="first_purity"]/text()').get(),
            'info2': response.xpath('//span[contains(text(), "存储:")]/text()').get(),

            'img_url': response.xpath('//div[@class="products-big-img img-box position-R"]/img/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
