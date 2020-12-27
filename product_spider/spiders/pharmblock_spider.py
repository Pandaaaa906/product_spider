import json
from urllib.parse import urlencode, urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.maketrans import formular_trans
from product_spider.utils.spider_mixin import BaseSpider


class PharmBlockSpider(BaseSpider):
    name = "pharmblock"
    base_url = "https://product.pharmablock.com/"
    brand = '南京药石'

    def make_url(self, page='1', category_id=''):
        url = 'https://product.pharmablock.com/Products/GetMultiProductList?'
        d = {
            'limit': '20',
            'page': page,
            'DataType': '',
            'CategoryId': category_id,
            'Source': '3',
            'Content': '',
            'ProductIDArr': '',
        }
        return f'{url}{urlencode(d)}'

    def start_requests(self):
        yield Request(
            url='https://product.pharmablock.com/Products/GetFunctionCategoryMenus',
            method='POST',
            callback=self.parse
        )

    def _iter_end_category(self, obj):
        for category in obj:
            children = category.get('childList', [])
            if children:
                yield from children
            else:
                yield category

    def parse(self, response):
        j_obj = json.loads(response.text)
        for category in self._iter_end_category(j_obj):
            category_id = category.get('CategoryId')
            return Request(
                self.make_url(category_id=category_id), callback=self.parse_list,
                meta={'page': '2', 'category_id': category_id}
            )

    def parse_list(self, response):
        j_obj = json.loads(response.text)
        page = response.meta.get('page')
        category_id = response.meta.get('category_id')
        if not j_obj.get('data'):
            return
        for row in j_obj.get('data', []):
            cat_no = row.get('ProductCode')
            yield Request(f'https://product.pharmablock.com/product/{cat_no}.html?IsUnique=true',
                          callback=self.parse_detail)
        yield Request(
            self.make_url(category_id=category_id, page=page),
            callback=self.parse_list, meta={'page': str(int(page)+1), 'category_id': category_id}
        )

    def parse_detail(self, response):
        tmp = '//th[contains(text(), {!r})]/following-sibling::td/text()'
        rel_img = response.xpath('//div[@class="pic"]/img/@src').get()
        cat_no = response.xpath('//div/span[@style]/text()').get()
        d = {
            'brand': self.brand,
            'cat_no': cat_no,
            'en_name': response.xpath('//div/span/@data-nameen').get(),
            'cas': response.xpath(tmp.format("CAS:")).get(),
            'mdl': response.xpath(tmp.format("MDL:")).get(),
            'mf': formular_trans(strip(response.xpath(tmp.format("分子式:")).get())),
            'mw': response.xpath(tmp.format("分子量:")).get(),
            'smiles': response.xpath(tmp.format("SMILES code:")).get(),
            'purity': response.xpath(tmp.format("化学纯度:")).get(),

            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }
        yield RawData(**d)

        rows = response.xpath('//div[@class="table-1"]//tbody/tr')
        for row in rows:
            package = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': row.xpath('./td[1]/text()').get(),
                'price': strip(row.xpath('./td[2]/text()').get()),
                'stock_num': row.xpath('./td[5]/text()').get(),
            }
            yield ProductPackage(**package)
