from os import getenv
from urllib.parse import urljoin, urlencode

from more_itertools import first
from requests_html import HTMLSession
from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class ArcSpider(BaseSpider):
    name = "arc"
    base_url = "https://www.arcincusa.com/"
    start_urls = ["https://www.arcincusa.com/", ]
    cookies = {}

    def login(self, username, password):
        s = HTMLSession()
        r = s.get(self.base_url)
        btl_return = first(r.html.xpath('//input[@id="btl-return"]/@value'))
        secret_name = first(r.html.xpath('//input[@id="btl-return"]/following-sibling::input/@name'))
        d = {
            'bttask': 'login',
            'username': username,
            'passwd': password,
            secret_name: 1,
            'return': btl_return,
        }
        _ = s.post(self.base_url, data=d)
        self.cookies = dict(s.cookies)

    def start_requests(self):
        username = getenv('ARC_USERNAME')
        password = getenv('ARC_PASSWORD')
        if username and password:
            self.login(username, password)
        for url in self.start_urls:
            yield Request(url, callback=self.parse, cookies=self.cookies)

    def parse(self, response):
        rel_urls = response.xpath('//div[@id="our_products"]//li/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(
                urljoin(response.url, rel_url), callback=self.parse_list,
                cookies=self.cookies
            )

    def parse_list(self, response):
        rows = response.xpath('//div[@class="spacer"]')
        parent = response.meta.get('parent') or response.xpath('//div[@align]/p/text()').get()
        parent_id = response.meta.get('parent_id') or response.xpath(f'//option[@data-name={parent!r}]/@value').get()
        first_comment = response.meta.get('first_comment', response.xpath('//div[@class="postedComment"]/@id').get())
        last_comment = response.xpath('//div[@class="postedComment"][last()]/@id').get()

        for row in rows:
            cat_no = row.xpath('./div/a/text()').get()
            rel_url = row.xpath('./div/a/@href').get()
            yield Request(
                urljoin(response.url, rel_url), callback=self.parse_detail,
                meta={'parent': parent, 'cat_no': cat_no},
                cookies=self.cookies
            )

        if len(rows) > 0:
            d = self.make_form(parent_id, first_comment, last_comment)
            url = f'{urljoin(response.url, "index.php")}?{urlencode(d)}'
            yield Request(
                url, callback=self.parse_list,
                meta={'parent': parent, 'parent_id': parent_id, 'first_comment': first_comment},
                cookies=self.cookies
            )

    def make_form(self, category_id, first_comment, last_comment):
        return {
            'option': 'com_virtuemart',
            'view': 'categoryloadmore',
            'tmpl': 'component_nostyle',
            'virtuemart_category_id': str(category_id),
            'lastComment': str(last_comment),
            'firstComment': str(first_comment),
        }

    def parse_detail(self, response):
        tmp = '//div[contains(text(), {!r})]/following-sibling::div//text()'
        # sku = response.xpath('//span[@class="product_detail_sku_mobile_detail"]/text()').get()
        solvent = strip(response.xpath(tmp.format("Solvent:")).get())
        concentration = strip(response.xpath(tmp.format("Concentration:")).get())
        cas = strip(response.xpath(tmp.format("CAS Number:")).get())
        d = {
            'brand': 'ARC',
            'parent': response.meta.get('parent'),
            'cat_no': response.meta.get('cat_no'),
            'en_name': response.xpath('//p[@itemprop="name"]/text()').get(),
            'cas': None if cas == 'Not available' else cas,
            'mf': strip(response.xpath(tmp.format("Formula:")).get()),
            'mw': strip(response.xpath(tmp.format("Molecular Weight:")).get()),
            'info1': strip(response.xpath(tmp.format("Synonym:")).get()),
            'info3': solvent if concentration == 'Not available' else f'{solvent}; {concentration}',
            'info4': response.xpath('//span[@class="PricediscountedPriceWithoutTax"]/text()').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
