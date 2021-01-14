import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class ChromaDexSpider(BaseSpider):
    name = "chromadex"
    start_urls = (f"https://standards.chromadex.com/search?type=product&q={x}" for x in ("ASB", "KIT"))
    base_url = "https://standards.chromadex.com/"
    brand = "ChromaDex"

    def parse(self, response):
        rel_urls = response.xpath('//h5[@class="sub_title"]/a/@href').getall()
        for url in rel_urls:
            yield Request(urljoin(self.base_url, url), callback=self.detail_parse)
        next_url = response.xpath('//span[@class="next"]/a/@href').get()
        if next_url:
            yield Request(urljoin(self.base_url, next_url), callback=self.parse)

    @staticmethod
    def extract_value(response, title):
        ret = response.xpath(f'//p[contains(text(), {title!r})]/text()').get()
        return ret and ret.replace(title, '').strip() or None

    def detail_parse(self, response):
        cat_no_unit = response.xpath('//span[@itemprop="sku"]/text()').get("")
        m = re.match(r'[A-Z]{3}-\d+', cat_no_unit)
        cat_no = m.group(0) if m else cat_no_unit
        rel_img = response.xpath('//img[@class="zoomImg"]/@src').get()
        full_name = response.xpath('//h1[@itemprop="name"][1]/text()').get("").title()
        tmp_full_name = response.xpath('//div[@itemprop="description"]/text()').get("").title()
        if '-' in full_name:
            en_name, package = full_name.rsplit('-', 1)
        elif '-' in tmp_full_name:
            en_name, package = tmp_full_name.rsplit('-', 1)
        else:
            en_name, package = full_name, 'kit'

        d = {
            "brand": self.brand,
            "parent": self.extract_value(response, "Chemical Family: "),
            "cat_no": cat_no,
            "en_name": strip(en_name),
            "cas": self.extract_value(response, "CAS: "),
            "mf": self.extract_value(response, "Chemical Formula: "),
            "mw": self.extract_value(response, "Formula Weight: "),
            "info2": self.extract_value(response, "Long Term Storage: "),
            "appearance": self.extract_value(response, "Appearance: "),
            "purity": self.extract_value(response, "Purity: "),

            'img_url': rel_img and urljoin(self.base_url, rel_img),
            "prd_url": response.url,
        }
        yield RawData(**d)

        stock_num = response.xpath('//div[@class="items_left"]//em/text()').get()
        package = strip(package)
        dd = {
            'brand': self.brand,
            'cat_no_unit': cat_no_unit,
            'cat_no': cat_no,
            'package': package and package.lower(),
            'price': response.xpath('//span[@itemprop="price"]/@content').get(),
            'currency': 'USD',
            'stock_num': stock_num and first(re.findall(r'\d+', stock_num), None),
        }
        yield ProductPackage(**dd)
