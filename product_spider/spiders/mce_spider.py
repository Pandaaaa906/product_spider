from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.functions import strip
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class MCESpider(BaseSpider):
    name = "mce"
    brand = 'mce'
    base_url = "https://www.medchemexpress.cn/"
    start_urls = ['https://www.medchemexpress.cn/products.html', ]

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//td/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

        a_nodes = response.xpath('//div[@class="ctg_tit" and not(following-sibling::div[@class="ctg_con"])]/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        rel_urls = response.xpath('//th[@class="t_pro_list_name"]/a/@href').getall()
        parent = response.meta.get('parent')
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//link[@rel="next"]/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//th[contains(text(), {!r})]/following-sibling::td//p//text()'
        package = '//tr[td and td[@class="pro_price_3"]/span[not(@class)]]/td[@class="pro_price_1"]'
        rel_img = response.xpath('//div[@class="struct-img-wrapper"]/img/@src').get()
        cat_no = response.xpath('//dt/span/text()').get('').replace('Cat. No.: ', '').replace('目录号: ', '')
        tmp_package = strip(response.xpath(f'normalize-space({package}/text())').get())
        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': cat_no,
            'en_name': response.xpath('//h1/strong/text()').get(),

            'cas': strip(response.xpath(tmp.format("CAS No.")).get()),
            'mf': formula_trans(strip(response.xpath(tmp.format("Formula")).get())),
            'mw': strip(response.xpath(tmp.format("Molecular Weight")).get()),
            'smiles': strip(''.join(response.xpath(tmp.format("SMILES")).getall())),

            'info3': tmp_package and tmp_package.replace('\xa0', ' '),
            'info4': strip(response.xpath(f'{package}/following-sibling::td[1]/text()').get()),

            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }
        yield RawData(**d)
        if not cat_no:
            return
        rows = response.xpath('//tr[td and td[@class="pro_price_3"]/span[not(@class)]]')
        for row in rows:
            price = strip(row.xpath('./td[@class="pro_price_2"]/text()').get())
            tmp_package = strip(row.xpath('normalize-space(./td[@class="pro_price_1"]/text())').get())
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': tmp_package and tmp_package.replace('\xa0', ' '),
                'cost': price and price.strip('￥'),
                'delivery_time': strip(''.join(row.xpath('./td[@class="pro_price_3"]/span//text()').getall())) or None,
                'currency': 'RMB',
            }

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "parent": d["parent"],
                "en_name": d["en_name"],
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
            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)
