from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class SplendidLabSpider(BaseSpider):
    name = 'splendidlab'
    base_url = 'http://splendidlab.com/'
    start_urls = ['http://splendidlab.com/products.php', ]

    def parse(self, response, **kwargs):
        prds = response.xpath('//div[@class="product-box"]')
        tmp = './/div[@class="label" and text()={!r}]/following-sibling::div/text()'
        for prd in prds:
            img_rel = prd.xpath('.//div[@class="product-img"]/img/@src').get()
            d = {
                "brand": self.name,
                "parent": None,
                "cat_no": prd.xpath(tmp.format("Catalog Number")).get(),
                "en_name": prd.xpath('.//div[@class="product-text"]/h3/text()').get('').strip() or None,
                "cas": prd.xpath(tmp.format("CAS Number")).get('').strip() or None,
                "mf": prd.xpath(tmp.format("Molecular Formula")).get('').strip() or None,
                "mw": prd.xpath(tmp.format("Molecular Weight")).get('').strip() or None,
                "img_url": img_rel and urljoin(self.base_url, img_rel),
                "info1": prd.xpath(tmp.format("Synonyms ")).get('').strip() or None,
                "prd_url": response.request.url,
            }
            yield RawData(**d)

        ref = response.xpath('//a[text()="Next"]/@href').get()
        if ref:
            yield Request(urljoin(self.base_url, ref), callback=self.parse)
