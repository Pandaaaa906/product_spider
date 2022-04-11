import json

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class AccPrdSpider(BaseSpider):
    name = 'acc'
    allowed_domains = ['accustandard.com']
    base_url = 'https://www.accustandard.com'
    start_urls = ['https://www.accustandard.com/organic.html?limit=100',
                  'https://www.accustandard.com/petrochemical.html?limit=100',
                  'https://www.accustandard.com/inorganic.html?limit=100',
                  ]

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS_PER_IP': 2,
    }

    def parse(self, response, *args, **kwargs):
        prd_urls = response.xpath('//a[@class="product-item-link"]/@href').extract()
        for prd_url in prd_urls:
            yield Request(prd_url, callback=self.detail_parse)

        next_page_url = response.xpath('//a[@class="action  next"]/@href').get()
        if next_page_url is not None:
            yield Request(next_page_url, method="GET", callback=self.parse)

    def detail_parse(self, response):
        tmp = '//div[contains(@class, {!r})]/div[contains(@class, "value")]//text()'
        cat_no = response.xpath('//div[@itemprop="sku"]/text()').get()
        package = response.xpath(tmp.format('sales_unit_size')).get()
        if package is not None:
            package = package.replace(" ", '')

        feature = response.xpath("//*[contains(text(), 'Matrix')]/parent::div/following-sibling::div/text()").get()  # 特性值

        prd_attrs = json.dumps({
            "feature": feature
        })

        d = {
            "brand": "accustandard",
            "parent": response.xpath('//li[position()=last()-1]/a/span[@itemprop]/text()').get(),
            "cat_no": cat_no,
            "en_name": response.xpath('//h1[@class="page-title"]//text()').get(),
            "cas": ";".join(response.xpath('//td[contains(@class, "cas_number")]/text()').extract()),
            "mf": "".join(response.xpath(tmp.format('molecular_formula')).extract()) or None,
            "mw": response.xpath(tmp.format('molecular_weight')).get(),
            "img_url": response.xpath('//img[@itemprop="image"]/@data-src').get(),
            "info2": response.xpath(tmp.format('storage_condition')).get(),
            "info3": response.xpath(tmp.format('sales_unit_size')).get(),
            "prd_url": response.url,
            "attrs": prd_attrs
        }

        dd = {
            "brand": "accustandard",
            "cat_no": cat_no,
            "package": package,
            "currency": "USD",
        }

        yield RawData(**d)
        yield ProductPackage(**dd)
