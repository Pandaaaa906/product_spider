from scrapy import Request
from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.cost import parse_cost
from product_spider.utils.parsepackage import parse_package
from product_spider.utils.spider_mixin import BaseSpider
import re
from more_itertools import first


class EchelonSpider(BaseSpider):
    name = "echelon"
    allow_domain = ["echelon-inc.com"]
    start_urls = ["https://echelon-inc.com/shop/", ]

    def parse(self, response, **kwargs):
        urls = response.xpath("//div[@class='astra-shop-summary-wrap']//a/@href").getall()
        for url in urls:
            yield Request(
                url=url,
                callback=self.parse_detail,
            )
        next_url = response.xpath("//li/a[@class='next page-numbers']/@href").get()
        if next_url:
            yield Request(
                url=next_url,
                callback=self.parse,
            )

    def parse_detail(self, response):
        mw = response.xpath(
            "//div[@class='woocommerce-Tabs-panel woocommerce-Tabs-panel--description panel entry-content wc-tab']//p/text()[contains(self::text(),'Molecular Weight:')]").get()
        mw2 = response.xpath(
            "//tr[contains(@class, 'woocommerce-product-attributes-item--attribute_pa_mw')]//p/text()").get()
        cas = response.xpath(
            "//div[@class='woocommerce-Tabs-panel woocommerce-Tabs-panel--description panel entry-content wc-tab']/p[contains(text(),'CAS Number:')]/text()").get()
        cas2 = response.xpath(
            '//tr[@class="woocommerce-product-attributes-item woocommerce-product-attributes-item--attribute_pa_cas"]//td[@class="woocommerce-product-attributes-item__value"]//p/text()').get()
        purity = response.xpath(
            "//div[@class='woocommerce-Tabs-panel woocommerce-Tabs-panel--description panel entry-content wc-tab']//p/text()[contains(self::text(),'Purity:')]").get()
        purity2 = response.xpath(
            "//tr[@class='woocommerce-product-attributes-item woocommerce-product-attributes-item--attribute_pa_purity']//p/text()").get()
        cat_no = response.xpath("//div[@class='woocommerce-product-details__short-description']//p/text()").get('')
        cat_no = re.sub(r'Product Number:', '', cat_no, 0, re.IGNORECASE)
        info = response.xpath(
            "//div[@class='woocommerce-Tabs-panel woocommerce-Tabs-panel--description panel entry-content wc-tab']//p/text()[contains(self::text(),'Storage:')]").get()
        info2 = response.xpath(
            "//tr[@class='woocommerce-product-attributes-item woocommerce-product-attributes-item--attribute_pa_storage']//td[@class='woocommerce-product-attributes-item__value']//p/text()").get()

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": response.xpath(
                '//tr[@class="woocommerce-product-attributes-item woocommerce-product-attributes-item--attribute_pa_categories"]//td[@class="woocommerce-product-attributes-item__value"]/p/text()').get(),
            "cas": (cas and first(re.findall(r'CAS Number: (.+)', cas), None)) or cas2,
            "mf": response.xpath(
                "//tr[@class='woocommerce-product-attributes-item woocommerce-product-attributes-item--attribute_pa_molecular-formula']//td[@class='woocommerce-product-attributes-item__value']//p/text()").get(),
            'mw': (mw and first(re.findall(r'Molecular Weight: (.+)', mw), None)) or mw2,
            'purity': (purity and first(re.findall(r'Purity: (.+)', purity), None)) or purity2,
            'img_url': response.xpath(
                "//div[@class='woocommerce-product-gallery woocommerce-product-gallery--with-images woocommerce-product-gallery--columns-4 images']//a/@href").get(),
            'prd_url': response.url,
            'en_name': response.xpath("//h1[@class='product_title entry-title']//text()").get(),
            "info2": (info and first(re.findall(r'Storage: (.+)', info), None)) or info2
        }

        yield RawData(**d)

        rows = response.xpath("//table[@class='woocommerce-grouped-product-list group_table']//tr")
        for row in rows:
            package = first(re.findall(r'[^(]+', row.xpath(
                ".//td[@class='woocommerce-grouped-product-list-item__label']/label/text()").get()), None)
            cost = row.xpath(".//span[@class='woocommerce-Price-currencySymbol']//parent::bdi/text()").get()
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": parse_package(package),
                "currency": 'USD',
                "cost": parse_cost(cost),
            }

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
                "img_url": d["img_url"],
                "prd_url": d["prd_url"],
            }

            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)
