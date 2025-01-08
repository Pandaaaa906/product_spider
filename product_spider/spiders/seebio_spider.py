import json
from typing import Optional, Union

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip, clean_dict
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


d_brand = {
    "seebio": "seebio",
    "西宝": "seebio",
}


def map_brand(_brand: Union[str, None]) -> Optional[str]:
    if not _brand:
        return
    _brand = _brand.lower()
    return d_brand.get(_brand, _brand)


class SeebioSpider(BaseSpider):
    name = "seebio"
    brand = "seebio"
    base_url = "http://www.seebio.cn/"
    start_urls = ["http://www.seebio.cn/product_category.php?id=1", ]

    custom_settings = {
        'RETRY_HTTP_CODES': [503, 504, 502],
        'RETRY_TIMES': 10,
    }

    # def is_proxy_invalid(self, request, response):
    #     proxy = request.meta.get('proxy')
    #     is_detected = False
    #     if response.status in {502, 503, 403, 504}:
    #         is_detected = True
    #     if is_detected:
    #         self.logger.warning(f'status code:{response.status}, {request.url}, using proxy {proxy}')
    #         return True
    #     return False

    def parse(self, response, **kwargs):
        hrefs = response.xpath(
            '//li[contains(@class,"drop")]//a[contains(@href,"product_category.php")]/@href'
        ).getall()
        for href in hrefs:
            yield Request(href, callback=self.parse_list)

    def parse_list(self, response):
        detail_hrefs = response.xpath('//h2[@class="entry-title post-title"]/a/@href').getall()
        for href in detail_hrefs:
            yield Request(href, callback=self.parse_detail)

        next_page = response.xpath('//div[@id="pages"]/div/a[contains(text(),"下一页")]/@href').get()
        last_page = response.xpath('//div[@id="pages"]/div/a[contains(text(),"最后一页")]/@href').get()
        if next_page and next_page != last_page:
            yield Request(next_page, callback=self.parse_list)

    def parse_detail(self, response):
        tmp = '//div[@class="product-info"]/ul/li[contains(text(),{!r})]/text()'
        tmp2 = '//table[@id="baseinfo"]//tr/td[contains(text(),{!r})]/following-sibling::*[1]//text()'

        parent = strip(response.xpath('//div[@class="col-md-9 col-sm-8 location"]/span/a[last()]/text()').get())
        if parent in {'首页', '产品中心'}:
            parent = None

        cat_no = strip(response.xpath(tmp.format("编码")).get(), "").strip("编码：")
        introduction = strip(response.xpath(tmp.format("简介")).get("").strip("简介："))

        if not (en_name := response.xpath(tmp2.format("英文名")).get()):
            # 如果基本信息中没有英文名 尝试从上面的别名获取
            if _ := strip(response.xpath(tmp.format("别名")).get(), "").strip("别名："):
                if _[0].isalnum():
                    en_name = _

        table_heads = response.xpath('//table[@id="packlist"]/thead/tr/th/text()').getall()
        brand_index = table_heads.index("品牌")
        package_index = table_heads.index("包装规格")
        stock_index = table_heads.index("库存")
        price_index = table_heads.index("价格")

        if not (brand := response.xpath(tmp2.format("品牌")).get()):
            brand = response.xpath(f'//table[@id="packlist"]//tr/td[{brand_index+1}]/text()').get()
        brand = map_brand(brand)

        if not (img_url := response.xpath('//div[@id="product"]//div[@class="product-img"]//a/@href').get()):
            img_url = response.xpath('//div[@class="swiper-slide"]/img/@src').get()

        attrs = {
            'product_info': introduction,
        }
        d = {
            'brand': brand,
            'cat_no': cat_no,
            'chs_name': response.xpath('//div[@class="product-info"]/h1/text()').get(),
            'en_name': en_name,
            'cas': response.xpath(tmp2.format("CAS")).get(),
            'parent': parent,
            'purity': strip(response.xpath(tmp.format("级别")).get(), "").strip("级别："),
            'img_url': img_url,
            'prd_url': response.url,
            'attrs': json.dumps(clean_dict(attrs), ensure_ascii=False),
        }

        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        yield SupplierProduct(**ddd)
        yield RawData(**d)

        package_rows = response.xpath('//table[@id="packlist"]/tbody/tr')
        for row in package_rows:
            if not (tds := row.xpath('./td')) or len(tds) <= max(stock_index, price_index, package_index):
                self.logger.warning(f"规格信息异常 prd_url:{response.url}")
                continue
            stock_num = tds[stock_index].xpath("./text()").get()
            package = tds[package_index].xpath("./text()").get()
            price = parse_cost(tds[price_index].xpath("./em/text()").get())
            if price == '面议':
                price = None
            dd = {
                'brand': brand,
                'cat_no': cat_no,
                'package': package,
                'cost': price,
                'price': price,
                'currency': 'RMB',
                'stock_num': stock_num,
            }
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
            yield ProductPackage(**dd)
            if price:
                yield RawSupplierQuotation(**dddd)

