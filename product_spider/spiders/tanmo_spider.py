from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class TanmoSpider(BaseSpider):
    name = "tanmo"
    base_url = "https://www.gbw-china.com/"
    start_urls = ["https://www.gbw-china.com/", ]

    def parse(self, response):
        a_nodes = response.xpath('//dd/a[contains(@href, "list_good")]')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            url = a.xpath('./@href').get()
            yield Request(url, callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        urls = response.xpath('//table[@id="product_table"]//td[1]//a/@href').getall()
        parent = response.meta.get('parent')
        for url in urls:
            yield Request(url, callback=self.parse_detail, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//el-form-item[contains(@label, {!r})]/span/text()'
        brand = strip(response.xpath(tmp.format("品牌")).get(), "")
        brand = '_'.join(('Tanmo', brand))
        cat_no = strip(response.xpath(tmp.format("产品编号")).get())
        d = {
            'brand': brand,
            'cat_no': cat_no,
            'chs_name': strip(response.xpath('//h2[@class="p-right-title"]/text()').get()),
            'cas': strip(response.xpath(tmp.format("CAS号")).get()),

            'stock_info': strip(response.xpath(tmp.format("库存")).get()),
            'expiry_date': strip(response.xpath(tmp.format("有效期")).get()),
            'purity': strip(response.xpath(tmp.format("标准值")).get()),

            'info2': strip(response.xpath(tmp.format("储存条件")).get()),
            'info3': strip(response.xpath(tmp.format("规格")).get()),
            'info4': strip(response.xpath('//span[@class="sell-price"]/text()').get()),

            'prd_url': response.url,
        }
        yield RawData(**d)

        dd = {
            'brand': brand,
            'cat_no': cat_no,
            'package': strip(response.xpath(tmp.format("规格")).get()),
            'price': strip(response.xpath('//span[@class="sell-price"]/text()').get()),
            'currency': 'RMB',
        }
        yield ProductPackage(**dd)
