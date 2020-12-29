from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


# Blocked by captcha
class MacklinSpider(BaseSpider):
    name = "macklin"
    brand = "麦克林"
    start_urls = ["http://www.macklin.cn/products", ]
    base_url = "http://www.macklin.cn/"

    custom_settings = {
        'CONCURRENT_REQUESTS': '1',
        'DOWNLOAD_DELAY': 2,
    }

    def parse(self, response):
        a_nodes = response.xpath('//div[@class="list"]//a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            url = a.xpath('./@href').get()
            yield Request(url, callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        a_nodes = response.xpath('//td[1]/a')
        parent = response.meta.get('parent')
        for a in a_nodes:
            url = a.xpath('./@href').get()
            cat_no = a.xpath('./text()').get()
            yield Request(url, callback=self.parse_detail, meta={'parent': parent, 'cat_no': cat_no})

    def parse_detail(self, response):
        tmp = '//th[contains(text(), {!r})]/following-sibling::td//text()'
        cat_no = response.meta.get('cat_no')
        parent = response.meta.get('parent')
        d = {
            'brand': self.brand,
            'parent': parent,
            'cat_no': cat_no,
            'en_name': strip(response.xpath('//div[@class="product-general"]/span/text()').get()),
            'chs_name': strip(response.xpath(tmp.format("别名:")).get()) or response.xpath('//h1/text()').get(),
            'cas': strip(response.xpath(tmp.format("Cas号:")).get()),
            'mf': strip(''.join(response.xpath(tmp.format("分子式:")).getall())),
            'mw': strip(response.xpath(tmp.format("分子量:")).get()),
            'einecs': strip(response.xpath(tmp.format("EINECS编号:")).get()),
            'mdl': strip(response.xpath(tmp.format("MDL号:")).get()),
            'info2': strip(response.xpath(tmp.format("储存条件:")).get()),
            'appearance': strip(response.xpath(tmp.format("颜色:")).get()),

            'img_url': response.xpath('//td/img/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)

        rows = response.xpath('//div[@class="shopping"]//tbody/tr')
        for row in rows:
            cat_no_unit = strip(row.xpath('./td[1]/text()').get())
            package = cat_no_unit.replace(f'{cat_no}-', '')
            if package == 'bulk':
                return
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': package,
                'cat_no_unit': cat_no_unit,
                'price': strip(row.xpath('./td[5]/text()').get()),
                'currency': 'RMB',
            }
            yield ProductPackage(**dd)
