import re
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class ItomSpider(BaseSpider):
    name = "itom"
    start_urls = [
        "https://www.ltom.com/products/1209885185940279296.html"
    ]

    def parse(self, response, **kwargs):
        urls = response.xpath('//div[@class="cbox-1 p_loopitem"]//a/@href').getall()
        for url in urls:
            yield Request(url=urljoin(response.url, url), callback=self.parse_detail)
        next_page = response.xpath('//div[@class="page_con"]/a[contains(@class, "current")]/following-sibling::a[contains(@class, "page_num")]/@href').get()
        if next_page:
            yield Request(url=urljoin(response.url, next_page), callback=self.parse)

    def parse_detail(self, response):
        raw_cas = response.xpath('//div[contains(@class, "s_title") and contains(text(), "CAS")]/text()').get()
        cas = None
        if raw_cas:
            cas = (m := re.search(r'\d{2,}-\d{2}-\d\b', raw_cas)) and m.group(0)
        parents = response.xpath('//div[p[contains(text(), "所属分类")]]/following-sibling::div//p/text()').getall()
        info = '\n'.join(filter(bool, map(strip, response.xpath('//div[div/p[contains(text(), "产品详情")]]/following-sibling::div//text()').getall())))
        product_id = (m := re.search(r'(\d+)\.html', response.url)) and m.group(1)
        img_url = response.xpath('//div[@class="small-img"]//img/@lazy').get()
        if not img_url:
            self.logger.info('no image')
        d = {
            "brand": self.name,
            "cat_no": product_id,
            "parent": ';'.join(map(strip, parents)),
            "en_name": response.xpath('//h1[contains(@class, "s_subtitle")]/text()').get(),
            "cas": cas,
            "prd_url": response.url,
            "img_url": img_url and urljoin(response.url, img_url),
        }
        if info:
            d['smiles'] = (m := re.search(r'Smiles Code[;:]\s*(\S+)', info)) and m.group(1)
            d['purity'] = (m := re.search(r'(纯度|含量)[;:]\s*([^\n]+)', info)) and m.group(2)
            d['mf'] = (m := re.search(r'分子式[;:]\s*(\S+)', info)) and m.group(1)
            d['mw'] = (m := re.search(r'分子量[;:]\s*(\S+)', info)) and m.group(1)
            d['info2'] = (m := re.search(r'存储条件[;:]\s*([^\n]+)', info)) and m.group(1)
            d['mdl'] = (m := re.search(r'MDL ?号?[;:]\s*([^\n]+)', info)) and m.group(1)

            d['chs_name'] = (m := re.search(r'中文名称[;:]\s*([^\n]+)', info)) and m.group(1)
            en_name = (m := re.search(r'英文名称[;:]\s*([^\n]+)', info)) and m.group(1)
            if en_name:
                d['en_name'] = en_name
            pass
        yield RawData(**d)
