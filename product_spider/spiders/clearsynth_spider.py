import json
from urllib.parse import urljoin, urlencode
from lxml import etree
from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class ClearsynthSpider(BaseSpider):
    name = "clearsynth"
    base_url = "https://www.clearsynth.com/en/"
    start_urls = ["https://www.clearsynth.com/en/api.asp?c=API%20Standards", "https://www.clearsynth.com/en/categories"]

    def start_requests(self):
        for url in self.start_urls:
            if url == "https://www.clearsynth.com/en/api.asp?c=API%20Standards":
                yield Request(
                    url=url,
                    callback=self.parse_api,
                )
            else:
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
                callback=self.parse_catalog_list
            )

    def parse_catalog_list(self, response):
        """获取当前分类的子分类"""
        rows = response.xpath("//div[@class='col-lg-3 col-md-4 col-sm-6']//a/@href").getall()
        for row in rows:
            url = urljoin(self.base_url, row)
            yield Request(
                url=url,
                callback=self.parse_prd_list
            )
        urls = response.xpath(
            "//div[@class='product-badges product-badges-position product-badges-mrg']//a/@href"
        ).getall()
        if urls:
            for url in urls:
                yield Request(
                    url=url,
                    callback=self.parse_detail,
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
        tmp_xpath = "//*[contains(text(), {!r})]/following-sibling::td/text()"
        parent = response.xpath(tmp_xpath.format('Parent API')).get()
        category = response.xpath(tmp_xpath.format("Category")).get()
        img_url = response.xpath("//*[@class='p_details1']/img/@src").get()
        usage = response.xpath(tmp_xpath.format("Primary Usage :")).get()

        cat_no = strip(response.xpath(tmp_xpath.format('CAT No. :')).get())
        cas = strip(response.xpath(tmp_xpath.format('CAS Registry No. :')).get())
        mw = strip(response.xpath(tmp_xpath.format('Molecular Weight: ')).get())
        mf = formula_trans(strip(response.xpath(tmp_xpath.format('Molecular Formula :')).get()))

        prd_attrs = json.dumps({
            "api_name": parent,
            "usage": usage,
        })

        d = {
            "brand": "clearsynth",
            "en_name": response.xpath(tmp_xpath.format('Compound :')).get(),
            "cat_no": cat_no,
            "cas": cas,
            "parent": category or parent,
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
        rows = response.xpath("//div[@class='col-md-12']//tr")
        for row in rows:
            raw_package = row.xpath(".//td[last()-4]/span/text()").get()
            raw_cost = parse_cost(row.xpath(".//td[last()-1]//span/text()").get())
            if raw_package is None or raw_cost is None:
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
            yield SupplierProduct(**ddd)
