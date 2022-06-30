from urllib.parse import urljoin
import scrapy
from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.cost import parse_cost
from product_spider.utils.spider_mixin import BaseSpider


class ChemfacesSpider(BaseSpider):
    """武汉天植"""
    name = "chemfaces"
    allow_domain = ["chemfaces.com"]
    start_urls = ["https://www.chemfaces.com/compound/index.php", ]
    base_url = "https://www.chemfaces.com/"

    def parse(self, response, **kwargs):
        rows = response.xpath("//div[@class='com_left']")
        for row in rows:
            url = urljoin(self.base_url, row.xpath(".//a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        rows = response.xpath("//tr[@class='hot_tab_tr']/following-sibling::tr")
        for row in rows:
            url = urljoin(self.base_url, row.xpath(".//a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail
            )
        next_url = urljoin(self.base_url, response.xpath("//a[contains(text(), 'Next')]/@href").get())
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list
            )

    def parse_detail(self, response):
        cat_no = response.xpath("//td[contains(text(), 'Catalog No.')]/following-sibling::td/text()").get()
        cas = response.xpath("//td[contains(text(), 'CAS No.')]/following-sibling::td/text()").get()
        mf = ''.join(response.xpath("//td[contains(text(), 'Formula')]/following-sibling::td[1]//text()").getall())
        mw = response.xpath("//td[contains(text(), 'Molecular Weight')]/following-sibling::td/text()").get()
        parent = response.xpath("//td[contains(text(), 'Type of Compound')]/following-sibling::td/text()").get()
        purity = response.xpath("//td[contains(text(), 'Purity')]/following-sibling::td/text()").get()
        appearance = response.xpath("//td[contains(text(), 'Physical Description')]/following-sibling::td/text()").get()
        en_name1 = response.xpath("//div[@class='pi_title']/b/text()").get()
        en_name2 = response.xpath("//div[@class='pi_title']/b/a/text()").get()
        en_name = en_name1 or en_name2
        img_url = urljoin(self.base_url, response.xpath("//img[@id='img_id']/@src").get())
        package_info1 = response.xpath("//td[contains(text(), 'Price')]//following-sibling::td/span/text()").get()
        package_info2 = response.xpath("//td[contains(text(), 'Price')]//following-sibling::td/input/@value").get()
        package_info = package_info1 or package_info2

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "parent": parent,
            "purity": purity,
            "en_name": en_name,
            "appearance": appearance,
            "img_url": img_url,
            "prd_url": response.url
        }

        if package_info == 'Inquiry':
            yield RawData(**d)
        elif package_info is not None and package_info != 'Inquiry':
            price, *_, package = package_info.split()
            price = parse_cost(price)

            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "cost": price,
                "package": package,
                "currency": "USD",
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
