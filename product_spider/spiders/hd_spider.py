from urllib.parse import urljoin

import re
import scrapy

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class HDPrdSpider(BaseSpider):
    """恒丰万达"""
    name = 'hd'
    base_url = "https://www.hdimpurity.com/"
    start_urls = ["https://www.hdimpurity.com/pro/", ]

    def parse(self, response, **kwargs):
        """获取分类"""
        rows = response.xpath("//div[@class='layout grid_5']/a[@class='catelist db dbox']")
        for row in rows:
            url = row.xpath("./@href").get()
            act_type = re.search(r'(?<=https://www.hdimpurity.com/).*(?=/)', url).group()
            if act_type == "list":
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_list,
                )
            else:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                )
        next_url = urljoin(self.base_url, response.xpath("//*[contains(text(), '下一页')]/@href").get())
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
            )

    def parse_list(self, response):
        """获取产品列表"""
        rows = response.xpath("//div[@class='divhover']")
        for row in rows:
            url = row.xpath("./a/@href").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )

    def parse_detail(self, response):
        cat_no = response.xpath("//*[contains(text(), '货号：')]/following-sibling::dd/text()").get()
        en_name = response.xpath("//*[contains(text(), '英文名：')]/following-sibling::dd/text()").get()
        cas = response.xpath("//*[contains(text(), 'CAS号：')]/following-sibling::dd/text()").get()
        mf = ''.join(response.xpath("//*[contains(text(), '分子式：')]/following-sibling::dd//text()").getall())
        mw = response.xpath("//*[contains(text(), '分子量：')]/following-sibling::dd/text()").get()
        parent = response.xpath("//div[@class='inner_wrap']/li[last()-1]/a/text()").get()
        img_url = urljoin(self.base_url, response.xpath("//div[@class='autopic']/a/@href").get())
        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "en_name": en_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "parent": parent,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)

