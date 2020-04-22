from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import HbErmItem
from product_spider.utils.spider_mixin import BaseSpider


class HbErmSpider(BaseSpider):
    name = "hberm_prds"
    base_url = 'http://www.hb-erm.com/'
    start_urls = [
        'http://www.hb-erm.com/index.php?m=goods&a=search',
    ]

    def parse(self, response):
        rel_urls = response.xpath('//td/a[@target]/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse)

        next_page = response.xpath('//span[@class="current"]/following-sibling::a[not(@data)]/@href').get()
        if not next_page:
            return
        yield Request(urljoin(self.base_url, next_page), callback=self.parse)

    def detail_parse(self, response):
        d = {
            'cat_no': response.xpath('//div[contains(text(), "国家标准样品编号：")]/following-sibling::div/text()').get(),
            'cn_name': response.xpath('//p[@class="list-title"]/text()').get(),
            'batch': response.xpath('//div[contains(text(), "批号:")]/following-sibling::div/text()').get(),
            'manufacture': response.xpath('//div[contains(text(), "生产商：")]/following-sibling::div/text()').get(),
            'expire_date': response.xpath('//div[contains(text(), "有效期：")]/following-sibling::div/text()').get(),
            'package': response.xpath('//div[contains(text(), "【规格】：")]/following-sibling::div/text()').get(),
            'sale_info': response.xpath('//div[contains(text(), "销售说明：")]/following-sibling::div/text()').get(),
            'usage': response.xpath('//div[contains(text(), "商品用途：")]/following-sibling::div/text()').get(),
            'components': response.xpath('//div[contains(text(), "商品组分：")]/following-sibling::div/text()').get(),
            'concentrate': response.xpath('//div[contains(text(), "浓度：")]/following-sibling::div/text()').get(),

            'price': response.xpath('//p[@class="sj"]/label/text()').get(),
            'stock_info': response.xpath('//p[@class="kucun"]/label/text()').get(),
        }
        yield HbErmItem(**d)
