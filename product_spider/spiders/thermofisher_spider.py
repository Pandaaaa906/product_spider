import html
import json
import re
import urllib.parse

from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import Rule, CrawlSpider
from product_spider.items import RawData, SupplierProduct, ProductPackage, RawSupplierQuotation
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation


class ThermofisherSpider(CrawlSpider):
    name = "thermofisher"
    start_urls = ["https://www.thermofisher.cn/cn/zh/home/applications-techniques.html", ]
    base_url = "https://www.thermofisher.cn"
    allowed_domains = ['www.thermofisher.cn', 'thermofisher.cn']
    brand = 'thermofisher'
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
    rules = (
        Rule(
            LinkExtractor(allow=r'/order/catalog/product/.+'),
            callback='parse_detail',
            follow=False
        ),
        Rule(
            LinkExtractor(allow=r'/cn/zh/\w+/product/.+'),
            callback='parse_detail2',
            follow=False
        ),
        Rule(
            LinkExtractor(allow=r'/cn/zh/home/'),
            follow=True  # 继续往下爬
        ),
    )

    def parse_brand(self, brand):
        brand = html.unescape(brand).lower()
        if 'thermo' in brand:
            return self.brand
        return brand

    def parse_detail(self, response):
        self.logger.info(f"detail page:{response.url}")
        state_str = response.xpath("//script[contains(text(),'window._PRELOADED_STATE_ =')]/text()").get()
        if not state_str:
            return
        pattern = re.compile(r'window\._PRELOADED_STATE_\s*=\s*(.+);', re.S)
        match = pattern.search(state_str)
        if not match:
            return
        j_str = match.group(1)
        try:
            j_obj: dict = json.loads(j_str)
        except:
            self.logger.warning(f"解析产品数据json失败 json字符串:{j_str}")
            return
        product = j_obj.get('product').get('product')
        parent = None
        if crumbs := product.get('breadCrumbs'):
            parent = crumbs[-1].get('name')
        items = product.get('items')
        prices = j_obj.get('prices', {}).get('prices', [])
        price_data_map = {x.get('requestedCatalogNumber'): x for x in prices}
        for item in items:
            if err := item.get('error'):
                self.logger.warning(f'Not available product, err:{err} url:{response.url}')
                continue
            brand = self.parse_brand(item.get('umbrellaBrand') or self.brand)
            specifications = [{x.get('name'): x.get('value')} for x in item.get('specifications', [])]
            attrs = {'specifications': specifications, }
            img_url = None
            if item.get('images') and (img := item.get('images')[0]):
                img_url = urllib.parse.urljoin(self.base_url, img.get('path'))
            cat_no = item.get("requestedCatalogNumber")
            if not cat_no:
                continue
            prd_url = response.url
            if item.get('productUrl'):
                prd_url = urllib.parse.urljoin(self.base_url, item.get('productUrl'))
            if chs_name := item.get('productTitleV3') or item.get('productTitle'):
                chs_name = html.unescape(chs_name)
            d = {
                "brand": brand,
                "cat_no": cat_no,
                "parent": parent,
                "chs_name": chs_name,
                'prd_url': prd_url,
                'img_url': img_url,
                'info2': item.get('contentsAndStorage'),
                'attrs': json.dumps(attrs, ensure_ascii=False),
            }
            yield RawData(**d)
            ddd = rawdata_to_supplier_product(d, platform=self.brand, vendor=self.brand)
            yield SupplierProduct(**ddd)
            cat_price_data = price_data_map.get(cat_no)

            price, currency = None, None
            if cat_price_data:
                price_data = cat_price_data.get('formattedPrice', {})
                currency = cat_price_data.get('currency') or self.currency
                price = price_data.get('finalPrice', price_data.get("listPrice"))
            sku_differentiators = item.get('skuDifferentiatorsV3')
            pacakge = None
            if sku_differentiators:
                package_id = sku_differentiators[0].get('id')
                if temp := list(filter(lambda x: x.get("id") == package_id, item.get('specifications', []))):
                    pacakge_obj = temp[0]
                    pacakge = pacakge_obj.get("value")
            if not pacakge or not price:
                continue
            dd = {
                "brand": brand,
                "cat_no": d['cat_no'],
                "package": pacakge,
                "cost": price,
                "price": price,
                "currency": currency,
                'attrs': json.dumps(attrs, ensure_ascii=False),
            }
            yield ProductPackage(**dd)
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.brand, vendor=self.brand)
            yield RawSupplierQuotation(**dddd)

    def parse_detail2(self, response):
        state_str = response.xpath("//script[contains(text(),'window._PRELOADED_STATE_ =')]/text()").get()
        if state_str:
            yield from self.parse_detail(response)
            return
        data_str = response.xpath("//script[@id='product-schema-pdp']/text()").get()
        product_data = json.loads(data_str)
        cat_no = product_data.get('sku')
        parent = response.xpath("//ul[contains(@class,'breadcrumb')]/li[position()=last()]/a/text()").get()
        property_xpath = ("//div[@class='product-item']/*[contains(text(),{!r})]"
                          "/parent::div[1]/following-sibling::div[1]/*/text()")
        attrs = {
            'RRID': response.xpath(property_xpath.format('RRID')).get(),
            '内含物': response.xpath(property_xpath.format('内含物')).get(),
            '形式': response.xpath(property_xpath.format('形式')).get(),
            '保存液': response.xpath(property_xpath.format('保存液')).get(),
            '偶联物': response.xpath(property_xpath.format('偶联物')).get(),
            '克隆号': response.xpath(property_xpath.format('克隆号')).get(),
            '宿主/亚型': response.xpath(property_xpath.format('宿主/亚型')).get(),
            '已发表种属': response.xpath(property_xpath.format('已发表种属')).get(),
            '种属反应': response.xpath(property_xpath.format('种属反应')).get(),
        }
        attrs = {k: v.strip() for k, v in attrs.items() if v is not None}
        d = {
            "brand": self.brand,
            "cat_no": cat_no,
            "parent": parent,
            "chs_name": response.xpath("//h2[@class='product-name']/text()").get(),
            'prd_url': response.url,
            'purity': response.xpath(property_xpath.format('浓度')).get(),
            'info2': response.xpath(property_xpath.format('保存条件')).get(),
            'shipping_info': response.xpath(property_xpath.format('运输条件')).get(),
            'img_url': response.xpath("//img[@id='media-image']/@src").get(),
            'attrs': json.dumps(attrs, ensure_ascii=False),
        }
        yield RawData(**d)
