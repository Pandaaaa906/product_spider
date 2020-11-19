from time import time
from urllib.parse import urljoin, urlencode

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.maketrans import formular_trans
from product_spider.utils.spider_mixin import BaseSpider


class ClearsynthSpider(BaseSpider):
    name = "clearsynth"
    base_url = "https://www.clearsynth.com/en/"
    start_urls = ["https://www.clearsynth.com/en/", ]

    def parse(self, response):
        categories = response.xpath('//ul[@class="menu"]//a/text()').extract()
        for category in categories:
            params = {
                "search": category,
                "Therapeutic": "",
                "api": "",
                "industry": "",
                "category": "",
                "t": "",
                "limit": 20,
                "start": 1,
                "_": int(time() * 1000),
            }
            url = "https://www.clearsynth.com/en/fetch.asp?" + urlencode(params)
            yield Request(url, callback=self.list_parse, meta={'params': params})

    def list_parse(self, response):
        rel_urls = response.xpath('//div[@class="product-image"]//a/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(response.request.url, rel_url), callback=self.detail_parse)
        if rel_urls:
            params = response.meta.get('params')
            params["start"] = params["start"] + params["limit"]
            url = "https://www.clearsynth.com/en/fetch.asp?" + urlencode(params)
            yield Request(url, callback=self.list_parse, meta={'params': params})

    def detail_parse(self, response):
        tmp = 'normalize-space(//td[contains(text(),{!r})]/following-sibling::td//text())'
        tmp2 = '//strong[contains(text(), {!r})]/../following-sibling::td/text()'
        parent = response.xpath(tmp.format("Parent API")).get()
        category = response.xpath(tmp.format("Category")).get()
        img_rel_url = response.xpath('//div[@class="product-media"]//img/@src').get()
        d = {
            "brand": "Clearsynth",
            "parent": parent or category,
            "cat_no": response.xpath(tmp.format("CAT No.")).get(),
            "en_name": ''.join(response.xpath('//div[@class="product-name"]//text()').getall()),
            "cas": response.xpath(tmp.format("CAS")).get(),
            "mf": formular_trans(strip("".join(
                response.xpath("//td[contains(text(),'Mol. Formula')]/following-sibling::td//text()").extract()))),

            "mw": response.xpath(tmp.format("Mol. Weight")).get(),
            "img_url": img_rel_url and urljoin(response.request.url, img_rel_url),
            "info1": strip(response.xpath(tmp2.format('Synonyms')).get()),
            "info2": strip(response.xpath(tmp2.format("Storage Conditions")).get()),
            "smiles": strip(response.xpath(tmp2.format("Smiles")).get()),
            "prd_url": response.request.url,
            "stock_info": strip(response.xpath(tmp2.format("Stock Status")).get()),
        }
        yield RawData(**d)
