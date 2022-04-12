from urllib.parse import urljoin
import scrapy
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.items import RawData, ProductPackage


class BertinbioreagentSpider(BaseSpider):
    name = "bertinbioreagent"
    allow_domain = ["bertin-bioreagent.com"]
    start_urls = ["https://www.bertin-bioreagent.com/pa266/products?nbProduitsParPage_Param=100"]
    base_url = "https://www.bertin-bioreagent.com"

    def parse(self, response, *args, **kwargs):
        rows = response.xpath("//ul[@class='thumbnails liste-produits']//li")
        for row in rows:
            href = urljoin(self.base_url, row.xpath(".//a/@href").get())
            if href:
                yield scrapy.Request(
                    href,
                    callback=self.parse_detail
                )

        next_url = urljoin(self.base_url, response.xpath("//a[@rel='next']/@href").get())
        if next_url:
            yield scrapy.Request(
                next_url,
                callback=self.parse
            )

    def parse_detail(self, response):
        parent = response.xpath("//div[@class='famille']/a[last()]/span/text()").get()
        cat_no = response.xpath("//div[@class='refInfo']//span[last()]/text()").get()
        en_name = ''.join(response.xpath("//div[@id='bloc_2_content']//h1/text()").getall())
        cas = response.xpath(
            "//div[@id='tabsFicheProduit-data']//td[contains(text(), 'CAS Number')]/following-sibling::td/text()").get()
        smiles = response.xpath(
            "//div[@id='tabsFicheProduit-data']//td[contains(text(), 'SMILES')]/following-sibling::td/text()").get()
        mf = ''.join(response.xpath("//td[text()='Molecular Formula']/following-sibling::td[1]//text()").getall())
        mw = response.xpath(
            "//div[@id='tabsFicheProduit-data']//td[contains(text(), 'Molecular Weight')]/following-sibling::td/text()").get()
        purity = response.xpath(
            "//div[@id='tabsFicheProduit-data']//td[contains(text(), 'Purity')]/following-sibling::td/text()").get()
        img_url = response.xpath("//div[@class='container-img-diapo']//img/@src").get()

        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": cat_no,
            "en_name": en_name,
            "cas": cas,
            "smiles": smiles,
            "mf": mf,
            "mw": mw,
            "purity": purity,
            "prd_url": response.url,
            "img_url": img_url
        }
        yield RawData(**d)
        rows = response.xpath("//select[@id='ecom_cat_decli_type_1']/option")
        for row in rows:
            package = row.xpath("./text()").get()
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "currency": "EUR"
            }
            yield ProductPackage(**dd)
