import json
from urllib.parse import urljoin

from scrapy import Request, FormRequest

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider

def trans_brand(raw_brand):
    """转换诗丹德"""
    if raw_brand != "诗丹德":
        return raw_brand
    else:
        return "sdd"

def is_sdd(brand):
    if not brand or brand not in ["诗丹德"]:
        return False
    else:
        return True


class SddStoreSpider(BaseSpider):
    """诗丹德"""
    name = "sddstore"
    base_url = "http://www.sddstore.com/"
    prd_url = 'http://www.sddstore.com/web/item/info/getAll.do'
    other_brands = set()

    @staticmethod
    def make_form(page: int):
        return {
            'page': str(page),
            'limit': '12',
            'state': '1',
            'queryType': 'web',
        }

    def start_requests(self):
        page = 1
        d = self.make_form(page)
        yield FormRequest(self.prd_url, formdata=d, callback=self.parse)

    def parse(self, response, **kwargs):
        j_obj = json.loads(response.text)
        prds = j_obj.get('data', [])
        for prd in prds:
            prd_id = prd.get('id')
            if not prd_id:
                continue
            yield Request(f'http://www.sddstore.com/info/item/{prd_id}', callback=self.parse_detail)

        if prds:
            next_page = response.meta.get('page', 1) + 1
            f = self.make_form(next_page)
            yield FormRequest(self.prd_url, formdata=f, callback=self.parse, meta={'page': next_page})

    def parse_detail(self, response):
        tmp_xpath = '//div[contains(text(), {!r})]/following-sibling::div/text()'
        mf = strip(response.xpath(tmp_xpath.format("分子式")).get())
        mw = strip(response.xpath(tmp_xpath.format("分子量")).get())
        info1 = strip(response.xpath(tmp_xpath.format("英文异名")).get()),
        info2 = response.xpath('//td[contains(text(), "存储条件")]/following-sibling::td[1]/text()').get()
        appearance = response.xpath('//td[contains(text(), "性状")]/following-sibling::td[1]/text()').get()
        cas = strip(response.xpath(tmp_xpath.format("CAS NO.")).get())
        rel_img = response.xpath('//img[@class="pic"]/@src').get()

        rows = response.xpath('//th[contains(text(), "货号")]/parent::tr/following-sibling::tr')
        for row in rows:
            brand = trans_brand(row.xpath("./td[last()-6]/text()").get())
            chs_name = row.xpath("./td[last()-7]/text()").get()
            cat_no = row.xpath("./td[last()-8]/text()").get()
            purity = row.xpath("./td[last()-5]/text()").get()
            cost = parse_cost(row.xpath("./td[last()-4]/div/text()").get())
            package = row.xpath("./td[last()-3]/text()").get()
            stock_num = strip(row.xpath("./td[last()-2]/text()").get())

            d = {
                "brand": "sdd",
                "cat_no": cat_no,
                "chs_name": chs_name,
                "purity": purity,
                "mf": mf,
                "mw": mw,
                "cas": cas,
                "info1": info1,
                "info2": info2,
                "appearance": appearance,
                "img_url": rel_img and urljoin(self.base_url, rel_img),
                "prd_url": response.url,
            }
            dd = {
                "brand": d["brand"],
                "cat_no": cat_no,
                "package": package,
                "cost": cost,
                "stock_num": stock_num,
                "currency": "RMB",
            }

            ddd = {
                "source_id": f"{d['cat_no']}",
                "platform": "sdd",
                "vendor": "sdd",
                "brand": brand,
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
                "img_url": d["img_url"],
                "prd_url": d["prd_url"],
            }
            yield SupplierProduct(**ddd)
            if not is_sdd(brand):
                self.other_brands.add(brand)
                continue
            yield RawData(**d)
            yield ProductPackage(**dd)

    def closed(self, reason):
        self.logger.info(f'其他品牌: {self.other_brands}')
