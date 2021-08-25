from scrapy import Request
from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider
import re
from more_itertools import first

class EchelonSpider(BaseSpider):
    name = "echelon"
    allow_domain = ["echelon-inc.com"]
    start_urls = ["https://echelon-inc.com/shop/", ]

    def parse(self, response):
        urls = response.xpath("//div[@class='astra-shop-summary-wrap']//a/@href").getall()
        for url in urls:
            yield Request(
                url=url,
                callback=self.parse_detial,
            )
        next_url = response.xpath("//li/a[@class='next page-numbers']/@href").get()
        if next_url:
            yield Request(
                url=next_url,
                callback=self.parse,
            )

    def parse_detial(self, response):
        mw =response.xpath("//div[@class='woocommerce-Tabs-panel woocommerce-Tabs-panel--description panel entry-content wc-tab']//p/text()[contains(self::text(),'Molecular Weight:')]").get()
        mw2 = response.xpath("//tr[contains(@class, 'woocommerce-product-attributes-item--attribute_pa_mw')]//p/text()").get()
        cas = response.xpath("//div[@class='woocommerce-Tabs-panel woocommerce-Tabs-panel--description panel entry-content wc-tab']/p[contains(text(),'CAS Number:')]/text()").get()
        cas2 = response.xpath('//tr[@class="woocommerce-product-attributes-item woocommerce-product-attributes-item--attribute_pa_cas"]//td[@class="woocommerce-product-attributes-item__value"]//p/text()').get()
        purity = response.xpath("//div[@class='woocommerce-Tabs-panel woocommerce-Tabs-panel--description panel entry-content wc-tab']//p/text()[contains(self::text(),'Purity:')]").get()
        purity2 = response.xpath("//tr[@class='woocommerce-product-attributes-item woocommerce-product-attributes-item--attribute_pa_purity']//p/text()").get()
        cat_no = response.xpath("//div[@class='woocommerce-product-details__short-description']//p/text()").get('')
        cat_no = re.sub(r'Product Number:', '', cat_no, 0, re.IGNORECASE)
        info = response.xpath("//div[@class='woocommerce-Tabs-panel woocommerce-Tabs-panel--description panel entry-content wc-tab']//p/text()[contains(self::text(),'Storage:')]").get()
        info2 = response.xpath("//tr[@class='woocommerce-product-attributes-item woocommerce-product-attributes-item--attribute_pa_storage']//td[@class='woocommerce-product-attributes-item__value']//p/text()").get()

        d = {
            "brand" : self.name,
            "cat_no" : cat_no,
            "parent" : response.xpath('//tr[@class="woocommerce-product-attributes-item woocommerce-product-attributes-item--attribute_pa_categories"]//td[@class="woocommerce-product-attributes-item__value"]/p/text()').get(),
            "cas" : (cas and first(re.findall(r'CAS Number: (.+)',cas), None)) or cas2,
            "mf" : response.xpath("//tr[@class='woocommerce-product-attributes-item woocommerce-product-attributes-item--attribute_pa_molecular-formula']//td[@class='woocommerce-product-attributes-item__value']//p/text()").get(),
            'mw' : (mw and first(re.findall(r'Molecular Weight: (.+)',mw), None)) or mw2,
            'purity' : (purity and first(re.findall(r'Purity: (.+)',purity), None)) or purity2,
            'img_url' : response.xpath("//div[@class='woocommerce-product-gallery woocommerce-product-gallery--with-images woocommerce-product-gallery--columns-4 images']//a/@href").get(),
            'prd_url': response.url,
            'en_name' : response.xpath("//h1[@class='product_title entry-title']//text()").get(),
            "info2" : (info and first(re.findall(r'Storage: (.+)',info), None)) or info2
        }

        yield RawData(**d)

        rows = response.xpath("//table[@class='woocommerce-grouped-product-list group_table']//tr")
        for row in rows:
            dd = {
                "brand" : self.name,
                "cat_no" : cat_no,
                "package" : row.xpath(".//td[@class='woocommerce-grouped-product-list-item__label']/label/text()").get(),
                "currency" : 'USD',
                "price" : row.xpath(".//span[@class='woocommerce-Price-currencySymbol']//parent::bdi/text()").get(),
            }
            dd["package"] = first(re.findall(r'[^(]+', dd["package"]),None)

            yield ProductPackage(**dd)




