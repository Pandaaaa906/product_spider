import json
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.functions import strip
from product_spider.utils.parsepackage import parse_package
from product_spider.utils.spider_mixin import BaseSpider


class AltaSpider(BaseSpider):
    """阿尔塔"""
    name = "alta"
    brand = 'alta'
    base_url = "http://www.altascientific.com/"
    start_urls = ['http://www.altascientific.com/', ]

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//li[position()<7]//li[not(ul)]/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        parent = response.meta.get('parent')
        rel_urls = response.xpath('//a[@class="linkall"]/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = 'normalize-space(//td[contains(div/text(), {!r})]/following-sibling::td/text())'
        rel_img = response.xpath('//div[@class="c_c_p"]//div/img/@src').get()
        cat_no = strip(response.xpath(tmp.format("产品号/Catalog#")).get())
        synonyms = strip(response.xpath(tmp.format("Synonyms：")).get())

        # 其他产品信息
        product_info = response.xpath("//table[@class='c_c_p_1']//tr[last()]//td[last()]//p[last()-1]/text()").get()
        # 其他产品信息图片
        product_info_img = response.xpath("//table[@class='c_c_p_1']//tr[last()]//td[last()]//p[last()]//@src").get()

        prd_attrs = json.dumps({
            "synonyms": synonyms,
            "product_info": product_info,
            "product_info_img": product_info_img,
        })

        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': cat_no,
            'en_name': strip(response.xpath(tmp.format("Product Name：")).get()),
            'chs_name': strip(response.xpath(tmp.format("产品名称：")).get()),
            'cas': strip(response.xpath(tmp.format("CAS#：")).get()),
            'mf': strip(response.xpath(tmp.format("分子式/Formula：")).get()),
            'mw': strip(response.xpath(tmp.format("分子量/MW：")).get()),
            'purity': strip(response.xpath(tmp.format("纯度/Purity (%)：")).get()),
            'info1': strip(response.xpath(tmp.format("Synonyms：")).get()),
            'info2': strip(response.xpath(tmp.format("储藏条件/Storage：")).get()),
            'appearance': strip(response.xpath(tmp.format("颜色/Color：")).get()),
            'shipping_info': strip(response.xpath(tmp.format("运输条件/Transportation：")).get()),
            'mdl': strip(response.xpath(tmp.format("MDL#：")).get()),
            "attrs": prd_attrs,
            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }
        for k in d:
            d[k] = d[k] if d[k] != 'NA' else None
        yield RawData(**d)
        rows = response.xpath('//table[@class="c_p_size"]//tr[td and td/text()!="NA"]')
        for row in rows:
            if (cost := row.xpath('./td[2]/text()').get()) == 'NA':
                cost = None
            package = parse_package(row.xpath('./td[1]/text()').get())
            delivery_time = row.xpath('./td[3]/text()').get()
            sub_brand = row.xpath("./td[4]/text()").get()

            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': package,
                'cost': cost,
                "delivery_time": delivery_time,
                'currency': 'RMB',
            }
            yield ProductPackage(**dd)

            if not sub_brand or sub_brand == "First Standard":
                ddd = {
                    "platform": self.brand,
                    "vendor": self.brand,
                    "brand": self.brand,
                    "parent": d["parent"],
                    "en_name": d["en_name"],
                    "cas": d["cas"],
                    "mf": d["mf"],
                    "mw": d["mw"],
                    'cat_no': d["cat_no"],
                    'package': dd['package'],
                    'cost': dd['cost'],
                    "currency": dd["currency"],
                    "stock_info": dd["delivery_time"],
                    "img_url": d["img_url"],
                    "prd_url": response.url,
                }
                yield SupplierProduct(**ddd)
