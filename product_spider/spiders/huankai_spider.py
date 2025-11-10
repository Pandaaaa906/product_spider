from typing import List, Optional

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url
from product_spider.utils.spider_mixin import BaseSpider


def search_col_index(keyword_list: List[str], headers: List[str]) -> Optional[int]:
    for col in keyword_list:
        for index, h in enumerate(headers):
            h = h.replace(' ', '').strip()
            if col in h:
                return index + 1


class HuankaiSpider(BaseSpider):
    name = "huankai"
    start_urls = ["https://www.huankai.com/product.html", ]
    base_url = "https://www.huankai.com/product.html"
    brand = 'huankai'
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'RETRY_ENABLED': True,
        'RETRY_HTTP_CODES': [403, 500, 502, 504],
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
        rel_urls = response.xpath("//ul[@class='sidebar-list-wrap']/li/a/@href").getall()
        for rel_url in rel_urls:
            if url := get_url(response.url, rel_url):
                yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_urls = response.xpath("//div[@class='product-con']/a/@href").getall()
        if not product_urls:
            return
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, callback=self.parse_detail, )
        if next_url := response.xpath('//ul[@class="pagination"]/a[contains(text(), "下一页")]/@href').get():
            next_url = get_url(response.url, next_url)
            if next_url:
                yield Request(next_url, callback=self.parse_list)

    def extract_property(self, response, keyword: str, base_xpath: str = None):
        base_xpath = base_xpath or '//'
        temp = response.xpath(f"{base_xpath}*[contains(text(),'{keyword}')]/text()").get()
        if temp:
            return temp.replace(keyword, '')
        return None

    def parse_detail2(self, response):
        """
        适合只有一个货号的
        https://www.huankai.com/show/21566.html?btwaf=79671800
        """
        basic_info = self.extract_common_info(response)
        d = {
            "brand": self.brand,
            "cat_no": basic_info.get('cat_no'),
            "en_name": basic_info.get('en_name'),
            "chs_name": basic_info.get('chs_name'),
            "img_url": basic_info.get('img_url'),
            'prd_url': response.url,
        }
        yield RawData(**d)
        packages = basic_info.get('packages') or []
        for package in packages:
            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": package,
                "currency": self.currency,
            }
            yield ProductPackage(**dd)

    def extract_common_info(self, response):
        if img_url := response.xpath('//div[@class="swiper-slide"]/img/@src').get():
            img_url = get_url(response.url, img_url)
        package_text = self.extract_property(response, '规 格 ：') or None
        parent = response.xpath("//div[@class='bread-box']/a[position()=last()-1]/text()").get()
        if not package_text:
            packages = []
        else:
            if '|' in package_text:
                packages = package_text.split('|')
            elif '/' in package_text:
                packages = package_text.split('/')
            else:
                packages = [package_text]
        cat_no = self.extract_property(response, '货 号 ：')
        if not cat_no:
            cat_no = response.url.split('/')[-1]
        return {
            'chs_name': response.xpath("//form[@id='proform']/h3/text()").get(),
            'en_name': self.extract_property(response, '英文名称：'),
            'cat_no': cat_no,
            'usage': self.extract_property(response, '用途：'),
            'packages': packages,
            'img_url': img_url,
            'parent': parent,
        }

    def parse_detail(self, response):
        """
        适合有多个货号写在表格的
        https://www.huankai.com/show/65048.html
        """
        cat_no_cols = ['产品编号', '产品编码', '产品货号', '货号']
        chs_name_cols = ['产品类型', '产品名称', '产品型号', '名称', ]
        package_cols = ['包装规格', '产品包装', '规格包装', '产品规格', '规格', ]
        cat_no_col = None
        trs = []

        header_index = 0  # 表头的索引
        for col in cat_no_cols:
            trs = response.xpath(f"//table[contains(string(.),'{col}')]/tbody/tr")
            if len(trs) > 1:
                cat_no_col = col
                for index, tr in enumerate(trs):
                    if _ := tr.xpath(f"./*[contains(string(.),'{cat_no_col}')]"):
                        header_index = index
                        break
                break
        if not cat_no_col or not trs:
            yield from self.parse_detail2(response)
            return
        headers = trs[header_index].xpath(".//text()").getall()
        headers = list(filter(lambda x: len(x.strip()) > 0, headers))
        if not headers:
            yield from self.parse_detail2(response)
            return
        headers = [x.strip() for x in headers]

        pacakge_col = search_col_index(package_cols, headers)
        cat_no_col = search_col_index(cat_no_cols, headers)
        chs_name_col = search_col_index(chs_name_cols, headers)

        basic_info = self.extract_common_info(response)

        for tr in trs[header_index + 1:]:
            cat_no = tr.xpath(f"./td[{cat_no_col}]//text()").get()
            if cat_no and len(cat_no) > 15:
                self.logger.info(f"疑似不是货号:{cat_no} url:{response.url}")
                continue
            chs_name = tr.xpath(f"./td[{chs_name_col}]//text()").get()
            package = tr.xpath(f"./td[{pacakge_col}]//text()").getall()
            package = ''.join(package)
            d = {
                "brand": self.brand,
                "parent": basic_info.get('parent'),
                "cat_no": cat_no,
                "en_name": basic_info.get('en_name'),
                "chs_name": chs_name or basic_info.get('chs_name'),
                "img_url": basic_info.get('img_url'),
                'prd_url': response.url,
            }
            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": package,
                "currency": self.currency,
            }
            yield RawData(**d)
            yield ProductPackage(**dd)
