import json
from urllib.parse import urljoin

import scrapy
from scrapy.spiders import CrawlSpider
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip


class AaronchemSpider(CrawlSpider):
    name = "aaronchem"
    allow_domain = ["aaronchem.com"]
    start_urls = ["https://www.aaronchem.com/product.html?page=1", ]
    base_url = 'https://www.aaronchem.com/storage/structure'

    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }

    def start_requests(self):
        yield scrapy.Request(
            url='https://www.aaronchem.com/product.html?page=1',
            callback=self.parse
        )

    def parse(self, response, **kwargs):
        nodes = response.xpath('//ul[@class="ul2 "]/li/a')
        for node in nodes:
            parent = node.xpath('./text()').get()
            url = node.xpath('./@href').get()
            yield scrapy.Request(url, callback=self.parse_list, meta={'parent': parent})

    def parse_list(self, response):
        parent = response.meta.get('parent', None)
        urls = response.xpath("//a[@class='view_detial']/@href").getall()
        for url in urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={"parent": parent}
            )

        next_url = response.xpath('//div[@class="layui-box layui-laypage"]/a[@rel="next"]/@href').get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        parent = response.meta.get("parent", None)
        img_url = urljoin(self.base_url, response.xpath("//div[@class='detail_img']/img/@src").get())
        en_name = response.xpath("//div[@class='detail_des']/h2/text()").get()
        cat_no = strip(response.xpath("//td[contains(text(), 'Catalog Number')]/following-sibling::td/text()").get())
        mdl = strip(response.xpath("//td[contains(text(), 'MDL Number')]/following-sibling::td/text()").get())
        smiles = strip(response.xpath("//td[contains(text(), 'SMILES')]/following-sibling::td/text()").get())
        info1 = strip(response.xpath("//td[contains(text(), 'Chemical Name')]/following-sibling::td/text()").get())
        cas = strip(response.xpath("//td[contains(text(), 'CAS Number')]/following-sibling::td/text()").get())
        mf = strip(response.xpath("//td[contains(text(), 'Molecular Formula')]/following-sibling::td/text()").get())
        mw = strip(response.xpath("//td[contains(text(), 'Molecular Weight')]/following-sibling::td/text()").get())

        inchl = strip(response.xpath("//td[contains(text(), 'InChI')]/following-sibling::td/text()").get())
        inchl_key = strip(response.xpath("//td[contains(text(), 'InChI Key')]/following-sibling::td/text()").get())
        iupac = strip(response.xpath("//td[contains(text(), 'IUPAC Name')]/following-sibling::td/text()").get())

        prd_attrs = json.dumps({
            "inchl": inchl,
            "inchl_key": inchl_key,
            "iupac": iupac
        })

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": parent,
            "en_name": en_name,
            "mdl": mdl,
            "smiles": smiles,
            "info1": info1,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "prd_url": response.url,
            "img_url": img_url,
            "attrs": prd_attrs,
        }
        yield RawData(**d)

        rows = response.xpath("//div[@class='detail']//tr[position()>1]")
        for row in rows:
            price = row.xpath('./td[3]/text()').get()
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": row.xpath('./td[1]/text()').get(),
                "currency": "USD",
                "cost": parse_cost(price),
            }
            yield ProductPackage(**dd)

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id": f'{self.name}_{d["cat_no"]}_{dd["package"]}',
                "parent": d["parent"],
                "en_name": d["en_name"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "smiles": d["smiles"],
                "currency": dd["currency"],
                "img_url": d["img_url"],
                "prd_url": response.url,
            }
            dddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id": f'{self.name}_{d["cat_no"]}',
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'discount_price': dd['cost'],
                'price': dd['cost'],
                'cas': d["cas"],
                'currency': dd["currency"],
            }
            yield SupplierProduct(**ddd)
            yield RawSupplierQuotation(**dddd)
