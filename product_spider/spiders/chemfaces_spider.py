from urllib.parse import urljoin
import scrapy
from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class ChemfacesSpider(BaseSpider):
    """武汉天植"""
    name = "chemfaces"
    allow_domain = ["chemfaces.com"]
    start_urls = ["https://www.chemfaces.com/compound/index.php", ]
    base_url = "https://www.chemfaces.com/"

    def parse(self, response):
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

        if package_info != 'Inquiry':
            price, *_, package = package_info.split()
            price = price.replace("$", '')
        else:
            price = None
            package = None

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

        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "price": price,
            "package": package,
            "currency": "$",
        }
        yield RawData(**d)
        yield ProductPackage(**dd)
