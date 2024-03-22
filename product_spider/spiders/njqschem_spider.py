from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class NJQSSpider(BaseSpider):
    """南京强山"""
    name = "njqschem"

    start_urls = [
        "http://www.njqschem.com/productse.php"
    ]

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//table[@id="left_pro"]//td/a')
        for a_node in a_nodes:
            parent = a_node.xpath('./text()').get()
            url = a_node.xpath('./@href').get()
            yield Request(
                url=urljoin(response.url, url),
                callback=self.parse_list,
                meta={"parent": parent}
            )
        yield from self.parse_list(response, **kwargs)

    def parse_list(self, response, **kwargs):
        urls = response.xpath('//td[2]/a/@href').getall()
        for url in urls:
            yield Request(
                url=urljoin(response.url, url),
                callback=self.parse_detail,
                meta=response.meta
            )

        next_urls = response.xpath('//td[@class="s"]/strong/a[not(./img)]/@href').getall()
        for next_page in next_urls:
            yield Request(
                url=urljoin(response.url, next_page),
                callback=self.parse_list,
                meta=response.meta
            )

    def parse_detail(self, response):
        tmpl = '//td[text()={!r}]/following-sibling::td/text()'
        _id = response.xpath(tmpl.format("No.：")).get()
        rel_img = response.xpath('//td[text()="Molecular Structure："]/following-sibling::td/img/@src').get()
        cat_no = (t := f"{self.name.upper()}-{_id}") and t.strip()
        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": response.meta.get("parent"),
            "en_name": strip(response.xpath(tmpl.format("Product Name：")).get()),
            "cas": strip(response.xpath(tmpl.format("Cas No.：")).get()),
            "purity": strip(response.xpath(tmpl.format("Purity：")).get()),
            "prd_url": response.url,
            "img_url": rel_img and urljoin(response.url, rel_img),
        }
        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "package": strip(pkg := response.xpath(tmpl.format("Pack：")).get()),
            "purity": strip(d["purity"]),
            "info": strip(price := response.xpath(tmpl.format("Price：")).get()),
        }
        yield RawData(**d)
        yield ProductPackage(**dd)
