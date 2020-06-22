from string import ascii_lowercase

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.maketrans import formular_trans
from product_spider.utils.spider_mixin import BaseSpider


class AnantSpider(BaseSpider):
    name = "anant"
    allowd_domains = ["anantlabs.com"]
    start_urls = [f"http://anantlabs.com/{a}/" for a in ascii_lowercase]
    base_url = "http://anantlabs.com"
    custom_settings = {
        'CONCURRENT_REQUESTS': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 3,
        'CONCURRENT_REQUESTS_PER_IP': 3,
    }

    def parse(self, response):
        nodes = response.xpath('//div[@id="content"]//li/a')
        for node in nodes:
            url = node.xpath('./@href').get()
            if not url:
                continue
            parent = node.xpath('./text()').get('').strip() or None
            yield Request(url, callback=self.list_parse, meta={'parent': parent})

    def list_parse(self, response):
        urls = response.xpath('//div[contains(@class,"product")]/h5/a/@href').extract()
        for url in urls:
            yield Request(url, callback=self.detail_parse, meta=response.meta)

    def detail_parse(self, response):
        div = response.xpath('//div[contains(@class,"heading")]')
        tmp_xpath = './h6[contains(text(),"{0}")]/parent::*/following-sibling::*/h5/descendant-or-self::*/text()'
        tmp_xpath_2 = './h6[contains(text(),"{0}")]/parent::*/following-sibling::*/h5/text()'
        # TODO untested
        mf = ''.join(div.xpath(tmp_xpath.format("Molecular Formula")).extract()).strip()
        d = {
            'brand': "Anant",
            'en_name': response.xpath('normalize-space(//div[contains(@class,"prod-details")]//h1/text())').get(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': response.xpath('//h5[@class="prod-cat"]/text()').get("").strip(),
            'cas': div.xpath(tmp_xpath_2.format("CAS")).get("").strip(),
            'stock_info': div.xpath(tmp_xpath_2.format("Stock Status")).get("").strip(),
            'mf': formular_trans(mf),
            'mw': div.xpath(tmp_xpath_2.format("Molecular Weight")).get("").strip(),
            'info1': response.xpath('//b[contains(text(),"Synonyms : ")]/following-sibling::text()').get("").strip(),
            'parent': response.meta.get('parent'),
            'img_url': response.xpath('//div[contains(@class,"entry-thumb")]/a/img/@src').get(),
        }
        yield RawData(**d)

