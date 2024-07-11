from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class XianglongpharmSpider(BaseSpider):
    name = "xianglongpharm"
    brand = "xianglongpharm"
    start_urls = [
        'https://www.xianglongpharm.com/index.php/Index/products?id=1&flag=2',
        'https://www.xianglongpharm.com/index.php/Index/products?id=2&flag=2',
    ]

    def parse(self, response, **kwargs):
        api_nodes = response.xpath("//div[@class='col-md-4']/a")
        for api in api_nodes:
            url = urljoin(response.url, api.xpath('./@href').get(""))
            parent = strip(api.xpath('./text()').get())
            yield Request(url, callback=self.parse_list, meta={"parent": parent})
        next_url = response.xpath("//a[text()='下一页']/@href").get()
        if next_url:
            yield Request(urljoin(response.url, next_url), callback=self.parse)

    def parse_list(self, response):
        rows = response.xpath("//tbody//tr")
        parent = response.meta.get('parent')
        for row in rows:
            img_url = row.xpath('./td[2]//img/@src').get()
            prd_url = row.xpath('./td[position()=last()]//a/@href').get()
            d = {
                'brand': self.brand,
                "parent": parent,
                "cat_no": row.xpath('./td[1]/text()').get(),
                "cas": row.xpath('./td[6]/text()').get(),
                'chs_name': row.xpath('./td[3]/text()').get(),
                "en_name": row.xpath('./td[4]/text()').get(),
                "img_url": img_url and urljoin(response.url, img_url),
                "mf": row.xpath('./td[7]/text()').get(),
                'mw': row.xpath('./td[8]/text()').get(),
                "prd_url": prd_url and urljoin(response.url, prd_url),
            }
            yield RawData(**d)
        next_url = response.xpath("//a[text()='下一页']/@href").get()
        if next_url:
            yield Request(urljoin(response.url, next_url), callback=self.parse_list)
