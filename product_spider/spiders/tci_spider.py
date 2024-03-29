from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class TCISpider(BaseSpider):
    name = "tci"
    base_url = "https://www.tcichemicals.com"
    start_urls = ['https://www.tcichemicals.com/CN/zh/product/index', ]
    brand = 'tci'

    custom_settings = {
        'CONCURRENT_REQUESTS': '1',
    }

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//div[@class="section-inner"]//p[@class="mark"]/a/@href').getall()

        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_cat_list)

    def parse_cat_list(self, response):
        rel_urls = response.xpath('//div[@class="card-header"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.deep_parse_cat_list)

    def deep_parse_cat_list(self, response):
        rel_urls = response.xpath('//div[@class="card-header"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.deep_parse_cat_list_v2)

    def deep_parse_cat_list_v2(self, response):
        rel_urls = response.xpath('//div[@class="card-header"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        nodes = response.xpath("//div[@id = 'product-list-wrap']/div")
        for node in nodes:
            url = node.xpath(".//a/@href").get()
            yield Request(
                url=urljoin(response.url, url),
                callback=self.parse_detail
            )

    def parse_detail(self, response):
        tmp = '//span[@class={!r}]/text()'
        tmp2 = '//td[contains(text(), {!r})]/following-sibling::td/text()'
        cat_no = response.xpath(tmp.format("code productVal")).get()
        mw = strip(response.xpath(tmp2.format("分子式/分子量")).get())
        img_rel = response.xpath('//div[@data-attr]/@data-attr').get()
        d = {
            'brand': self.brand,
            'parent': '_'.join(response.xpath(
                '//div[@class="subCategory clearfix"][1]//span[@class="startPoint"]//a/text()').getall()),
            'cat_no': cat_no,
            'en_name': ''.join(response.xpath('//h1[@class="name"]//text()').getall()),
            'cas': response.xpath(tmp.format("cas productVal")).get(),
            'mf': ''.join(response.xpath('//span[@id="molecularFormula"]//text()').getall()).replace('_', ''),
            'mw': mw and mw.replace('=', ''),
            'purity': response.xpath(tmp2.format("纯度/分析方法")).get(),
            'appearance': response.xpath(tmp2.format("外观与形状")).get(),
            'info2': response.xpath(tmp2.format("储存温度")).get(),
            'mdl': response.xpath(tmp2.format("MDL编号")).get(),

            'img_url': img_rel and urljoin(self.base_url, img_rel),
            'prd_url': response.url,
        }
        yield RawData(**d)

        rows = response.xpath('//table[@id="PricingTable"]/tbody/tr')
        for row in rows:
            stock_num = strip(row.xpath('./td[3]/text()').get())
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': row.xpath('./td[1]/text()').get(),
                'delivery_time': '现货' if stock_num != '0' else None,
                'cost': strip(row.xpath('./td[2]/div/text()').get()),
                'stock_num': stock_num,
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
