# TODO Get Blocked
from scrapy import Request

from product_spider.utils.spider_mixin import BaseSpider


class ChemServicePrdSpider(BaseSpider):
    name = "chemservice"
    base_url = "https://www.chemservice.com/"
    start_urls = ["https://www.chemservice.com/store.html?limit=100", ]
    handle_httpstatus_list = [500, ]

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS_PER_IP': 2,
    }

    def start_requests(self):
        yield Request(url=self.base_url, headers=self.headers, callback=self.home_parse)
        for item in self.start_urls:
            yield Request(url=item, headers=self.headers, callback=self.parse)

    def home_parse(self, response):
        self.headers["referer"] = response.url

    def parse(self, response):
        x_urls = response.xpath('//h2[@class="product-name"]/a/@href').getall()
        with open('html', 'w') as f:
            f.write(response.body_as_unicode())
        self.headers['referer'] = response.url
        for url in x_urls:
            yield Request(url, callback=self.prd_parse, headers=self.headers)
            break

    def prd_parse(self, response):
        tmp_d = {
            "name": response.xpath('//div[@itemprop="name"]/h1/text()').get(),
            "cat_no": response.xpath('//div[@itemprop="name"]/div[@class="product-sku"]/span/text()').get(),
            "cas": response.xpath('//div[@itemprop="name"]/div[@class="product-cas"]/span/text()').get(),
            "unit": response.xpath('//span[@class="size"]/text()').get(),
            "price": response.xpath('//span[@class="price"]/text()').get(),
            "stock_available": response.xpath('//p[@class="avail-count"]/span/text()').get(),
            "catalog": response.xpath(
                '//table[@id="product-attribute-specs-table"]//tr/th/text()[contains(.,"Classification")]/../../td/text()').get(),
            "synonyms": response.xpath(
                '//table[@id="product-attribute-specs-table"]//tr/th/text()[contains(.,"Alternate")]/../../td/text()').get(),
            "shipment": response.xpath('//p[contains(@class, "availability")]/span/text()')
        }
        d = dict()
        d["url"] = response.url
        for k, v in tmp_d.items():
            d[k] = v and v[0] or "N/A"
        concn_solv = response.xpath(
            '//table[@id="product-attribute-specs-table"]//tr/th/text()[contains(.,"Concentration")]/../../td/text()').get()
        if concn_solv:
            tmp = concn_solv[0].split('in')
            d['concn'] = tmp[0].strip()
            d['solv'] = tmp[1].strip()
        else:
            d['concn'] = "N/A"
            d['solv'] = "N/A"
        for k, v in tmp_d.items():
            print(k, v)
