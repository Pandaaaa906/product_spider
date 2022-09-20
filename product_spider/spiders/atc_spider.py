from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import ATCIndex
from product_spider.utils.spider_mixin import BaseSpider


class ATCSpider(BaseSpider):
    name = 'atc'
    start_urls = ['https://www.whocc.no/atc_ddd_index/']

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//p/b/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(
                urljoin(response.url, rel_url),
                callback=self.parse,
            )
        rows = response.xpath('//ul/table//tr[position()>1]')
        for row in rows:
            d = {
                'atc_code': row.xpath('./td[1]/text()').get(),
                'drug_name': ''.join(row.xpath('./td[2]//text()').getall()),
                'ddd': row.xpath('./td[3]//text()').get(),
                'unit': row.xpath('./td[4]//text()').get(),
                'adm': row.xpath('./td[5]//text()').get(),
                'note': row.xpath('./td[6]//text()').get(),
                'url': response.url,
            }
            if not d['drug_name']:
                continue
            yield ATCIndex(**d)
