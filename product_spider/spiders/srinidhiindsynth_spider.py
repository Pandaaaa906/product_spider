from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


# TODO extract info from text
class SrinidhiindSynthSpider(BaseSpider):
    name = "srinidhiindsynth"
    allowd_domains = ["srinidhiindsynth.com/"]
    start_urls = ["http://srinidhiindsynth.com/products/"]
    base_url = "http://srinidhiindsynth.com/"

    def parse(self, response):
        a_nodes = response.xpath('//p/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            url = a.xpath('./@href').get()
            yield Request(url, callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        tables = response.xpath('//table')
        for table in tables:
            en_name = table.xpath('.//td[@class="info"]/h5[not(@class)]/strong//text()').get('')
            short_desc = table.xpath('normalize-space(.//td[@class="info"]/h5[@class="short_desc"]/strong//text())').get('')
            en_name = en_name.strip(' :')
            tmp = short_desc.split(';')
            tmp = map(str.strip, tmp)
            tmp = tuple(filter(bool, tmp))
            d = {
                'brand': 'SrinidhiindSynth',
                'cat_no': en_name,
                'en_name': en_name,
                'img_url': table.xpath('.//img/@src'),
            }
            # yield RawData(**d)
