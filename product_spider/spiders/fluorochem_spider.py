import math
from urllib.parse import urlparse, urlencode, urlunparse

from scrapy import Request
from scrapy.http.request.json_request import JsonRequest

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url
from product_spider.utils.spider_mixin import BaseSpider


class FluorochemSpider(BaseSpider):
    name = "fluorochem"
    start_urls = ["https://www.fluorochem.co.uk/", ]
    base_url = "https://www.fluorochem.co.uk/"
    brand = 'fluorochem'
    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'CONCURRENT_REQUESTS_PER_IP': 8,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        'RETRY_HTTP_CODES': [403],
        'RETRY_TIMES': 10,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }
    currency = 'GBP'

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//ul[@class="sub-menu"]/li[not(ul)]/a/@href').getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, self.request_list_pages)

    def request_list_pages(self, response):
        category_id = response.xpath("//input[@id='all-category-ids']/@value").get()
        if category_id:
            filter_data = {"from": 0, "size": 20, "all_category_ids": category_id, "has_stock": [], "keywords": [],
                           "concept_groups": [], "tags": [], "chemical_structure": [],
                           "logp": {"min": None, "max": None},
                           "molecular_weight": {"min": None, "max": None},
                           "asymmetric_atoms": {"min": None, "max": None},
                           "h_bond_acceptors": {"min": None, "max": None}, "h_bond_donors": {"min": None, "max": None},
                           "fsp3": [], "excludefilters": {"concept_groups": [], "keywords": []}}

            yield JsonRequest(
                url="https://fluorochem.co.uk/wp-json/wpces/v1/filter",
                data=filter_data,
                meta={'category_id': category_id, 'list_url': response.url, },
                callback=self.handle_list_pages_response,
            )

    # 处理每类产品的最大页码
    def handle_list_pages_response(self, response):
        page_size = 20
        meta = response.meta
        list_url = urlparse(meta.get('list_url'))
        try:
            j_obj = response.json()
            total: int = int(j_obj['hits']['total']['value'])
            total_page = math.ceil(total / page_size)
        except Exception as e:
            self.logger.error('获取分类产品数量失败', exc_info=e)
            return

        for page in range(1, total_page + 1):
            new_query = urlencode({'page': page}, doseq=True)
            new_url = urlunparse(list_url._replace(query=new_query))
            yield Request(new_url, self.parse_list)

    def parse_list(self, response):
        self.logger.info(f'list url:{response.url}')
        product_urls = response.xpath("//div[contains(@class,'post-card-container')]/a/@href").getall()
        if not product_urls:
            return
        for url in product_urls:
            url = get_url(response.url, url)
            yield Request(url, self.parse_detail)

    def parse_detail(self, response):
        d = {
            "brand": self.name,
            "parent": response.xpath(
                "//div[@class='single-product__breadcrumbs']//span[@aria-current='page']/text()").get(),
            "cat_no": response.xpath(
                "(//div[@id='content']//*[contains(text(),'Product Code')])[1]/following-sibling::*[1]/text()").get(),
            "en_name": response.xpath("//div[@id='content']//h1[contains(@class,'product_title')]/text()").get(),
            "cas": response.xpath(
                "(//div[@id='content']//*[contains(text(),'CAS')])[1]/following-sibling::*[1]/text()").get(),
            "smiles": response.xpath(
                "(//div[@id='content']//*[contains(text(),'Smiles')])[1]/parent::*[1]/following-sibling::*[1]/text()").get(),
            "mf": response.xpath(
                "(//div[@id='content']//*[contains(text(),'Molecular Formula')])[1]/parent::*[1]/following-sibling::*[1]/text()").get(),
            "img_url": response.xpath("//div[@class='product-card__image']/img/@src").get(),
            'mdl': response.xpath(
                "(//div[@id='content']//*[contains(text(),'MDL Number')])[1]/following-sibling::*[1]/text()")
        }
        yield RawData(**d)

        package_table_trs = response.xpath("//div[@id='content']//*[contains(@class,'pack-selector-table')]//tr")
        headers = [x.strip() for x in package_table_trs[0].xpath(".//th/text()").getall()]
        property_map = {}
        for index, th in enumerate(headers):
            property_map[th] = index + 1

        for tr in package_table_trs[1:]:
            pkg = {
                'package': tr.xpath(f".//td[{property_map.get('Pack size', 0)}]/text()").get(),
                'price': tr.xpath(f".//td[{property_map.get('Price', 0)}]/text()").get(),
                'stock1': tr.xpath(f".//td[{property_map.get('UK', 0)}]/*/text()").get(),
                'stock2': tr.xpath(f".//td[{property_map.get('Europe', 0)}]/*/text()").get(),
                'stock3': tr.xpath(f".//td[{property_map.get('China', 0)}]/*/text()").get(),
            }
            price = pkg['price'].replace('£', '') if pkg['price'] else None
            if not price:
                continue

            stock = 'IN STOCK' if 'In Stock' in [pkg['stock1'], pkg['stock2'], pkg['stock3']] else 'ENQUIRE'
            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": pkg['package'].replace(' ', '') if pkg['package'] else None,
                "cost": price,
                "price": price,
                "stock_num": stock,
                "currency": self.currency,
            }
            yield ProductPackage(**dd)
