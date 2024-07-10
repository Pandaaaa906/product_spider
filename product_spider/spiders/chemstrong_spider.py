from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class ChemstrongSpider(BaseSpider):
    name = "chemstrong"
    brand = "chemstrong"
    start_urls = ['https://www.qcsrm.com/index.php/Indexcn/products']
    base_url = "https://www.qcsrm.com"

    def parse(self, response, **kwargs):
        option_nodes = response.xpath("//select[@id='jumpMenu']/option")
        for option in option_nodes:
            url = urljoin(self.base_url, option.xpath('./@value').get(""))
            parent = strip(option.xpath('./text()').get())
            yield Request(url, callback=self.parse_list, meta={"parent": parent})

    def parse_list(self, response):
        detail_urls = response.xpath("//div[@class='col-md-4 pfont']//img/parent::*/@href").getall()
        for u in detail_urls:
            yield Request(url=urljoin(self.base_url, u), callback=self.parse_detail, meta=response.meta)

    def parse_detail(self, response):
        img_rel = response.xpath("//div[@class='example']//img/@src").get()
        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': response.xpath("//div[@class='col-md-4']/div/text()").get(),
            'chs_name': response.xpath("//div[@class='col-md-7 col-md-offset-1']/div/text()").get(),
            'en_name': response.xpath("//tr/td[contains(text(),'别名:')]/following-sibling::td[1]/text()").get(),
            'cas': response.xpath("//tr/td[contains(text(),'别名:')]/following-sibling::td[1]/text()").get(),
            'mf': response.xpath("//tr/td[contains(text(),'分子式')]/following-sibling::td[1]/text()").get(),
            'mw': response.xpath("//tr/td[contains(text(),'分子量')]/following-sibling::td[1]/text()").get(),
            'stock_info': response.xpath("//tr/td[contains(.//text(),'库存状态')]/following-sibling::td[1]//text()").get(),
            'img_url': img_rel and urljoin(self.base_url, img_rel),
            'prd_url': response.url,
        }
        yield RawData(**d)