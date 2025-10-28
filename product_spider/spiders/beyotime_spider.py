from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url, extract_adjacent_property
from product_spider.utils.spider_mixin import BaseSpider


class BeyotimeSpider(BaseSpider):
    name = "beyotime"
    start_urls = ["https://www.beyotime.com/", ]
    base_url = "https://www.beyotime.com/"
    brand = 'beyotime'
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
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
        rel_urls = response.xpath("//div[@class='dorpdown']//dl/dd/a/@href").getall()
        for rel_url in rel_urls:
            if url := get_url(response.url, rel_url):
                yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_urls = response.xpath("//table[@class='cplist']//td/a[contains(@href,'product/')]/@href").getall()
        if not product_urls:
            return
        parent = response.xpath("//div/label[@class='lcodenav' and position()=last()]/text()").get()
        meta = {
            'parent': parent
        }
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, callback=self.parse_detail, meta=meta)

        # Pagination not found
        # if next_url := response.xpath(
        #         '//ul[contains(@class,"pagination")]/li[@class="active"]/following-sibling::li[1]/a/@href').get():
        #     next_url = get_url(response.url, next_url)
        #     if next_url:
        #         yield Request(next_url, callback=self.parse_list, meta=meta)

    def extract_property(self, response, keyword: str, base_xpath: str = None):
        base_xpath = base_xpath or '//'
        temp = response.xpath(f"{base_xpath}*[contains(text(),'{keyword}')]/following-sibling::p[1]/text()").get()
        return temp

    def parse_detail(self, response):
        if img_url := response.xpath('//a[@id="sku_mainimage_a"]/@href').get():
            img_url = get_url(response.url, img_url)

        cat_no = response.xpath("//*[@id='sku_cpcode']/text()").get()
        if not cat_no:
            self.logger.info(f"No cat no found, url:{response.url}")
            return
        cat_no = cat_no.split('-')[0]
        d = {
            "brand": self.brand,
            "parent": response.meta.get('parent'),
            "cat_no": cat_no,
            "chs_name": response.xpath("//a[@id='sku_cpname']/text()").get(),
            "img_url": img_url,
            "mf": extract_adjacent_property(response, '化学式', sub_text=True),
            "mw": extract_adjacent_property(response, '分子量', base_xpath='//td'),
            "cas": extract_adjacent_property(response, 'CAS号', base_xpath='//td'),
            'prd_url': response.url,
            "info2": response.xpath(f"//*[contains(text(),'保存条件：')]/following-sibling::p[1]/text()").get(),
        }
        yield RawData(**d)
        headers = response.xpath("//tr[@class='cplisttitle']/td/text()").getall()
        headers = [x.strip() for x in headers]
        property_map = {}
        for index, th in enumerate(headers):
            property_map[th] = index + 1
        package_table_trs = response.xpath("//tr[@class='cplisttitle']/following-sibling::tr")
        for tr in package_table_trs:
            p_cat_no = tr.xpath(f"./td[{property_map.get('产品编号', 0)}]/text()").get() or ''
            if cat_no.strip() not in p_cat_no.strip():
                continue
            price = tr.xpath(f"./td[{property_map.get('产品价格', 0)}]/text()").get() or ''
            price = price.replace('元', '')
            package = tr.xpath(f"./td[{property_map.get('产品包装', 0)}]/text()").get()
            if not price or not package:
                continue

            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": package,
                "cost": price,
                "price": price,
                "currency": self.currency,
            }
            yield ProductPackage(**dd)
