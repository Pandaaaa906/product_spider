import json
import re

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider

t = str.maketrans('', '', '[]')


class SyninnovaSpider(BaseSpider):
    name = "syninnova"
    base_url = "https://www.syninnova.com/"
    start_urls = ['https://www.syninnova.com/catalog', ]
    prds_url = 'https://www.syninnova.com/products_ajax.php?spoint={spoint}&pcid={pcid}'
    prd_url = 'https://www.syninnova.com/catalog/product/{cat_no}'

    def parse(self, response, **kwargs):
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
        rows = response.xpath(
            '//div[not(@style)]/table[@class="table table-condensed"]/tbody/tr'
        )
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
            'img_url': response.xpath('//div[@class="prodImage"]/img/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
        for row in rows:
            cost = row.xpath("./td[last()-3]/text()").get()
            stock_num = row.xpath("./td[last()-1]/text()").get()
            raw_package = row.xpath("./td[last()-4]/text()").get()
            if not raw_package:
                continue
            package = raw_package.lower()

            dd = {
                "brand": d["brand"],
                "cat_no": d["cat_no"],
                "package": package,
                "cost": cost,
                "stock_num": stock_num,
                "currency": "USD",
            }

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id": f'{self.name}_{d["cat_no"]}_{dd["package"]}',
                "parent": d["parent"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                "en_name": d["en_name"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
                "img_url": d["img_url"],
                "prd_url": d["prd_url"],
            }
            dddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id":  f'{self.name}_{d["cat_no"]}',
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'discount_price': dd['cost'],
                'price': dd['cost'],
                'currency': dd["currency"],
            }
            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)
            yield RawSupplierQuotation(**dddd)

