import re

from scrapy import Request, FormRequest

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url
from product_spider.utils.spider_mixin import BaseSpider


class InterchimSpider(BaseSpider):
    name = "interchim"
    base_url = "https://www.interchim.com"
    brand = 'interchim'
    api_url = 'https://www.interchim.com/inter_products_fine_requete.php'
    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
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
    nav_types = {
        'ALPHA': '1',
        'PAGINATION': '0',
    }

    def build_params(self, c_param_fine: str, nav_type: str):
        return {
            "cSearch_fine": "",
            "cCAS_fine": "",
            "cMFCD_fine": "",
            "cCatalogNumber_fine": "",
            "nChoixRecherche_fine": "-1",
            "cAfficheNavig": "search_affiche_navig",
            "cAfficheNavigNum": "search_affiche_navig_num",
            "cTypeNavig": nav_type,
            "cParam_fine": c_param_fine,
        }

    def start_requests(self):
        params = {
            "cSearch_fine": "",
            "cCAS_fine": "",
            "cMFCD_fine": "",
            "cCatalogNumber_fine": "",
            "nChoixRecherche_fine": "-2",
            "cAfficheNavig": "search_affiche_navig",
            "cAfficheNavigNum": "search_affiche_navig_num",
            "cTypeNavig": "1",
            "cParam_fine": '65;200',
        }
        yield FormRequest(self.api_url, formdata=params)

    def parse(self, response, **kwargs):
        nav_params = re.findall(r'navigAlpha\(.*?&quot;(.+?)&quot;', response.text)
        for nav in nav_params:
            yield FormRequest(self.api_url, formdata=self.build_params(nav, self.nav_types['ALPHA']),
                              callback=self.parse_list)

    def parse_detail_list(self, response):
        product_urls = response.xpath("//td/a/@href").getall()
        if not product_urls:
            return
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, self.parse_detail, )

    def parse_list(self, response):
        nav_params = re.findall(r'navig\(.*?&quot;(.+?)&quot;', response.text)
        if len(nav_params) < 5:
            # 不带<<   <  >   >>
            for index, nav in enumerate(nav_params):
                yield FormRequest(self.api_url, callback=self.parse_detail_list,
                                  formdata=self.build_params(nav, self.nav_types['PAGINATION']), )
        else:
            self.parse_detail_list(response)
            for index, nav in enumerate(nav_params):
                # nav: 'debut;200;;805;1;0'
                parts = nav.split(';')
                if len(parts) < 6:
                    self.logger.warning(f'分页参数异常:{nav}')
                    return
                if parts[0] == parts[-2] and index == len(nav_params) - 3:
                    # 最后一页
                    return
                if parts[0] == 'suiv':
                    yield FormRequest(self.api_url, formdata=self.build_params(nav, self.nav_types['PAGINATION']),
                                      callback=self.parse_list)

    def parse_detail(self, response):
        product_div = response.xpath("//div[@id='bloc']")
        for div in product_div:
            brand = div.xpath('./div/font/text()').get()
            cat_no_pack_text: str = div.xpath('./div[contains(text(),"P/N")]/text()').get()
            if not cat_no_pack_text:
                continue
            cat_no_pack_text = cat_no_pack_text.replace('nbsp;', ' ')
            match = re.search(r'P/N\s*:\s*(\S+)\s+Pack\s*:\s*\d+\s*x\s*(\d+\s*\w+)', cat_no_pack_text)
            if match:
                cat_no = match.group(1).strip()
                pack = match.group(2).strip()
                if pack:
                    pack = pack.replace(' ', '')
            else:
                continue
            if not cat_no:
                continue
            img_url = div.xpath('.//div/img/@src').get()
            if img_url:
                img_url = get_url(response.url, img_url)
            d = {
                "brand": brand,
                "cat_no": cat_no,
                "en_name": div.xpath("./div/font/following-sibling::text()[1]").get(),
                "cas": div.xpath(".//div/*[contains(text(), 'CAS')]/following-sibling::text()[1]").get(),
                "mf": div.xpath(".//div/*[contains(text(), 'Molecular formula')]/following-sibling::text()[1]").get(),
                "img_url": img_url,
                'prd_url': response.url,
            }
            yield RawData(**d)
            if pack:
                dd = {
                    "brand": self.brand,
                    "cat_no": d['cat_no'],
                    "package": pack,
                }
                yield ProductPackage(**dd)
