import json
import re
from urllib.parse import urljoin, urlencode

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class ChemImpexSpider(BaseSpider):
    name = "chemimpex"
    base_url = "https://www.chemimpex.com/"
    start_urls = ['https://www.chemimpex.com/products/catalog', ]

    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
    }

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//div[@class="count-box"]/a[translate(normalize-space(text())," ","")!="0"]')
        for a in a_nodes:
            cat_url = strip(a.xpath('./@href').get())
            if not cat_url:
                continue
            parent = strip(a.xpath('./text()').get())
            yield Request(urljoin(self.base_url, cat_url), callback=self.parse, meta={'parent': parent})

        prd_urls = response.xpath('//h3[@class="prodname"]/a/@href').getall()
        for prd_url in prd_urls:
            yield Request(urljoin(self.base_url, prd_url), callback=self.parse_detail,
                          meta={'parent': response.meta.get('parent')}
                          )

        next_page = strip(response.xpath(
            '//span[@class="selectedpage"]/../following-sibling::li/a[not(parent::li/span)]/text()'
        ).get())
        if next_page:
            url, *_ = response.url.split('?')
            params = urlencode({
                'custguid': '',
                'custclsid': '',
                'pn': next_page,
            })
            yield Request(f'{url}?{params}', callback=self.parse, meta={'parent': response.meta.get('parent')})

    def parse_detail(self, response):
        tmp = '//span[contains(text(), {!r})]/following-sibling::span//text()'
        d = {
            'brand': self.name,
            'parent': response.meta.get('parent'),
            'cat_no': response.xpath(tmp.format("Catalog Number:")).get(),
            'en_name': strip(''.join(response.xpath('//h1[@itemprop="name"]//text()[not(parent::span)]').getall())),
            'purity': strip(response.xpath('//h1[@itemprop="name"]/span[@style]/text()').get()),
            'mf': strip(''.join(response.xpath(tmp.format('Molecular Formula:')).getall())),
            'mw': strip(response.xpath(tmp.format('Molecular Weight:')).get()),
            'cas': strip(response.xpath(tmp.format('CAS No:')).get()),
            'appearance': strip(response.xpath(tmp.format('Appearance:')).get()),
            'info1': strip(';'.join(response.xpath(tmp.format('Synonyms:')).getall())),
            'info2': strip(response.xpath(tmp.format('Storage Temp:')).get()),
            'img_url': strip(response.xpath('//div[@id="catalog_content"]/img/@src').get()),
            'prd_url': response.url,
        }
        m = re.search(r'skuWidgets\.push\(({.+\})\);', response.text)
        yield RawData(**d)

        j_obj = json.loads(m.group(1))
        params = [j_obj.get(f'param{i}', '') for i in range(1, 7)]
        url = 'https://www.chemimpex.com/Widgets-product/gethtml_skulist/{}/{}/{}/{}/{}/{}'.format(*params)
        yield Request(url, callback=self.parse_table, meta={'prd_info': d})

    def parse_table(self, response):
        prd = response.meta.get("prd_info", {})
        rows = response.xpath('//tr[@class="trSkuList"]')
        for row in rows:
            stock_info = strip(row.xpath('.//span[contains(@class, "stockstatus")]/text()').get())
            dd = {
                'brand': self.name,
                'cat_no': prd.get("cat_no"),
                'package': strip(row.xpath('./td[@class="skusize"]/text()').get()),
                'cost': strip(row.xpath('.//span[@class="price"]/text()').get()),
                'currency': "USD",
                'stock_num': 1 if stock_info == 'YES' else 0,
                'delivery_time': 'in-stock' if stock_info == 'YES' else stock_info
            }
            yield ProductPackage(**dd)
