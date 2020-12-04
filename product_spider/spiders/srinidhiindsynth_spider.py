import re

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
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
            m_cas = re.search(r'\d+-\d{2}-\d', short_desc)
            m_mw = re.search(r'Mol\. Wt\.: ([^;]+);', short_desc)
            m_mf = re.search(r'CAS : [^;]+; ([^;]+)', short_desc)
            d = {
                'brand': 'SrinidhiindSynth',
                'parent': response.meta.get('parent'),
                'cat_no': en_name,
                'en_name': en_name,
                'cas': m_cas and m_cas.group(),
                'mf': m_mf and strip(m_mf.group(1)),
                'mw': m_mw and strip(m_mw.group(1)),
                'img_url': table.xpath('.//img/@src').get(),
                'prd_url': response.url,
            }
            # yield RawData(**d)
