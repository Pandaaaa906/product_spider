from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class PaiTaiSpider(BaseSpider):
    name = "paitai"
    brand = '湃肽'
    base_url = "https://www.peptide-china.com/"
    start_urls = ['https://www.peptide-china.com/product/index.php?class2=119&page=1', ]

    def parse(self, response):
        urls = response.xpath('//div[@class="less-page-content"]//h4/a/@href').getall()
        for url in urls:
            yield Request(url, callback=self.parse_detail)

        next_page = response.xpath('//a[@class="NextA"]/@href').get()
        if next_page:
            yield Request(next_page, callback=self.parse)

    def parse_detail(self, response):
        tmp = '//td[contains(./span/text(), {!r})]/following-sibling::td//span//text()'
        tmp2 = '//td[contains(./span/text(), {!r})]/following-sibling::td/p[{}]/span/text()'
        en_name = strip(response.xpath(tmp2.format("Product Name", 1)).get()) or \
                  strip(response.xpath(tmp.format("Product Name")).get())
        d = {
            'brand': self.brand,
            'cat_no': en_name,
            'en_name': en_name,
            'chs_name': strip(response.xpath(tmp2.format("Product Name", 2)).get()),
            'cas': strip(response.xpath(tmp.format("Cas No.")).get()),
            'info1': strip(response.xpath(tmp.format("Sequence")).get()),
            'mf': strip(''.join(response.xpath(tmp.format("Molecular Formula")).getall())),
            'mw': strip(response.xpath(tmp.format("Molar Mass")).get()),
            'purity': strip(''.join(response.xpath(tmp.format("Purity")).getall())),
            'info2': strip(response.xpath(tmp.format("Storage Temperature")).get()),

            'img_url': response.xpath('//div[contains(@class, "slick-slide")][1]/a/img/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
