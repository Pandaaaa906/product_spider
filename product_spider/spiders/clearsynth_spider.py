import json
from urllib.parse import urljoin, urlencode
from lxml import etree
from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class ClearsynthSpider(BaseSpider):
    name = "clearsynth"
    base_url = "https://www.clearsynth.com/en/"
    start_urls = [
        "https://www.clearsynth.com/en/api.asp",
        "https://www.clearsynth.com/en/categories",
    ]

    def start_requests(self):
        for url in self.start_urls:
            # 解析api分类
            if url == "https://www.clearsynth.com/en/api.asp":
                yield Request(
                    url=url,
                    callback=self.parse_api,
                )
            else:
                # 解析普通分类
                yield Request(
                    url=url,
                    callback=self.parse_catalog,
                )

    def parse_api(self, response, **kwargs):
        """请求api"""
        params = response.xpath("//div[@align='center']/text()").getall()
        for param in params:
            url = '{}{}'.format(
                "https://www.clearsynth.com/en/search.asp?",
                urlencode({"s": param})
            )
            yield Request(
                url=url,
                callback=self.parse_api_list,
            )

    def parse_api_list(self, response):
        html_response = etree.HTML(response.text)
        urls = html_response.xpath("//*[@class='product-img-action-wrap']/a/@href")
        for url in urls:
            yield Request(
                url=url,
                callback=self.parse_detail
            )
        next_url = response.xpath("//*[contains(text(), 'Next >')]/@href").get()
        if next_url:
            yield Request(
                url=urljoin(self.base_url, next_url),
                callback=self.parse_api_list,
            )

    def parse_catalog(self, response, **kwargs):
        """获取全部分类(包含其他分类)"""
        urls = response.xpath("//div[@class='icon-box-title']//a/@href").getall()
        for url in urls:
            url = urljoin(self.base_url, url)
            yield Request(
                url=url,
                callback=self.parse_prd_list
            )

    def parse_prd_list(self, response):
        """解析产品列表"""
        urls = response.xpath("//*[@class='product-img-action-wrap']/a/@href").getall()
        for url in urls:
            yield Request(
                url=url,
                callback=self.parse_detail
            )
        next_url = response.xpath("//*[contains(text(), 'Next >')]/@href").get()
        if next_url:
            yield Request(
                url=urljoin(self.base_url, next_url),
                callback=self.parse_prd_list,
            )

    def parse_detail(self, response):
        tmp_xpath = "//*[contains(text(), {!r})]/following-sibling::td[last()]//text()"
        category = response.xpath(tmp_xpath.format("Category")).get()
        img_url = response.xpath("//div[@class='compound_name3']/a/@href").get()

        cat_no = strip(response.xpath(tmp_xpath.format('Catalog Number')).get())
        cas = strip(response.xpath(tmp_xpath.format('CAS Number')).get())
        mw = strip(response.xpath(tmp_xpath.format('Molecular Weight')).get())
        mf = strip(formula_trans(''.join(response.xpath(tmp_xpath.format('Molecular Formula')).getall())))

        inchl = response.xpath(tmp_xpath.format('InChI')).get()
        iupac = response.xpath(tmp_xpath.format('IUPAC Name')).get()
        inchlkey = response.xpath(tmp_xpath.format('InchIKey')).get()

        prd_attrs = json.dumps({
            "api_name": category,
            "inchl": inchl,
            "iupac": iupac,
            "inchlkey": inchlkey,
        })

        d = {
            "brand": "clearsynth",
            "en_name": response.xpath(tmp_xpath.format('Compound :')).get(),
            "cat_no": cat_no,
            "cas": cas,
            "parent": category,
            "mw": mw,
            "mf": mf,
            "purity": response.xpath(tmp_xpath.format('Purity :')).get(),
            "info1": strip(response.xpath(tmp_xpath.format('Synonyms')).get()),
            "info2": strip(response.xpath(tmp_xpath.format('Storage Condition :')).get()),
            "stock_info": strip(response.xpath("//*[@class='stock-status stt']/text()").get()),
            "attrs": prd_attrs,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)
        rows = response.xpath("//div[@class='compound_name5']//tr")
        if not rows:
            return
        for row in rows:
            raw_package = row.xpath(".//td[last()-2]//text()").get()
            raw_cost = parse_cost(row.xpath(".//td[last()-3]//text()").get())
            if raw_package is None:
                continue
            package = ''.join(raw_package.split()).lower()
            cost = raw_cost
            dd = {
                "brand": d["brand"],
                "cat_no": d["cat_no"],
                "package": package,
                "cost": cost,
                "currency": "USD",
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
                "currency": dd["currency"],
                "img_url": d["img_url"],
                "prd_url": d["prd_url"],
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
