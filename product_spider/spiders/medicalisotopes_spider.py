from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip
from product_spider.utils.parsepackage import parse_package
from product_spider.utils.spider_mixin import BaseSpider


class MedicalIsotopesSpider(BaseSpider):
    name = "medicalisotopes"
    base_url = "https://www.medicalisotopes.com/"
    start_urls = ['https://www.medicalisotopes.com/productsbycategories.php', ]

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//div[contains(@class, "main-content")]//a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, url), callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        rel_urls = response.xpath('//td[2]/a/@href').getall()
        parent = response.meta.get('parent')
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//a[@class="c-page"]/following-sibling::a[text()!="NEXT"]/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse_list, meta={'parent': parent})

    def parse_detail(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td//text()'
        d = {
            'brand': 'medicalisotopes',
            'parent': response.meta.get('parent'),
            'cat_no': strip(response.xpath(tmp.format("Catalog Number:")).get()),
            'en_name': strip(response.xpath('//th[contains(text(), "Product:")]/following-sibling::th/text()').get()),
            'cas': strip(response.xpath(tmp.format("CAS Number:")).get()),
            'mf': strip(''.join(response.xpath(tmp.format("Formula:")).getall())),
            'mw': strip(response.xpath(tmp.format("Molecular Weight:")).get()),
            'prd_url': response.url,
        }
        yield RawData(**d)
        rows = response.xpath("//td[contains(text(), 'Pricing:')]/following-sibling::td/table//tr")
        for row in rows:
            raw_package = row.xpath("./td[last()-3]/text()").get("\xa0=").rstrip('\xa0=')
            package = parse_package(raw_package)
            cost = row.xpath("./td[last()-2]/text()").get()
            if not package:
                continue
            dd = {
                'brand': 'medicalisotopes',
                'cat_no': d["cat_no"],
                'package': package,
                'cost': parse_cost(cost),
                'currency': "USD",
            }
            yield ProductPackage(**dd)
            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "parent": d["parent"],
                "en_name": d["en_name"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
                "prd_url": d["prd_url"],
            }
            yield SupplierProduct(**ddd)
