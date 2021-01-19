import json
from urllib.parse import urljoin

from scrapy import Request, FormRequest

from product_spider.items import RawData
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class SimsonSpider(BaseSpider):
    name = "simson"
    allowd_domains = ["simsonpharma.com"]
    base_url = "http://simsonpharma.com"

    def start_requests(self):
        url = "http://simsonpharma.com/category/products"
        for i in range(20):
            d = {
                "category_id": str(i),
                'stock_select': '0',
                'discount_select': '0',
                'price_select': '0',
                'sort_select': '0',
                "pageno": '1',
                "page_per_row": '99999',
            }
            yield FormRequest(url, formdata=d)

    def parse(self, response):
        try:
            j_objs = json.loads(response.text)
        except ValueError:
            return
        prds = j_objs.get("list", [])
        for prd in prds:
            tmp = prd.get("Page_Url")
            yield Request(urljoin(self.base_url, "/product/" + tmp), callback=self.detail_parse)

    @staticmethod
    def extract_value(response, title):
        ret = response.xpath(f'//td[text()={title!r}]/following-sibling::td/descendant-or-self::text()').extract()
        return ''.join(ret).strip() or None

    def detail_parse(self, response):
        img_url = response.xpath('//div[@class="product-img"]//img/@src').get()
        d = {
            "brand": "Simson",
            "en_name": response.xpath('//h1[contains(@class, "pro-title")]/text()').get(),
            "prd_url": response.url,
            "info1": self.extract_value(response, "Chemical Name"),
            "cat_no": self.extract_value(response, "Cat. No."),
            "cas": self.extract_value(response, "CAS. No."),
            "mf": formula_trans(self.extract_value(response, "Molecular Formula")),
            "mw": self.extract_value(response, "Formula Weight"),
            "img_url": img_url or urljoin(self.base_url, img_url),
            "info4": self.extract_value(response, "Category"),
            "stock_info": self.extract_value(response, "Product Stock Status"),
        }
        # TODO should have a middleware to warn this
        if d.get('en_name') is None or d.get('cat_no') is None:
            self.logger.warn(f'Get data loss from {response.url!r}')
        yield RawData(**d)
