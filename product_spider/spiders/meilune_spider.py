import re

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url
from product_spider.utils.spider_mixin import BaseSpider


class MeiluneSpider(BaseSpider):
    name = "meilune"
    start_urls = ["https://www.meilune.com/", ]
    base_url = "https://www.meilune.com/"
    brand = 'meilune'
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
        rel_urls = response.xpath("//div[contains(@class,'hh2_list')]/a/@href").getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_urls = response.xpath("//table//td/a/@href").getall()
        if not product_urls:
            return
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, callback=self.parse_detail)

        if next_url := response.xpath('//a[contains(text(),"下一页")]/@href').get():
            next_url = get_url(response.url, next_url)
            if next_url:
                yield Request(next_url, callback=self.parse_list)

    def extract_property(self, response, keyword: str, base_xpath: str = None):
        base_xpath = base_xpath or '//'
        temp = response.xpath(f"{base_xpath}*[contains(text(),'{keyword}')]/text()").get()
        if temp:
            return temp.replace(keyword, '')
        return None

    def parse_detail(self, response):
        if img_url := response.xpath('//div[@class="swiper-wrapper"]/div/img/@src').get():
            img_url = get_url(response.url, img_url)
        cas = self.extract_property(response, 'CAS 号：', base_xpath="//div[contains(@class,'pro_tab_con')]//")

        if mf := response.xpath("//span[contains(.//text(),'分子式：')]/following-sibling::*/text()").getall():
            mf = ''.join(mf)
            mf = mf.split('\xa0')[0]
        elif mf2 := self.extract_property(response, '分子式：'):
            mf = mf2
        else:
            mf = None
        mw = response.xpath("//span[contains(.//text(),'分子量：')]/following-sibling::*/text()").get()

        parent = response.xpath("//div[contains(@class,'top_break')]/a[@class='active']/text()").get()
        cat_no = self.extract_property(response, '总货号: ')

        d = {
            "brand": self.brand,
            "parent": parent,
            "cat_no": cat_no,
            "en_name": self.extract_property(response, '英文名字：'),
            "chs_name": response.xpath("//div[contains(@class,'pro_show_con_main')]//div[@class='hd1']/text()").get(),
            "purity": self.extract_property(response, '质量标准：'),
            "img_url": img_url,
            "mf": mf,
            "mw": mw,
            "cas": cas,
            'prd_url': response.url,
        }
        yield RawData(**d)

        headers = response.xpath("//table[@class='fl']/tr[@class='one']/td/text()").getall()
        headers = [x.strip() for x in headers]
        property_map = {}
        for index, th in enumerate(headers):
            property_map[th] = index + 1
        package_table_trs = response.xpath("//table[@class='fl']/tr[@class='top_4_two']")
        for tr in package_table_trs:
            price = tr.xpath(f"./td[{property_map.get('规格', 0)}]//span[contains(text(),'￥')]/text()").get() or ''
            if not price:
                continue
            else:
                price = price.replace(':￥', '')

            package = tr.xpath(f"./td[{property_map.get('规格', 0)}]//div[contains(@class,'czjz')]/text()").get() or ''
            if not package:
                continue
            pattern = re.compile(r'(.*)(?=\s*\[|$)', re.IGNORECASE)
            match = pattern.search(package)
            if match:
                package = match.group(1)
            else:
                package = None

            delivery_time = tr.xpath(f"./td[{property_map.get('发货时间', 0)}]/*/text()").get()
            stock_num = None
            if '现货' in delivery_time:
                stock_num = '现货'
            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": package,
                "cost": price,
                "price": price,
                "stock_num": stock_num,
                "delivery_time": delivery_time,
                "currency": self.currency,
            }
            yield ProductPackage(**dd)
