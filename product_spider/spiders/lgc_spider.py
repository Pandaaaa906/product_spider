import json
from urllib.parse import urlencode

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import JsonSpider


class LGCSpider(JsonSpider):
    name = "lgc"
    allowd_domains = ["lgcstandards.com"]
    start_urls = [
        "https://www.lgcstandards.com/lgccommercewebservices/v2/lgcstandards/categories/279492/products?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=&country=CN&lang=en",
    ]
    base_url = "https://www.lgcstandards.com/CN/en/"
    search_url = "https://www.lgcstandards.com/lgccommercewebservices/v2/lgcstandards/categories/279492/products?"

    def start_requests(self):
        url = "https://www.lgcstandards.com/lgccommercewebservices/v2/lgcstandards/categories/279492/products?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=&country=GB&lang=en"
        yield Request(url, callback=self.parse, headers=self.headers)

    def parse(self, response):
        obj = json.loads(response.text)
        pagination = obj.get('pagination', {})
        current_page = pagination.get('currentPage', 0)
        total_pages = pagination.get('totalPages', 0)
        per_page = pagination.get('pageSize', 0)

        if current_page < total_pages:
            data = {
                "currentPage": current_page + 1,
                "q": "",  # INFO hardcoding
                "sort": "relevance-code",
                "pageSize": per_page,
                "country": "GB",
                "lang": "en",
                "fields": "FULL",
                "defaultB2BUnit": "",
            }
            print(response.request.headers)
            yield Request(self.search_url + urlencode(data), callback=self.parse, headers=self.headers)

        products = obj.get('products', [])
        for product in products:
            url = product.get('url')
            yield Request(self.base_url + url, callback=self.detail_parse)

    def detail_parse(self, response):
        tmp = '//div[contains(@class,"product__item")]/h2[text()={!r}]/following-sibling::*/descendant-or-self::text()'
        cat_no = response.xpath(tmp.format("Product Code")).get('')
        if not cat_no.upper().startswith('MM'):
            return
        parents = response.xpath(
            '//div[contains(@class,"product page-section")]//div[contains(@class,"product__item")]/h2[contains(text(),"API Family")]/following-sibling::*/descendant-or-self::text()').extract()
        parent = "".join(parents)
        related_categories = response.xpath(
            '//ul[contains(@class,"breadcrumb")]/li[position()=last()-1]/a/text()').get(default="").strip()
        d = {
            "brand": 'LGC',
            "parent": parent or related_categories,
            "cat_no": cat_no,
            "en_name": response.xpath('//h1[@class="product__title"]/text()').get(default="").strip(),
            "cas": response.xpath(tmp.format("CAS Number")).get(default="").strip() or None,
            "mf": response.xpath(tmp.format("Molecular Formula")).get("").replace(" ", "") or None,
            "mw": response.xpath(tmp.format("Molecular Weight")).get(),
            "stock_info": response.xpath(
                '//h4[contains(@class,"orderbar__stock-title")]/descendant-or-self::text()').get(
                "").strip() or None,
            "img_url": response.xpath('//div[contains(@class, "product__brand-img")]/img/@src').get(),
            "info1": response.xpath(tmp.format("IUPAC")).get(default="").strip(),
            "info3": response.xpath('//span[text()="Pack Size:"]/following-sibling::p/text()').get(),
            "prd_url": response.request.url,
        }
        yield RawData(**d)

