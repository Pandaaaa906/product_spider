from urllib.parse import urljoin

from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.functions import strip
from product_spider.items import RawData, ProductPackage


class NistSpider(BaseSpider):
    name = "nist"
    start_urls = ["https://www-s.nist.gov/srmors/pricerpt.cfm", ]
    base_url = "https://www-s.nist.gov/"
    brand = 'nist'

    def parse(self, response):
        rows = response.xpath('//table//tr[position()>2 and @class]')
        for row in rows:
            cat_no = row.xpath('./td[2]/a/text()').get()
            rel_url = row.xpath('./td[2]/a/@href').get()
            d = {
                'brand': self.brand,
                'cat_no': cat_no,
                'en_name': row.xpath('./td[3]/text()').get(),
                'info3': row.xpath('./td[4]/text()').get(),
                'info4': strip(row.xpath('./td[5]/text()').get()),
                'prd_url': urljoin(response.url, rel_url),
                'expiry_date': row.xpath('./td[6]/text()').get(),
            }
            yield RawData(**d)

            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': row.xpath('./td[4]/text()').get(),
                'price': strip(row.xpath('./td[5]/text()').get()),
                'currency': 'USD',
            }
            yield ProductPackage(**dd)
