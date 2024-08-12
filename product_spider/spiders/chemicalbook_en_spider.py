import re
from enum import Enum
from itertools import chain
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import SupplierProduct, RawSupplier
from product_spider.utils.functions import dumps
from product_spider.utils.spider_mixin import BaseSpider


class ChemicalBookStrategy(str, Enum):
    FROM_CB_CHEM = 'FROM_CB_CHEM'
    WALK_THROUGH_CAS = 'WALK_THROUGH_CAS'


class ChemicalBookEnSpider(BaseSpider):
    name = 'chemicalbook_en'
    start_urls = [
        # 'https://www.chemicalbook.com/ProdSupplierGN_EN.aspx?CBNumber=CB3108758&ProvID=1001&start=2',
        'https://www.chemicalbook.com/ProdSupplierGN_EN.aspx?CBNumber=CB3108758&ProvID=1001&start=39',
    ]

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'PROXY_POOL_REFRESH_STATUS_CODES': [403, 500, 302],
        'RETRY_TIMES': 20,
        'CONCURRENT_REQUESTS': 8,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        ),
    }

    def is_proxy_invalid(self, request, response):
        if response.status in {403, 500, 302}:
            self.logger.warning(f'status code:{response.status}, {request.url}')
            return True
        if '系统忙' in response.text[:50]:
            self.logger.warning(f'system busy: {request.url}')
            return True
        if response.url.startswith('https://gateway.zspreview.net:443/'):
            return True
        if request.url.startswith('https://www.chemicalbook.com/ShowAllProductByIndexID') \
                and not bool(response.xpath("//div[@id='mainDiv']//tr/td[1]/a")):
            self.logger.warning(f'empty cas list: {request.url}')
            return True
        return False

    def __init__(
            self,
            strategy=ChemicalBookStrategy.WALK_THROUGH_CAS,
            page_start=1, page_end=35, lookback_days=60, **kwargs
    ):
        super().__init__(**kwargs)
        self.strategy = strategy
        self.page_start = int(page_start)
        self.page_end = int(page_end)

    def start_requests(self):
        if self.strategy == ChemicalBookStrategy.WALK_THROUGH_CAS:
            for i in range(self.page_start, self.page_end + 1):
                url = f"https://www.chemicalbook.com/ShowAllProductByIndexID_CAS_{i}_0.htm"
                yield Request(
                    url=url,
                    callback=self.parse,
                    meta={'dont_redirect': True, 'handle_httpstatus_list': [302]}
                )
        elif self.strategy == ChemicalBookStrategy.WALK_THROUGH_CAS:
            raise NotImplemented
        raise NotImplemented

    def parse(self, response, **kwargs):
        a_nodes = response.xpath("//div[@id='mainDiv']//tr/td[1]/a")

        for a_node in a_nodes:
            url = a_node.xpath('./@href').get()
            cas = a_node.xpath('./text()').get()
            cb_id = (m := re.search(r'CB\d+', url)) and m.group()
            if not cb_id:
                self.logger.warning(f"doesn't have cb_id in : {response.url}")
                continue
            yield Request(
                url=f"https://www.chemicalbook.com/ProdSupplierGN_EN.aspx?CBNumber={cb_id}&ProvID=1001",
                callback=self.parse_cb_supplier_list,
                meta={"cas": cas, 'dont_redirect': True, 'handle_httpstatus_list': [302]},
                priority=10,
            )
        # 翻页
        next_pages = response.xpath('//div[@class="page_jp"]/b/following-sibling::a/@href').getall()
        for idx, next_page in enumerate(next_pages):
            if idx > 32:
                break
            if idx not in {0, 2, 8, 32}:
                continue
            yield Request(
                url=urljoin(response.url, next_page),
                callback=self.parse,
                meta={'dont_redirect': True, 'handle_httpstatus_list': [302]}
            )

    def parse_cb_supplier_list(self, response):
        """
        parse url like:
        https://www.chemicalbook.com/ProdSupplierGNCB5433869_EN.htm
        https://www.chemicalbook.com/ProdSupplierGN_EN.aspx?CBNumber=CB3108758&ProvID=1001
        :param response:
        :return:
        """

        cb_id = response.xpath('//a[@id="bt_delegate_list"]/@data-cbnumber').get()
        en_name = response.xpath('//h1/text()').get()
        cas = ''.join(response.xpath('//td[text()="CAS:"]/following-sibling::td//text()').getall())
        mf = response.xpath('//td[text()="MF:"]/following-sibling::td//text()').get()
        mw = response.xpath('//td[text()="MW:"]/following-sibling::td//text()').get()
        img_url = response.xpath('//td[@class="Pro_img"]/img/@src').get()
        img_url = img_url and urljoin(response.url, img_url)

        div_supplier_nodes = response.xpath('//div[@id="ContentPlaceHolder1_ProductSupplier"]/div')
        table_supplier_nodes = response.xpath(
            '//div[@id="ContentPlaceHolder1_ProductSupplier"]/table[@class="ProdGN_4"]')
        for supp_node in chain(div_supplier_nodes, table_supplier_nodes):
            supp_id = supp_node.xpath('.//input[@name="cbsid"]/@data-cbsid').get()
            vendor = supp_node.xpath('.//tr[1]/td/a[1]//text()').get()
            country = supp_node.xpath('.//td[text()="Nationality:"]/following-sibling::td//text()').get()
            phone = supp_node.xpath('.//td[text()="Tel:"]/following-sibling::td//text()').get()
            email = supp_node.xpath('.//td[text()="Email:"]/following-sibling::td//text()').get()
            website = supp_node.xpath('.//td[text()="WebSite:"]/following-sibling::td//text()').get()
            cb_idx = supp_node.xpath('.//td[text()="CB Index:"]/following-sibling::td//text()').get()
            catalog_node = supp_node.xpath(
                './/td[text()="Related Information:"]/following-sibling::td/a[contains(text(), "Catalog")]')
            tmp = catalog_node.xpath('./text()').get('')
            prd_count = (m := re.match(r'Catalog\((\d+)\)', tmp)) and m.group(1)
            vendor_url = catalog_node.xpath('./@href').get()
            vendor_url = vendor_url and urljoin(response.url, vendor_url)
            attrs = {
                "prd_count": prd_count,
                "adv_score": cb_idx,
                "src_url": vendor_url,
            }
            ddd = {
                "platform": self.name,
                "vendor": vendor,
                "source_id": f"{supp_id or vendor}_{cb_id}",
                "brand": vendor,
                "en_name": en_name,
                "cas": cas,
                "mf": mf,
                "mw": mw,
                "cat_no": cb_id,
                "img_url": img_url,
                "prd_url": response.url,
            }
            if country:
                ddd['vendor_origin'] = country
            yield SupplierProduct(**ddd)
            supplier = {
                'src_type': self.name,
                'src_id': supp_id,
                "en_name": vendor,
                "region": country,
                "phone": phone,
                "email": email,
                "website": website,
                "attrs": dumps(attrs)
            }
            yield RawSupplier(**supplier)

        next_page = response.xpath('//div[@align="center"]/b/following-sibling::a/@href').get()
        if next_page:
            yield Request(
                urljoin(response.url, next_page),
                callback=self.parse_cb_supplier_list,
                meta={'dont_redirect': True, 'handle_httpstatus_list': [302]},
                priority=10,
            )
