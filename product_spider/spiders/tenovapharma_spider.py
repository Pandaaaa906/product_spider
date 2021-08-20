from urllib.parse import urljoin

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

from product_spider.items import RawData


class TenovaSpider(CrawlSpider):
    name = "tenovapharma"
    allow_domain = ["tenovapharma.com"]
    start_urls = ["https://tenovapharma.com/collections/all", ]

    rules = (
        Rule(LinkExtractor(allow=(r'.*collections/all?page=\d+')), follow=True ),  ##下一页
        Rule(LinkExtractor(allow=(r'.*/products/.*')), callback='parse_item', follow=False) ##解析详情页
    )

    def parse_item(self, response):

        d={
            "brand" : self.name,
            "cat_no" : response.xpath("//span[@class='variant-sku']//text()").get(),
            "pro_url" : response.url,
            "mf" : response.xpath('//td[contains(text(), "Molecular Formula:")]/following-sibling::td/text()').get(),
            "mw" : response.xpath('//td[contains(text(), "Molecular Weight:")]/following-sibling::td/text()').get(),
            "cas" : response.xpath('//td[contains(text(), "CAS Number:")]/following-sibling::td/text()').get(),
            "smiles" : response.xpath('//td[contains(text(), "SMILES:")]/following-sibling::td/text()').get(),
            "purity" : response.xpath('//td[contains(text(), "Purity (HPLC):")]/following-sibling::td/text()').get(),
            "info1" : response.xpath('//td[contains(text(), "Synonyms:")]/following-sibling::td/text()').get(),
            "info2" : response.xpath('//td[contains(text(), "Storage Conditions:")]/following-sibling::td/text()').get(),
            "img_url" : (m:=response.xpath('//noscript/img/@src').get()) and urljoin(response.url, m),
        }
        d["cat_no"] = d["cat_no"].split(":")[1].split("-")[0]


        yield RawData(**d)