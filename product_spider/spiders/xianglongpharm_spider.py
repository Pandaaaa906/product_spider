from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class XianglongpharmSpider(BaseSpider):
    name = "xianglongpharm"
    brand = "xianglongpharm"
    start_urls = ['https://www.xianglongpharm.com/index.php/Index/products?id=1&flag=2',
                  'https://www.xianglongpharm.com/index.php/Index/products?id=2&flag=2']
    base_url = "https://www.xianglongpharm.com"

    def parse(self, response, **kwargs):
        api_nodes = response.xpath("//div[@class='col-md-4']/a")
        for api in api_nodes:
            url = urljoin(self.base_url, api.xpath('./@href').get(""))
            parent = strip(api.xpath('./text()').get())
            yield Request(url, callback=self.parse_list, meta={"parent": parent})
        next_url = response.xpath("//a[text()='下一页']/@href").get()
        if next_url:
            yield Request(urljoin(self.base_url, next_url), callback=self.parse)

    def parse_list(self, response):
        rows = response.xpath("//tbody//tr")
        parent = response.meta.get('parent')
        for row in rows:
            yield RawData(**self.parse_row(row, parent))
        next_url = response.xpath("//a[text()='下一页']/@href").get()
        if next_url:
            yield Request(urljoin(self.base_url, next_url), callback=self.parse_list)

    def parse_row(self, row, parent) -> dict:
        tds = row.xpath('./td')
        return {
            'brand': self.brand,
            "parent": parent,
            "cat_no": tds[0].xpath('./text()').get(),
            "cas": tds[5].xpath('./text()').get(),
            'chs_name': tds[2].xpath('./text()').get(),
            "en_name": tds[3].xpath('./text()').get(),
            "img_url": urljoin(self.base_url, tds[1].xpath('.//a/@href').get('')),
            "mf": tds[6].xpath('./text()').get(),
            'mw': tds[7].xpath('./text()').get(),
            "prd_url": urljoin(self.base_url, tds[-1].xpath('.//a/@href').get('')),
        }
