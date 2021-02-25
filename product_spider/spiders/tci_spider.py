from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
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

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="section-inner"]//p[@class="mark"]/a/@href').getall()

        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_cat_list)

    def parse_cat_list(self, response):
        rel_urls = response.xpath('//div[@class="card-header"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_cat_list)

        rel_prds = response.xpath('//div[@class="text-concat"]/a/@href').getall()
        for rel_prd in rel_prds:
            yield Request(urljoin(response.url, rel_prd), callback=self.parse_detail)

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
            package = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': row.xpath('./td[1]/text()').get(),
                'delivery_time': '现货' if stock_num != '0' else None,
                'price': strip(row.xpath('./td[2]/div/text()').get()),
                'stock_num': stock_num,
                'currency': 'RMB',
            }
            yield ProductPackage(**package)

