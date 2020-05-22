from string import ascii_uppercase
from urllib.parse import urljoin, splitquery, parse_qsl, urlencode

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class TLCSpider(BaseSpider):
    name = "tlc_prds"
    base_url = "http://tlcstandards.com/"
    start_urls = map(lambda x: "http://tlcstandards.com/ProductsRS.aspx?type={}&cpage=1".format(x), ascii_uppercase)
    x_template = './child::br[contains(following-sibling::text(),"{0}")]/following-sibling::font[1]/text()'

    custom_settings = {
        'CONCURRENT_REQUESTS': 32,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 64,
        'CONCURRENT_REQUESTS_PER_IP': 64,
    }

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="information"]/a/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse)
        next_page = response.xpath('//a[@class="nextPage" and text()="▶"]').extract_first()
        if next_page:
            url, q = splitquery(response.url)
            d = dict(parse_qsl(q))
            d['cpage'] = int(d.get('cpage', 0)) + 1
            q = urlencode(d)
            yield Request('?'.join((url, q)), callback=self.parse)

    @staticmethod
    def extract_value(response, title):
        ret = response.xpath(f'//p[text()={title!r}]/../following-sibling::td/p/descendant-or-self::text()').extract()
        return "".join(ret) or None

    def detail_parse(self, response):
        img_src = response.xpath('//section[@class="page"][1]//img/@src').extract_first()
        d = {
            'en_name': self.extract_value(response, "Compound Name:"),
            'cat_no': self.extract_value(response, "Catalogue Number:"),
            'img_url': img_src and urljoin(self.base_url, img_src),
            'info1': self.extract_value(response, "Synonyms:"),
            'cas': self.extract_value(response, "CAS#:"),
            'mw': self.extract_value(response, "Molecular Weight:"),
            'mf': self.extract_value(response, "Molecular Formula:"),
            'parent': response.xpath('//section[@class="page"][1]//h3[@class="title--product"]/text()').extract_first(
                default="").title() or None,
            'brand': 'TLC',
            'prd_url': response.request.url,
            'stock_info': response.xpath('//span[@class="status"]/text()').extract_first("").strip().title() or None,
        }
        yield RawData(**d)
