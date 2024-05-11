
from urllib.parse import urljoin

import scrapy
from product_spider.items import ProductPackage, RawData, SupplierProduct, RawSupplierQuotation
from product_spider.utils.cost import parse_cost
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class TsbiochemSpider(BaseSpider):
    """陶术"""
    name = "tsbiochem"
    start_urls = ["https://www.tsbiochem.com/"]
    base_url = "https://www.tsbiochem.com/"

    def parse(self, response, **kwargs):
        rows = response.xpath("//div[@class='column']/a/@href").getall()
        for rel_url in rows:
            yield scrapy.Request(
                url=urljoin(response.url, rel_url),
                callback=self.parse_list
            )

    def parse_list(self, response):
        # catalog list
        rows = response.xpath('//div[@class="block-targets"]/a/@href').getall()
        for rel_url in rows:
            yield scrapy.Request(
                url=urljoin(response.url, rel_url),
                callback=self.parse_list
            )

        # product list
        nodes = response.xpath("//table[@class='table-cpd-list']//tbody/tr")
        for node in nodes:
            rel_url = node.xpath("./td[position()=1]/a/@href").get()
            cat_no = node.xpath("./td[position()=1]/a/text()").get()
            yield scrapy.Request(
                url=urljoin(response.url, rel_url),
                callback=self.parse_detail_v2,
                meta={
                    "cat_no": cat_no,
                }
            )
        # product list paginator
        next_url = response.xpath("//div[@class='block-pager']/a[last()]/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list
            )

    def parse_detail_v2(self, response):
        cat_no = response.meta.get("cat_no")
        parent = response.xpath('//div[contains(@class, "block-breadcrumb")]/ol[last()]//a/text()').get()
        en_name = response.xpath('//div[contains(@class, "product-name-title")]/h1/text()').get()
        purity = response.xpath(
            "//table[@class='table-cpd-info']//td[contains(text(), '纯度')]/following-sibling::td/span/text()"
        ).get()
        mw = response.xpath(
            "//table[@class='table-cpd-info']//td[contains(text(), '分子量')]/following-sibling::td/text()"
        ).get()
        if mw:
            mw = mw.strip()
        mf = response.xpath(
            "//table[@class='table-cpd-info']//td[contains(text(), '分子式')]/following-sibling::td/text()"
        ).get()
        cas = response.xpath(
            "//table[@class='table-cpd-info']//td[contains(text(), 'CAS No.')]/following-sibling::td/text()"
        ).get()
        img_url = urljoin(self.base_url, response.xpath("//div[@class='img-box']/img/@src").get()) \
                  or response.xpath("//div[@class='img-box']/div/text()").get()
        if parent == '首页':
            parent = None
        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": parent,
            "en_name": en_name,
            "purity": purity,
            "mw": mw,
            "mf": mf,
            "cas": cas,
            "prd_url": response.url,
            "img_url": img_url,
        }

        yield RawData(**d)
        yield SupplierProduct(**rawdata_to_supplier_product(d, platform=self.name, vendor=self.name))
        nodes = response.xpath("//tr[@class='line-item']")
        for node in nodes:
            package = node.xpath("./td[position()=1]/text()").get()
            delivery_time = node.xpath("./td[position()=3]/text()").get()
            price = parse_cost(node.xpath("./td[position()=2]/text()").get())
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "delivery_time": delivery_time,
                "cost": price,
                "currency": "RMB",
            }
            yield ProductPackage(**dd)
            if dd.get("cost") and dd.get("cost") != "待询":
                yield RawSupplierQuotation(**product_package_to_raw_supplier_quotation(d, dd, self.name, self.name))
