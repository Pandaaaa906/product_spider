from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


def replace_last_slash_content(url, new_content) -> str:
    # 找到最后一个'/'的位置
    last_slash_index = url.rfind('/')
    # 如果没有找到'/'，返回原URL
    if last_slash_index == -1:
        return url
    # 替换最后一个'/'及之后的内容
    return url[:last_slash_index + 1] + new_content


class PharmalegoSpider(BaseSpider):
    name = "pharmalego"
    brand = "pharmalego"
    start_urls = ['https://cn.pharmalego.com/all-products/index.html']
    base_url = "https://cn.pharmalego.com"

    def parse(self, response, **kwargs):
        urls = response.xpath("//div[@class='Content_list_txt']//a/@href").getall()
        for url in urls:
            _url = urljoin(self.base_url, url)
            yield Request(_url, callback=self.parse_list)

    def parse_list(self, response):
        detail_urls = response.xpath("//a[@class='HProductContent_list_title']/@href").getall()
        for u in detail_urls:
            yield Request(url=urljoin(self.base_url, u), callback=self.parse_detail, meta=response.meta)
        next_href = response.xpath("(//div[@class='page']//i)[last()]/parent::*/@href").get()
        if next_href:
            next_url = replace_last_slash_content(response.url,next_href)
            yield Request(url=next_url, callback=self.parse_list)

    def parse_detail(self, response):
        img_rel = response.xpath("//div[@class='left_top_img']//img/@src").get()
        info_xpath = "//div[@class='txt_con_list']//div[contains(text(),{!r})]/following-sibling::div[1]/text()"
        d = {
            'brand': self.brand,
            'parent': response.xpath("(//div[contains(@class,'BreadCrumbs')]//a/text())[last()]").get(),
            'cat_no': response.xpath(info_xpath.format('产品编号')).get(),
            'chs_name': response.xpath("//h1[contains(@class,'txt_title_dd')]/text()").get(),
            'en_name': response.xpath("//div[contains(@class,'txt_title_dt')]/text()").get(),
            'cas': response.xpath(info_xpath.format('CAS')).get(),
            'mf': formula_trans(response.xpath(info_xpath.format('分子式')).get()),
            'mw': response.xpath(info_xpath.format('分子量')).get(),
            'img_url': img_rel and urljoin(self.base_url, img_rel),
            'prd_url': response.url,
        }
        yield RawData(**d)

        dd = {
            "brand": response.xpath("//div[@class='sco_content_list']/div[position()=1]/text()").get(),
            "cat_no": d['cat_no'],
            "package": response.xpath("//div[@class='sco_content_list']/div[position()=4]/text()").get(),
            "cost": response.xpath("//div[@class='sco_content_list']/div[position()=5]/div/text()").get(),
            "currency": "RMB"
        }
        yield ProductPackage(**dd)
