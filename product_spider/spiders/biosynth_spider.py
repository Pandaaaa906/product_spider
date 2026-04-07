import re
from time import time
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class BiosynthSpider(BaseSpider):
    name = "biosynth"
    start_urls = ["https://www.biosynth.com/"]

    def parse(self, response, **kwargs):
        cat_urls = response.xpath('//li[a/text()="Catalog Products"]//div/a[1]/@href')
        print(cat_urls)
        for rel_url in cat_urls:
            yield Request(urljoin(response.url, f"{rel_url}", ), callback=self.parse_category_list)

    def parse_category_list(self, response):
        cat_nodes = response.xpath('//div[contains(@class, "categories")]/div/div/a[not(contains(div/text(), "View All"))]')
        for cat_node in cat_nodes:
            rel_url = cat_node.xpath('./@href').get()
            yield Request(urljoin(response.url, rel_url), callback=self.parse_category_list)

        prd_urls = response.xpath('//div[@class=" product-list"]//a[h3]/@href')
        for rel_url in prd_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

    def parse_detail(self, response):
        tmpl = '//div[@id="nav-tabContent"]//div[position()=1 and text()={!r}]/following-sibling::div//text()'
        rel_img = response.xpath('//div[@class="form-row"]//img[not(contains(@src, "Bottle"))]').get()
        prod_id = (m := re.search(r'var prodid = "(\d+)";', response.text)) and m.group()
        d = {
            "brand": self.name,
            "cat_no": response.xpath(tmpl.format("Product Code")).get(),
            "en_name": response.xpath('//h1/text()').get(),
            "cas": response.xpath(tmpl.format("CAS No")).get(),
            "mf": ''.join(response.xpath(tmpl.format("Chemical Formula")).getall()),
            "mw": ''.join(response.xpath(tmpl.format("Molecular Weight")).getall()),
            "smiles": ''.join(response.xpath(tmpl.format("Smiles")).getall()),
            "info1": ';'.join(response.xpath(tmpl.format("Synonyms")).getall()),
            "info2": response.xpath(tmpl.format("Storage")).get(),

            "prd_url": response.url,
            "img": rel_img and urljoin(response.url, rel_img),
        }
        yield RawData(**d)
        if not prod_id:
            return
        yield Request(
            f"https://www.biosynth.com/ajax/atc?id={prod_id}&_={time()*1000:.0f}",
            callback=self.parse_package, meta={"prd": d}
        )

    def parse_package(self, response):
        prd = response.meta.get("prd", {})
        dd = {
            "brand": self.name,
            "cat_no": prd.get("cat_no"),

        }
        yield ProductPackage(**dd)

