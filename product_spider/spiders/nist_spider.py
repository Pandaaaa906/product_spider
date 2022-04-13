import json
from urllib.parse import urljoin

import scrapy

from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.functions import strip
from product_spider.items import RawData, ProductPackage


class NistSpider(BaseSpider):
    name = "nist"
    start_urls = ["https://www-s.nist.gov/srmors/pricerpt.cfm", ]
    base_url = "https://www-s.nist.gov/"
    brand = 'nist'

    def parse(self, response, *args, **kwargs):
        rows = response.xpath('//table//tr[position()>2 and @class]')
        for row in rows:
            cat_no = row.xpath('./td[2]/a/text()').get()
            rel_url = row.xpath('./td[2]/a/@href').get()
            prd_url = urljoin(response.url, rel_url)
            d = {
                'brand': self.brand,
                'cat_no': cat_no,
                'en_name': row.xpath('./td[3]/text()').get(),
                'info3': row.xpath('./td[4]/text()').get(),
                'info4': strip(row.xpath('./td[5]/text()').get()),
                'prd_url': prd_url,
                'expiry_date': row.xpath('./td[6]/text()').get(),
            }

            package = row.xpath('./td[4]/text()').get()
            if package is not None:
                package = package.replace(" ", "")

            cost = strip(row.xpath('./td[5]/text()').get())
            if cost is not None:
                cost = cost.replace("$", '')

            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': package,
                'cost': cost,
                'currency': 'USD',
            }
            yield scrapy.Request(
                url=prd_url,
                callback=self.parse_detail,
                meta={
                    "product": d,
                    "package": dd,
                }
            )

    def parse_detail(self, response):
        d = response.meta.get("product")
        dd = response.meta.get("package")
        status = response.xpath("//*[contains(text(), 'Status:')]/following-sibling::td/text()").get().strip()  # 销售状态

        package_attrs = json.dumps({
            "status": status
        })
        dd["attrs"] = package_attrs
        yield RawData(**d)
        yield ProductPackage(**dd)
