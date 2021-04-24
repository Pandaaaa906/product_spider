from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import SupplierProduct
from product_spider.utils.spider_mixin import BaseSpider


cas_list = [
    '52793-97-2',
    '140-57-8',
    '56039-58-8',
    '205650-65-3',
    '298-02-2',
    '54239-37-1',
    '205-82-3',
    '21593-23-7',
    '26944-48-9',
    '154702-15-5',
    '935-95-5',
    '84467-94-7',
    '139755-85-4',
    '243973-20-8',
]

url_tmpl = 'https://www.guidechem.com/cas/{}.html'


class GuideChemSpider(BaseSpider):
    name = 'guidechem'
    allowed_domains = ['guidechem.com/']
    base_url = 'https://www.guidechem.com/'

    def start_requests(self):
        for cas in cas_list:
            yield Request(url_tmpl.format(cas), meta={'cas': cas})

    def parse(self, response):
        for dd in response.xpath('//dd[@data-id]'):
            d = {
                'platform': self.name,
                'source_id': dd.xpath('./@data-id').get(),
                'vendor': dd.xpath('.//em/a/text()').get(),
                'vendor_origin': dd.xpath('.//span/img[contains(@src, "country")]/@title').get(),
                'vendor_type': dd.xpath('.//span/img[contains(@src, "/vip/")][last()]/@title').get(),
                'en_name': dd.xpath('.//span/a/@title').get(),
                'img_url': dd.xpath('.//dd[@data-id]//td/img/@src').get(),
                'cas': response.meta.get('cas'),

                'prd_url': dd.xpath('.//span/a[@target]/@href').get(),
            }
            yield SupplierProduct(**d)

        next_page = response.xpath('//i[@class="omm"]/following-sibling::a/@href').get()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse)
