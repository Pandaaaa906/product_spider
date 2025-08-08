import json
import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request

from product_spider.items import HongmengItem, RawData, ProductPackage
from product_spider.utils.functions import strip, get_url
from product_spider.utils.spider_mixin import BaseSpider


class HongmengSpider(BaseSpider):
    name = "hongmeng"
    brand = '海岸鸿蒙'
    start_urls = ["http://www.bjhongmeng.com/shop/", ]
    base_url = "http://www.bjhongmeng.com/"

    def parse(self, response, **kwargs):
        rel_urls = response.xpath(
            '//ul[@class="dropdown-menu"]/li/a[contains(@href,"www.bjhongmeng.com/product/")]/@href').getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, callback=self.parse_list, )

    def parse_list(self, response):
        product_urls = response.xpath('//div[@class="product_list"]//tbody/tr/td[1]/a/@href').getall()
        parent = response.xpath("//ol[@class='breadcrumb']/li[@class='active']//text()").get()
        for url in set(product_urls):
            yield Request(urljoin(self.base_url, url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath("//li[@class='active']/following-sibling::li[1]/a/@href").get()
        if next_page:
            next_page = get_url(response.url, next_page)
            yield Request(next_page, callback=self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': response.xpath('//div[@class="pro_title"]/h3/text()').get(),
            'chs_name': response.xpath('//div[@class="pro_title"]/h1/text()').get(),
            'cas': response.xpath('//label[contains(text(),"CAS号")]/following-sibling::span[1]//text()').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)

        product_trs = response.xpath("//div[@class='table-responsive kj-table']/table/tbody/tr")

        headers = response.xpath("//div[@class='table-responsive kj-table']/table/thead//th/text()").getall()
        headers = [x.strip() for x in headers]
        property_map = {}
        for index, th in enumerate(headers):
            property_map[th] = index

        for tr in product_trs:
            tds = tr.xpath('./td')
            script_text = tr.xpath("./script/text()").get()
            try:
                package_info_match = re.search(r"=\s?\((.+?)\);", script_text)
                package_info_str: str = package_info_match.group(1)
                j_obj: dict = json.loads(package_info_str)
            except Exception as e:
                self.logger.warning(f'Parse pacakge info error, {response.url}')
                continue

            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": tds[property_map.get('规格')].xpath('.//text()').get(),
                'price': j_obj.get('Price'),
                'cost': j_obj.get('Price'),
                "currency": 'RMB',
                'purity': tds[property_map.get('浓度')].xpath('.//text()').get(),
                'stock_num': j_obj.get('AmountTotal'),
            }
            yield ProductPackage(**dd)

    def parse_price(self, response):
        t = first(re.findall(r'({.+});', response.text))
        if not t:
            return
        obj = json.loads(t)
        obj = json.loads(obj.get('ObjResult'))
        d = response.meta.get('product', {})

        if not obj.items():
            yield HongmengItem(**d)
            return

        _, prds = zip(*obj.items())
        for prd in prds:
            prd = first(prd)
            for inventory in prd.get('Inventores', []):
                goods_info = json.loads(inventory.get('Goods_Info', '{}')).get('goodsinfo', {})

                d_prd = {
                    'sub_cat_no': inventory.get('Goods_no'),
                    'place_code': inventory.get('Placecode'),
                    'amount': inventory.get('Amount'),
                    'package': goods_info.get('packaging'),
                    'sub_brand': goods_info.get('brand'),
                    'purity': goods_info.get('purity'),
                    'price': f"{inventory.get('MoneyUnit')} {inventory.get('Price')}"
                }
                d_prd.update(d)
                yield HongmengItem(**d_prd)
