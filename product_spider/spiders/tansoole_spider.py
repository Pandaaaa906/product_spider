import re
from random import random
from urllib.parse import urlsplit, parse_qsl, urlencode, urljoin

import scrapy
from scrapy import Request

from product_spider.items import SupplierProduct
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider

query_template = {
    'gloabSearchVo.type': '4',
    'gloabSearchVo.listType': '1',
    'gloabSearchVo.sortField': 'cn_len',
    'gloabSearchVo.asc': 'true',
    'Pagelist': '1',
    'page.pageSize': '50',
}


class TansooleSpider(BaseSpider):
    name = "tansoole"
    allowd_domains = ["tansoole.com/"]
    base_url = "http://www.tansoole.com/"

    def start_requests(self):
        brand = 'DR'
        yield Request(
            f'https://www.tansoole.com/search/search.htm?gloabSearchVo.queryString={brand}&t={random()}',
            meta={'brand': brand}
        )

    def parse(self, response, **kwargs):
        rows = response.xpath('//ul[@class="show-list show-list-con"]')
        for row in rows:
            d = {
                'platform': 'tansoole',
                'source_id': row.xpath('./li[1]/a/text()').get(),
                'vendor': 'tansoole',
                'brand': row.xpath('./li[4]/span/text()').get(),
                'vendor_origin': 'China',
                'vendor_type': 'trader',
                'cat_no': strip(''.join(row.xpath('./li[2]//text()').getall())),
                'chs_name': strip(row.xpath('./li[3]//a/text()').get()),
                'package': row.xpath('./li[5]/span/text()').get(),
                'cas': strip(row.xpath('./li[6]/span/text()').get()),
                'purity': strip(row.xpath('./li[7]/span/text()').get()),
                'info1': strip(row.xpath('./li[8]//text()').get()),
                'price': strip(row.xpath('./li[9]/span/span/text()').get()),
                'delivery': strip(''.join(row.xpath('./li[11]//text()').getall())),
            }
            yield SupplierProduct(**d)

        next_page = response.xpath('//input[@name="next" and not(@disabled)]')
        if not next_page:
            return
        query = dict(parse_qsl(urlsplit(response.url).query))
        next_page_d = query_template.copy()
        next_page_d.update(**query)
        next_page_d['page.currentPageNo'] = str(
            int(response.xpath('//input[@name="page.currentPageNo"]/@value').get()) + 1)
        next_page_d['page.totalCount'] = response.xpath('//input[@name="page.totalCount"]/@value').get()
        base_url, *_ = response.url.split('?')
        yield Request(f'{base_url}?{urlencode(next_page_d)}')


class TansooleDreSpider(BaseSpider):
    name = "tansoole_dre"
    start_urls = ["https://www.tansoole.com/search/search.htm?gloabSearchVo.queryString=DRE"]
    base_url = "https://www.tansoole.com/"

    def parse(self, response, **kwargs):
        """dre价格在泰坦官网获取"""
        rows = response.xpath("//ul[@class='show-list show-list-head']/following-sibling::ul/li[position()=1]")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_package
            )
        # 获取下一页
        next_url = response.xpath("//input[@value='下页']/@onclick").get()
        if next_url is not None:
            next_page_number = re.search(r'(?<==)\d+(?=;)', next_url).group()
            yield scrapy.Request(
                url=f"https://www.tansoole.com/search/search.htm?gloabSearchVo.queryString=dre&gloabSearchVo.nav=1&t=0.10001398760159042&page.currentPageNo={next_page_number}",
                callback=self.parse
            )

    def parse_package(self, response):
        chs_name = response.xpath("//div[@class='title']/text()").get()
        cat_no = response.xpath("//div[contains(text(), '原始编号：')]/following-sibling::div/text()").get()
        source_id = response.xpath("//div[contains(text(), '探索编号：')]/following-sibling::div/text()").get()
        img_url = urljoin(self.base_url, response.xpath("//div[@id='big-box']/img/@src").get())
        package = response.xpath("//div[contains(text(), '包装规格：')]/following-sibling::div/text()").get('')
        if package is not None:
            package = ''.join(package.split())

        cost = response.xpath("//span[@id='bigDecimalFormatPriceDesc']/text()").get()
        delivery = ''.join(
            response.xpath("//div[contains(text(), '货期：')]/following-sibling::div/span/text()").get('').split())
        stock_info = response.xpath("//div[contains(text(), '库存：')]/following-sibling::div/span/text()").get()
        expiry_date = response.xpath("//div[contains(text(), '有效期至：')]/following-sibling::div/text()").get()

        dd = {
            "brand": "dre",
            "cat_no": cat_no,
            "prd_url": response.url,
            "platform": "tansoole",
            "source_id": source_id,
            "img_url": img_url,
            "cost": cost,
            "chs_name": chs_name,
            "delivery": delivery,
            "stock_info": stock_info,
            "expiry_date": expiry_date,
            "package": package,
            "currency": "RMB",
        }
        yield SupplierProduct(**dd)
