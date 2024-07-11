from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class PharmalegoSpider(BaseSpider):
    name = "pharmalego"
    brand = "pharmalego"
    start_urls = ['https://cn.pharmalego.com/all-products/index.html']
    base_url = "https://cn.pharmalego.com"

    def parse(self, response, **kwargs):
        urls = response.xpath("//div[@class='Content_list_txt']//a/@href").getall()
        for url in urls:
            yield Request(urljoin(self.base_url, url), callback=self.parse_list)

    def parse_list(self, response):
        detail_urls = response.xpath("//a[@class='HProductContent_list_title']/@href").getall()
        for u in detail_urls:
            yield Request(url=urljoin(self.base_url, u), callback=self.parse_detail, meta=response.meta)
        next_href = response.xpath("(//div[@class='page']//i)[last()]/parent::*/@href").get()
        if next_href:
            yield Request(url=urljoin(response.url, next_href), callback=self.parse_list)

    def parse_detail(self, response):
        img_rel = response.xpath("//div[@class='left_top_img']//img/@src").get()
        info_xpath = "//div[@class='txt_con_list']//div[contains(text(),{!r})]/following-sibling::div[1]/text()"
        cat_no = response.xpath(info_xpath.format('产品编号')).get()
        cat_no = cat_no or response.xpath(info_xpath.format('产品货号')).get()
        d = {
            'brand': self.brand,
            'parent': response.xpath("(//div[contains(@class,'BreadCrumbs')]//a/text())[last()]").get(),
            'cat_no': cat_no,
            'chs_name': response.xpath("//h1[contains(@class,'txt_title_dd')]/text()").get(),
            'en_name': response.xpath("//div[contains(@class,'txt_title_dt')]/text()").get(),
            'cas': response.xpath(info_xpath.format('CAS')).get(),
            'mf': formula_trans(response.xpath(info_xpath.format('分子式')).get()),
            'mw': response.xpath(info_xpath.format('分子量')).get(),
            'smiles': response.xpath(info_xpath.format('Smiles Code')).get(),
            'img_url': img_rel and urljoin(self.base_url, img_rel),
            'prd_url': response.url,
        }
        yield RawData(**d)
        packages = response.xpath('//div[@class="sco_content_list"]')
        for pkg in packages:
            brand = (brand := pkg.xpath(".//div[position()=1]/text()").get()) and brand.lower()
            cost = pkg.xpath(".//div[position()=5]/div/text()").get()
            cost = None if cost and '面议' in cost else cost
            dd = {
                "brand": brand,
                "cat_no": d['cat_no'],
                "package": pkg.xpath(".//div[position()=4]/text()").get(),
                "cost": cost,
                "price": cost,
                "currency": "RMB"
            }
            if brand == self.name:
                yield ProductPackage(**dd)
