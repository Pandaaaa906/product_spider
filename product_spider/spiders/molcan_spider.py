import re
from string import ascii_uppercase

from scrapy import Request


from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class MolcanPrdSpider(BaseSpider):
    name = 'molcan'
    base_url = 'http://molcan.com'
    start_urls = map(lambda x: f"http://molcan.com/product_categories/{x}", ascii_uppercase)
    pattern_cas = re.compile(r"\d+-\d{2}-\d(?!\d)")
    pattern_mw = re.compile(r'\d+\.\d+')
    pattern_mf = re.compile(r"(?P<tmf>(?P<mf>(?P<p>[A-Za-z]+\d+)+([A-Z]+[a-z])?)\.?(?P=mf)?)")

    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'CONCURRENT_REQUESTS_PER_IP': 8,
    }

    def parse(self, response):
        urls = response.xpath('//ul[@class="categories"]/li/a/@href').extract()
        api_names = response.xpath('//ul[@class="categories"]/li/a/text()').extract()
        for url, api_name in zip(urls, api_names):
            url = url.replace("..", self.base_url)
            yield Request(url, headers=self.headers, meta={'api_name': api_name}, callback=self.parent_parse)

    def parent_parse(self, response):
        detail_urls = response.xpath('//div[@class="product_wrapper"]//a[@class="readmore"]/@href').extract()
        for detail_url in detail_urls:
            url = detail_url.replace("..", self.base_url)
            yield Request(url, headers=self.headers, meta=response.meta, callback=self.detail_parse)

    def detail_parse(self, response):
        info = " ".join(response.xpath('//div[@id="description"]/*/text()').extract())
        l = self.pattern_mf.findall(info)
        if l:
            mf = "".join(map(lambda x: x[0], l))
        else:
            mf = ""
        relate_img_url = response.xpath('//a[@class="product_image lightbox"]/img/@src').get()
        d = {
            'brand': "molcan",
            'en_name': response.xpath('//p[@class="product_name"]/text()').get().split(' ; ')[0],
            'cat_no': response.xpath('//span[@class="productNo"]/text()').get().split('-')[0],
            'img_url': relate_img_url and self.base_url + relate_img_url,
            'cas': ' '.join(self.pattern_cas.findall(info)),
            'mw': ' '.join(self.pattern_mw.findall(info)),
            'mf': mf,
            'prd_url': response.request.url,
            'info1': "".join(response.xpath('//div[@id="description"]/descendant::*/text()').extract()),
            'parent': response.meta.get('api_name'),
        }
        yield RawData(**d)


