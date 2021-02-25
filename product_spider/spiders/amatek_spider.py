from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class AmatekSpider(BaseSpider):
    name = "amatek"
    base_url = "http://www.amatekbio.com/cn/"
    start_urls = ["http://www.amatekbio.com/cn/product.html", ]
    brand = 'amatek'

    def parse(self, response):
        a_nodes = response.xpath('//div[@class="produtimg"]/following-sibling::ul/li/a')
        for a in a_nodes:
            rel_urls = a.xpath('./@href').get()
            parent = a.xpath('./text()').get()
            yield Request(urljoin(self.base_url, rel_urls), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        parent = response.meta.get('parent')
        prd_urls = response.xpath('//a[@class="view"]/@href').getall()
        for rel_url in prd_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//a[@class="oncalass"]/following-sibling::a[@class="cf"]/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//span[contains(text(), {!r})]/following-sibling::text()'
        cat_no = strip(response.xpath(tmp.format("产品编号：")).get())
        sub_brand = response.xpath(tmp.format("品牌：")).get('')
        rel_img = response.xpath('//div[@class="riliimg-aa"]/img/@src').get()
        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': cat_no,
            'en_name': strip(response.xpath('//div[@class="tit-aa"]/text()').get()),
            'chs_name': strip(response.xpath(tmp.format('中文名称：')).get()),
            'cas': strip(response.xpath(tmp.format('CAS No：')).get()),
            'mf': strip(response.xpath(tmp.format('分子式：')).get()),
            'mw': strip(response.xpath(tmp.format('分子量：')).get()),
            'purity': strip(response.xpath(tmp.format('纯度：')).get()),
            'mdl': strip(response.xpath(tmp.format('MDL号：')).get()),

            'img_url': rel_img and urljoin(self.base_url, rel_img),
            'prd_url': response.url,
        }
        if 'amatek' not in sub_brand.lower():
            print(f'{cat_no}, have weird brand')
            return
        yield RawData(**d)

        rows = response.xpath('//div[@class="tablpp"]//tr[position()>1]')
        for row in rows:
            price = row.xpath('./td[3]/text()').get()
            if price is None or 'Inquire' == price:
                continue
            stock_num = row.xpath('./td[2]/text()').get('')
            delivery_time = 'in-stock' if stock_num.isdigit() and int(stock_num) else None
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': row.xpath('./td[1]/text()').get(),
                'price': price,
                'currency': 'RMB',
                'delivery_time': delivery_time,
                'stock_num': stock_num,
            }
            yield ProductPackage(**dd)
