from urllib.parse import urljoin, urlencode

from scrapy import Request, FormRequest

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider

IGNORE_BRANDS = {
    'cerillian'
}


class SigmaSpider(BaseSpider):
    name = "sigma"
    start_urls = ["https://www.sigmaaldrich.com/catalog/search?&interface=All_ZH&N=0+9634086&mode=match%20partialmax&lang=zh&region=CN&focus=product", ]
    base_url = "https://www.sigmaaldrich.com/"

    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                          'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
            'Accept-Encoding': 'gzip, deflate, br', 'Accept': '*/*', 'Connection': 'keep-alive',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        },
    }

    def parse(self, response):
        rel_urls = response.xpath('//li[@class="productNumberValue"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

        next_page = response.xpath('//li[@class="currentPage"]/following-sibling::li/a/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse)

    def parse_detail(self, response):
        brand = strip(response.xpath('//input[@id="brand"]/@value').get())
        brand = brand and brand.lower()
        if brand in IGNORE_BRANDS:
            return
        cat_no = strip(response.xpath('//strong[@itemprop="productID"]/text()').get())
        tmp = '//p[contains(text(), {!r})]/span//text()'
        tmp2 = '//td[contains(text(),{!r})]/following-sibling::td//text()[parent::a[not(@id="relatedCategoryLink")]]'
        rel_img = response.xpath('//div[@class="productMedia"]//img/@src').get()
        d = {
            'brand': brand or self.name,
            'cat_no': cat_no,
            'en_name': strip(''.join(response.xpath('//h1[@itemprop="name"]//text()').getall())),
            'cas': strip(''.join(response.xpath(tmp.format("CAS")).getall())),
            'mf': strip(''.join(response.xpath(tmp.format("Formula")).getall())),
            'mw': strip(''.join(response.xpath(tmp.format("Molecular Weight")).getall())),
            'mdl': strip(''.join(response.xpath(tmp.format("MDL number")).getall())),
            'parent': strip(''.join(response.xpath(tmp2.format("Related Categories")).getall())) or None,
            'grade': strip(''.join(response.xpath(tmp2.format("grade")).getall())) or None,
            'info5': strip(''.join(response.xpath(tmp2.format("product line")).getall())) or None,
            'info2': strip(''.join(response.xpath(tmp2.format("storage temp.")).getall())) or None,
            'purity': strip(''.join(response.xpath(tmp2.format("assay")).getall())) or None,
            'smiles': strip(''.join(response.xpath(tmp2.format("SMILES string")).getall())) or None,

            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }
        yield RawData(**d)

        # data = {
        #     'productNumber': cat_no,
        #     'brandKey': brand,
        #     'divId': 'pricingContainerMessage',
        #     'isRollup': '0'
        # }
    #     yield FormRequest(
    #         f'https://www.sigmaaldrich.com/catalog/PricingAvailability.do?{urlencode(data)}',
    #         formdata={'loadFor': 'PRD_RS'},
    #         callback=self.parse_package, meta={'prd': d},
    #         headers={'X-Requested-With': 'XMLHttpRequest'}
    #     )
    #
    # def parse_package(self, response):
    #     product = response.meta.get('prd')
    #     rows = response.xpath('//tr[@class="available"]')
    #     for row in rows:
    #         dd = {
    #             'brand': product.get('brand'),
    #             'cat_no': product.get('cat_no'),
    #         }
    #         pass
    #         #yield ProductPackage(**dd)
    #     pass
