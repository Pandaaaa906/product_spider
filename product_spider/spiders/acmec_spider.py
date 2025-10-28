import json

from scrapy import Request, FormRequest

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class AcmecSpider(BaseSpider):
    name = "acmec"
    start_urls = ["https://www.acmec-e.com/", ]
    base_url = "https://www.acmec-e.com/"
    brand = 'acmec'
    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'RETRY_ENABLED': True,
        'RETRY_HTTP_CODES': [403],
        'RETRY_TIMES': 10,
        'RETRY_BACKOFF_BASE': 2,
        'RETRY_BACKOFF_MAX': 60,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }
    currency = 'RMB'

    def parse(self, response, **kwargs):
        def extract_node(_li):
            if children := _li.xpath("./ul/li"):
                for sub_li in children:
                    yield from extract_node(sub_li)
            else:
                _url = _li.xpath("./a/@href").get()
                parent = _li.xpath("./a/text()").get()
                _url = get_url(response.url, _url)
                if _url:
                    yield Request(_url, callback=self.parse_list, meta={'parent': parent})

        li_list = response.xpath("//li[@role='presentation']/ul/li")
        for li in li_list:
            yield from extract_node(li)

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_urls = response.xpath("//td/a[contains(@href,'product/')]/@href").getall()
        if not product_urls:
            return
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, callback=self.parse_detail, meta=response.meta)

        if next_url := response.xpath(
                '//ul[contains(@class,"pagination")]/li[@class="active"]/following-sibling::li[1]/a/@href').get():
            next_url = get_url(response.url, next_url)
            if next_url:
                yield Request(next_url, callback=self.parse_list, meta=response.meta)

    def extract_property(self, response, keyword: str, base_xpath: str = None):
        base_xpath = base_xpath or '//'
        temp = response.xpath(f"{base_xpath}*[contains(text(),'{keyword}')]/following-sibling::*[1]/text()").get()
        return temp

    def parse_detail(self, response):
        if img_url := response.xpath('//img[@id="imgshows"]/@src').get():
            img_url = get_url(response.url, img_url)

        if mf := self.extract_property(response, '分子式：'):
            mf = formula_trans(mf)
        if brand := self.extract_property(response, '品牌：'):
            brand = brand.lower()

        cat_no = self.extract_property(response, '产品编号：')
        if not cat_no:
            self.logger.info(f"No cat no found, url:{response.url}")
            return
        purity_temp = response.xpath("//div[@class='kj_propduct_name']/h1/text()").get()
        purity = None
        if purity_temp:
            temp = purity_temp.split(',')
            for item in temp:
                if '%' in item:
                    purity = item
        d = {
            "brand": brand,
            "parent": response.meta.get('parent'),
            "cat_no": cat_no,
            "en_name": response.xpath("//div[@class='kj_propduct_name_h2']/h2/text()").get(),
            "chs_name": response.xpath("//div[@class='kj_propduct_name']/h1/*/text()").get(),
            "purity": purity,
            "img_url": img_url,
            "mf": mf,
            "mw": self.extract_property(response, '分子量：'),
            "mdl": self.extract_property(response, ' MDL：'),
            "cas": self.extract_property(response, 'CAS No.：'),
            'prd_url': response.url,
            "info2": self.extract_property(response, '保存条件：'),
        }
        yield RawData(**d)

        product_id = response.xpath("//h1/span[@class='inquiry_item']/@pdid").get()
        package_req = {
            'pd_id': product_id
        }
        yield FormRequest('https://www.acmec-e.com/index.aspx?a=ajaxpro_ajax&method=LoadGoods', formdata=package_req,
                          callback=self.handle_package_req, meta={'d': d})

    def handle_package_req(self, response):
        j_obj: dict = response.json()
        try:
            j_obj = json.loads(j_obj.get('ObjResult'))
            packages = list(j_obj.values())[0]
        except json.decoder.JSONDecodeError:
            return
        d = response.meta['d']
        for item in packages:
            inventories = item.get('Inventores')
            if not inventories:
                return
            price = inventories[0].get('Price')
            stock_num = sum([x.get('Amount', 0) for x in inventories])
            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": f'{item.get("Conv")}{item.get("Measure")}',
                "cost": price,
                "price": price,
                "stock_num": stock_num,
                "currency": self.currency,
            }
            yield ProductPackage(**dd)
