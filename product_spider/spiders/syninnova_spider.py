import json
import re

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider

t = str.maketrans('', '', '[]')


class SyninnovaSpider(BaseSpider):
    name = "syninnova"
    base_url = "https://www.syninnova.com/"
    start_urls = ['https://www.syninnova.com/catalog', ]
    prds_url = 'https://www.syninnova.com/products_ajax.php?spoint={spoint}&pcid={pcid}'
    prd_url = 'https://www.syninnova.com/catalog/product/{cat_no}'

    def parse(self, response):
        a_nodes = response.xpath('//ul[@class="nav_menu"]/li/a')
        for a in a_nodes:
            category = a.xpath('./text()').get()
            url = a.xpath('./@href').get()
            if not url:
                continue
            yield Request(url, callback=self.parse_list, meta={'category': category})

    def parse_list(self, response):
        m = re.search(r'pcid=(\d+);', response.text)
        if not m:
            return
        pcid = int(m.group(1))
        spoint = 0
        url = self.prds_url.format(pcid=pcid, spoint=spoint)
        yield Request(url, callback=self.parse_json,
                      meta={'pcid': pcid, 'spoint': spoint, 'category': response.meta.get('category')}
                      )

    def parse_json(self, response):
        j_obj = json.loads(response.text)
        for row in j_obj:
            if isinstance(row, list):
                return
            cat_no = row.get('pid')
            if not cat_no:
                continue
            yield Request(self.prd_url.format(cat_no=cat_no), callback=self.parse_detail,
                          meta={'category': response.meta.get('category')}
                          )

        if len(j_obj) == 0:
            return
        pcid = response.meta.get('pcid')
        spoint = response.meta.get('spoint') + len(j_obj)
        yield Request(self.prds_url.format(spoint=spoint, pcid=pcid),
                      callback=self.parse_json,
                      meta={'pcid': pcid, 'spoint': spoint, 'category': response.meta.get('category')}
                      )

    def parse_detail(self, response):
        mf = strip(''.join(response.xpath('//label[text()="Mol. Formula : "]/..//text()[not(parent::label)]').getall()))
        row = response.xpath(
            '//div[not(@style)]/table[@class="table table-condensed"]/tbody/tr[position()=1 and position()!=last()]'
        )
        price = row.xpath('./td[2]/text()').get()
        cas = strip(response.xpath('//b[contains(text(), "CAS")]/../following-sibling::div/text()').get())
        d = {
            'brand': 'syninnova',
            'parent': response.meta.get('category'),
            'cat_no': response.xpath('//div[contains(@class, "productinfo")]/h2[1]/text()').get(),
            'en_name': response.xpath('//div[contains(@class, "productinfo")]/h2[2]/text()').get(),
            'cas': cas and cas.translate(t),
            'mf': mf,
            'mw': strip(response.xpath('//label[text()="Mol. Weight : "]/following-sibling::text()').get()),
            'appearance': strip(response.xpath('//label[text()="Appearance : "]/following-sibling::text()').get()),
            'info3': row.xpath('./td[1]/text()').get(),
            'info4': price and f'USD {price}',
            'stock_info': row.xpath('./td[4]/text()').get(),
            'img_url': response.xpath('//div[@class="prodImage"]/img/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
