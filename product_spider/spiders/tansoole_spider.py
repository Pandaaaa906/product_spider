from random import random
from urllib.parse import urlsplit, parse_qsl, urlencode
from scrapy import Request

from product_spider.items import SupplierProduct
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider

query_template = {
    'gloabSearchVo.type': '4',
    'gloabSearchVo.listType': '1',
    'gloabSearchVo.sortField': 'cn_len',
    'gloabSearchVo.asc': 'true',
    'Pagelist': '1',
    'page.pageSize': '50',
}


class TansooleSpider(BaseSpider):
    name = "tansoole"
    allowd_domains = ["tansoole.com/"]
    base_url = "http://www.acanthusresearch.com/"

    def start_requests(self):
        brand = 'DR'
        yield Request(
            f'https://www.tansoole.com/search/search.htm?gloabSearchVo.queryString={brand}&t={random()}',
            meta={'brand': brand}
        )

    def parse(self, response):
        rows = response.xpath('//ul[@class="show-list show-list-con"]')
        for row in rows:
            d = {
                'platform': 'tansoole',
                'source_id': row.xpath('./li[1]/a/text()').get(),
                'vendor': 'tansoole',
                'brand': row.xpath('./li[4]/span/text()').get(),
                'vendor_origin': 'China',
                'vendor_type': 'trader',
                'cat_no': strip(''.join(row.xpath('./li[2]//text()').getall())),
                'chs_name': strip(row.xpath('./li[3]//a/text()').get()),
                'package': row.xpath('./li[5]/span/text()').get(),
                'cas': strip(row.xpath('./li[6]/span/text()').get()),
                'purity': strip(row.xpath('./li[7]/span/text()').get()),
                'info1': strip(row.xpath('./li[9]//text()').get()),
                'price': strip(row.xpath('./li[10]/span/span/text()').get()),
                'delivery': strip(''.join(row.xpath('./li[12]//text()').getall())),
            }
            yield SupplierProduct(**d)

        next_page = response.xpath('//input[@name="next" and not(@disabled)]')
        if not next_page:
            return
        query = dict(parse_qsl(urlsplit(response.url).query))
        next_page_d = query_template.copy()
        next_page_d.update(**query)
        next_page_d['page.currentPageNo'] = str(int(response.xpath('//input[@name="page.currentPageNo"]/@value').get()) +1)
        next_page_d['page.totalCount'] = response.xpath('//input[@name="page.totalCount"]/@value').get()
        base_url, *_ = response.url.split('?')
        yield Request(f'{base_url}?{urlencode(next_page_d)}')

