import json
import re
import time
from typing import List
from urllib.parse import urlencode, urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import get_url
from product_spider.utils.spider_mixin import BaseSpider

playwright_page_goto_kwargs = {
    'wait_until': 'networkidle',
}


class AgilentSpider(BaseSpider):
    name = "agilent"
    start_urls = ["https://www.agilent.com.cn/zh-cn/products", ]
    base_url = "https://www.agilent.com.cn/"
    brand = 'agilent'
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'RETRY_ENABLED': True,
        'RETRY_HTTP_CODES': [403, 502],
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
        rel_urls = response.xpath("//ul[@id='seeall']/li//a[contains(@href,'product')]/@href").getall()
        for rel_url in rel_urls:
            if url := get_url(response.url, rel_url):
                yield Request(url, callback=self.dispatch_response)

    def dispatch_response(self, response):
        rel_urls = response.xpath("//a[contains(@href,'/zh-cn/product')]/@href").getall()
        for rel_url in rel_urls:
            url = get_url(response.url, rel_url)
            yield Request(url, callback=self.dispatch_response)

        if script_str := response.xpath("//script[contains(text(),'categoryStepId')]/text()").get():
            self.logger.info(f"dispatch:{response.url}")
            script_str = script_str.strip()
            categoryStepId_pattern = re.compile(r"categoryStepId\s*=\s*'(.*?)';", re.S)
            subGroupStepId_pattern = re.compile(r"subGroupStepId\s*=\s*'(.*?)';", re.S)
            group_id_pattern = re.compile(r"groupStepId\s*=\s*'(.*?)';", re.S)
            category_step_id, d_product_subgroup_id, d_product_group_id = None, None, None
            if match := categoryStepId_pattern.search(script_str):
                category_step_id = match.group(1)
            if match := subGroupStepId_pattern.search(script_str):
                d_product_subgroup_id = match.group(1)
            if match := group_id_pattern.search(script_str):
                d_product_group_id = match.group(1)
            if d_product_subgroup_id and d_product_group_id:
                params = {
                    'No': '0',
                    'Nr': f'AND(SpSearch:Products,d_product_subgroup_id:{d_product_subgroup_id},'
                          f'd_product_group_id:{d_product_group_id},d_product_category_id:{category_step_id})',
                    'Ns': 'p_product_rank||PRODUCT_NAME',
                    '_': str(int(time.time() * 1000)),
                    'callback': 'callbackfn',
                    'format': 'json',
                }
                yield Request(f'https://www.agilent.com.cn/search/getResponse?{urlencode(params)}',
                              meta={'referer': response.url, 'category_key': category_step_id, 'params': params,
                                    "playwright": True, "playwright_page_goto_kwargs": playwright_page_goto_kwargs,
                                    },
                              callback=self.parse_category_json)
            if not d_product_subgroup_id and category_step_id:
                params = {
                    'Nr': f'AND(d_type:productGroupPage,d_product_category_id:{category_step_id})',
                    'Ns': 'p_product_rank||GROUP_NAME',
                    '_': str(int(time.time() * 1000)),
                    'callback': 'callbackfn',
                    'format': 'json',
                }
                yield Request(f'https://www.agilent.com.cn/search/getResponse?{urlencode(params)}',
                              meta={'referer': response.url, 'category_key': category_step_id,
                                    "playwright": True, "playwright_page_goto_kwargs": playwright_page_goto_kwargs,
                                    },
                              callback=self.parse_category_json)

        has_product_list = response.xpath("//*[text()='产品列表']/text()").get()
        if self.is_product_page(response) and not has_product_list:
            yield from self.parse_detail(response)

        if has_product_list:
            # https://www.agilent.com.cn/zh-cn/product/small-molecule-columns/chiral-columns/infinitylab-poroshell-120-chiral
            # 有产品列表
            subCatId, groupSID, subGroupSID, categorySID = None, None, None, None
            script_str = response.xpath("//script[contains(text(),'window.subCatId')]/text()").get() or ''
            if match := re.compile(r"window.subCatId\s*=\s*'(.*?)';", re.S).search(script_str):
                subCatId = match.group(1)

            script_str = response.xpath("//script[contains(text(),'groupSID=')]/text()").get() or ''
            if match := re.compile(r"groupSID\s*=\s*'(.*?)';", re.S).search(script_str):
                groupSID = match.group(1)

            script_str = response.xpath("//script[contains(text(),'categorySID=')]/text()").get() or ''
            if match := re.compile(r"categorySID\s*=\s*'(.*?)';", re.S).search(script_str):
                categorySID = match.group(1)

            script_str = response.xpath("//script[contains(text(),'subGroupSID=')]/text()").get() or ''
            if match := re.compile(r"categorySID\s*=\s*'(.*?)';", re.S).search(script_str):
                subGroupSID = match.group(1)

            params = {
                'Nr': f'AND(d_commerce_id:{subCatId},{"d_product_subgroup_id:" + subGroupSID + "," if subGroupSID else ""}'
                      f'd_product_group_id:{groupSID},d_product_category_id:{categorySID},d_type:part)',
                'Ns': 'p_title',
                '_': str(int(time.time() * 1000)),
                'callback': 'callbackfn',
                'format': 'json',
                'No': '0',
                'isPdpService': 'true',
            }
            url = f'https://www.agilent.com.cn/search/getResponse/services/pdpService?{urlencode(params)}'
            yield Request(url, meta={'referer': response.url, 'params': params,
                                     'cat_id': subCatId,
                                     "playwright": True, "playwright_page_goto_kwargs": playwright_page_goto_kwargs,
                                     }, callback=self.parse_products_json)

    def is_product_page(self, response):
        title = response.xpath("//h1[contains(@class,'pageTitle')]/text()").get()
        return True if title else False

    def parse_products_json(self, response):
        contents = self.extract_json_content(response)
        if not contents:
            if response.meta.get('depth', 0) < 10:
                self.logger.info(f"Retry fetch products json url:{response.url}")
                yield Request(response.url, callback=self.parse_products_json, meta=response.meta)
            return
        cat_id = response.meta.get('cat_id')
        if main_content := list(filter(lambda x: x and x.get('@type') == 'BoundedResultsList', contents)):
            records = main_content[0].get('records')
            if not records:
                self.logger.warning(f"No records found, err:{main_content[0].get('@error')}")
                return
            for record in records:
                try:
                    attrs = record.get('attributes', {})
                    cat_no = attrs.get('g_rollup_key')[0]
                    url = f'https://www.agilent.com.cn/store/productDetail.jsp?catalogId={cat_no}&catId={cat_id}'
                    yield Request(url, callback=self.parse_detail2, meta={
                        'cat_no': cat_no, 'product_data': attrs, "playwright": True,
                        "playwright_page_goto_kwargs": playwright_page_goto_kwargs, })
                except Exception as e:
                    self.logger.warning(f'extract product error:{e} url:{response.url}')

    def extract_json_content(self, response) -> List:
        if match := re.compile(r"^[^(]+\((.*)\)\s*$", re.S).search(response.text):
            j_str = match.group(1)
        else:
            raise ValueError("No valid json found")
        try:
            j_obj = json.loads(j_str)
            contents = j_obj.get('contents')
            main_content = contents[0].get('mainContent', [])
            return main_content
        except Exception as e:
            self.logger.warning(f"Parse json err:{e} url:{response.url} response:{response.text[:200]}")

    def parse_category_json(self, response):
        contents = self.extract_json_content(response)
        if not contents:
            if response.meta.get('depth', 0) < 10:
                self.logger.info(f"Retry fetch category json url:{response.url}")
                yield Request(response.url, callback=self.parse_category_json, meta=response.meta)
            return
        if main_content := list(filter(lambda x: x and x.get('@type') == 'ResultsList', contents)):
            records = main_content[0].get('records')
            if not records:
                self.logger.warning(f"No records found, err:{main_content[0].get('@error')}")
                return
            else:
                self.logger.info("parse_category_json OK")
            for record in records:
                attrs = record.get('attributes', {})
                if _url := attrs.get('sd_relative_url')[0] if attrs.get('sd_relative_url') else None:
                    _url = urljoin(self.base_url, _url)
                    meta = response.meta
                    meta['referer_json'] = response.url
                    yield Request(_url, callback=self.dispatch_response, meta=meta)

    def parse_detail(self, response):
        """
        https://www.agilent.com.cn/zh-cn/product/atomic-spectroscopy/atomic-absorption/graphite-furnace-atomic-absorption-instruments/240z-aa
        :param response:
        :return:
        """
        if img_url := response.xpath('//img[@class="theImg"]/@src').get():
            img_url = get_url(response.url, img_url)

        cat_no = response.xpath("//h1[contains(@class,'pageTitle')]/text()").get()
        if not cat_no:
            self.logger.info(f"No cat no found, url:{response.url}")
            return
        parent = response.xpath("//span[contains(@class,'pageSubTitle')]/text()").get()
        desc = response.xpath("//div[contains(@class,'dakoLogoTitle')]/text()").get() or ''
        attrs = {
            'description': desc.strip()
        }
        d = {
            "brand": self.brand,
            "parent": parent,
            "cat_no": cat_no,
            "chs_name": f'{parent}_{cat_no}',
            "img_url": img_url,
            'prd_url': response.url,
            'attrs': json.dumps(attrs, ensure_ascii=False),
        }
        yield RawData(**d)

    def parse_detail2(self, response):
        """
            https://www.agilent.com.cn/store/productDetail.jsp?catalogId=5799-0003&catId=CatECS_366825
        """
        if img_url := response.xpath('//img[@class="theImg"]/@src').get():
            img_url = get_url(response.url, img_url)
        product_data = response.meta['product_data']
        cat_no = response.meta['cat_no']
        parent = product_data.get('PROD_HIERARCHY')[-1]
        brand = response.xpath("//td[text()='品牌']/following-sibling::td[1]//li/text()").get() or self.brand
        d = {
            "brand": brand,
            "parent": parent,
            "cat_no": cat_no,
            "chs_name": f'{parent} {cat_no}',
            "en_name": f'{parent} {cat_no}',
            "img_url": img_url,
            'prd_url': response.url,
        }
        yield RawData(**d)

        package = response.xpath("//td[text()='体积']/following-sibling::td[1]//li/text()").get()
        if not package:
            package = '件'
        price = response.xpath("//span[@class='custom-price']/span/text()").get()
        if price:
            price = price.replace('CNY', '').replace(',', '')
        dd = {
            "brand": brand,
            "cat_no": d['cat_no'],
            "package": package,
            "cost": price,
            "price": price,
            "currency": self.currency,
            'delivery_time': response.xpath("//span[@class='estimated-ship']/span/text()").get(),
        }
        yield ProductPackage(**dd)
