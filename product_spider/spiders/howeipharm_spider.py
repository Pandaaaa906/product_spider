import json
import re
from urllib.parse import urljoin, urlparse, urlunparse

from scrapy.http import FormRequest, Request

from product_spider.items import (
    RawData,
    ProductPackage,
    SupplierProduct,
    RawSupplierQuotation,
)
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip, clean_dict
from product_spider.utils.items_translate import (
    product_package_to_raw_supplier_quotation,
    rawdata_to_supplier_product,
)
from product_spider.utils.spider_mixin import BaseSpider

EXCLUDE_BRANDS = {
    'ncrm',
    'hongmeng',
    'weiye',
    'tmrm',
}


def _trim_semi(t: str | None) -> str | None:
    if not isinstance(t, str):
        return t
    return t.strip(' :：')


class HoweipharmSpider(BaseSpider):
    name = "howeipharm"
    brand = "howeipharm"
    base_url = "https://www.howeipharm.com/zh"
    start_urls = ["https://www.howeipharm.com/zh"]

    custom_settings = {
        'RETRY_HTTP_CODES': [503, 504, 403, 429],
        'RETRY_TIMES': 10,
        'CONCURRENT_REQUESTS': 4,
    }

    @staticmethod
    def _compute_waf_answer(a: int, b: int, c: int) -> int:
        """根据 360 磐云 WAF 的 JS 挑战逻辑动态计算 answer"""
        e = a * b + c
        e = 3 * e + 7
        if e < 123:
            e += 2345
        if e > 2345:
            e = e // 123
        return e

    def _handle_waf(self, response, callback, **cb_kwargs):
        """检测并绕过 360 磐云 WAF JS 挑战"""
        if (
                response.status == 200
                and b"waf_answer" in response.body
                and b"ChallengeForm" in response.body
                and not response.meta.get("waf_bypassed")
        ):
            match = re.search(r"const a=(\d+),b=(\d+),c=(\d+)", response.text)
            if match:
                a, b, c = map(int, match.groups())
                answer = self._compute_waf_answer(a, b, c)
                self.logger.info(f"WAF challenge detected, auto-bypassing with answer={answer} (a={a}, b={b}, c={c})")
            else:
                # 兜底：如果正则匹配失败，给一个保守的默认值并记录警告
                self.logger.warning("WAF challenge detected but failed to parse a,b,c, fail to solve challenge")
                return None
            return FormRequest(
                url=response.url,
                formdata={"answer": str(answer)},
                callback=callback,
                meta={**response.meta, "waf_bypassed": True},
                dont_filter=True,
                cb_kwargs=cb_kwargs,
            )
        return None

    def parse(self, response, **kwargs):
        """解析产品分类链接"""
        waf_req = self._handle_waf(response, self.parse, **kwargs)
        if waf_req:
            yield waf_req
            return

        self.logger.debug(f"Parsing categories from {response.url}")

        # 提取所有产品分类链接
        category_links = response.xpath('//a[contains(@href, "/zh/products/")]/@href').getall()
        category_links = list(set(category_links))  # 去重

        self.logger.debug(f"Found {len(category_links)} category links")

        for link in category_links:
            yield Request(
                urljoin(self.base_url, link),
                callback=self.parse_product_list,
            )

    def parse_product_list(self, response):
        """解析产品列表页面"""
        waf_req = self._handle_waf(response, self.parse_product_list)
        if waf_req:
            yield waf_req
            return

        # 提取当前页的产品 - 在 p_list_body 下的 li 元素（排除 list_title）
        rel_urls = response.xpath('//div[contains(@class, "pname")]/a/@href').getall()

        for prd_rel_url in rel_urls:
            yield Request(
                urljoin(self.base_url, prd_rel_url),
                callback=self.parse_detail,
            )

        # 处理分页
        next_page = response.xpath('//li[@class="e-page-item"]/a[contains(text(), "下页")]/@href').get()
        if next_page:
            parsed = urlparse(response.url)
            clean_url = urlunparse(parsed._replace(query="", fragment=""))
            yield Request(
                clean_url + next_page,
                callback=self.parse_product_list,
            )

    def parse_detail(self, response):
        """解析产品详情页"""
        waf_req = self._handle_waf(response, self.parse_detail)
        if waf_req:
            yield waf_req
            return

        # 从URL中提取品牌和货号
        url_match = re.search(r'/product/([^/]+)/([^/]+)', response.url)
        brand_code = url_match.group(1) if url_match else ''

        # 初始化属性字典
        extra_attrs = {
            "reference_std": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"参考标准")]/text()').getall())),
            "color_std": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"色标")]/text()').getall())),
            "max_absorption_wavelength": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"最大吸收波长")]/text()').getall())),
            "melting_point": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"熔点")]/text()').getall())),
            "expiry_days": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"保质期")]/text()').getall())),
            "has_coa": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"质检报告(COA)")]/text()').getall())),
            "ph_trans_range": [
                value
                for raw_value in  response.xpath('//p[contains(./span/text(),"pH 变色域")]/text()').getall()
                if (value:=_trim_semi(raw_value))
            ]
        }

        # 使用默认品牌
        brand = brand_code or self.brand

        cat_no = response.xpath('//div[./span/text()="产品编号"]/following-sibling::div/text()').get()

        # 产品图片
        img_url = response.xpath('//div[contains(@class, "pd-image") or contains(@class, "product-image")]//img/@src').get('')
        if not img_url:
            img_url = response.xpath('//div[contains(@class, "e-prodetails-wrap")]//img/@src').get('')

        concentration = _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"浓度")]/text()').getall()))
        stock_info = response.xpath('//div[@id="stock"]/text()').get()
        if stock_info and '请选择包装' in stock_info:
            stock_info = None

        parent = response.xpath('//div[@id="path_full"]/a[position()=last()]/text()').get()
        extra_attrs = clean_dict(extra_attrs)
        # 创建 RawData
        raw_data = {
            "brand": brand,
            "parent": parent,
            "cat_no": cat_no,
            "chs_name": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"产品名称")]/text()').getall())),
            "en_name": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"英文名称")]/text()').getall())),
            "cas": response.xpath('//div[./span/text()="CAS号"]/following-sibling::div/text()').get(),
            "mf": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"分子式")]/text()').getall())),
            "mw": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"分子量")]/text()').getall())),
            "mdl": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"MDL编号")]/text()').getall())),
            "purity": concentration,
            "appearance": _trim_semi(''.join(response.xpath('//p[contains(./span/text(),"颜色外观")]/text()').getall())),
            "stock_info": stock_info,

            "img_url": img_url,
            "prd_url": response.url,
            "attrs": json.dumps(extra_attrs, ensure_ascii=False) if extra_attrs else None,
        }

        if brand not in EXCLUDE_BRANDS:
            yield RawData(**raw_data)

        ddd = rawdata_to_supplier_product(raw_data, platform=self.name, vendor=self.name)
        yield SupplierProduct(**ddd)

        # 处理包装和价格
        # 如果页面中有包装表格，提取具体包装和价格

        for row in response.xpath('//ul[@id="packs"]/li'):
            pkg = row.xpath('.//a/text()').get()
            if not pkg:
                continue
            price_text = row.xpath('./a/@price').get('')
            cost = parse_cost(price_text)

            pkg_data = {
                "brand": brand,
                "cat_no": cat_no,
                "package": pkg,
                "cost": cost,
                "price": cost,
                "currency": "CNY",
                "delivery_time": stock_info,
            }
            yield ProductPackage(**pkg_data)

            if cost:
                dddd = product_package_to_raw_supplier_quotation(raw_data, pkg_data, platform=self.name, vendor=self.name)
                yield RawSupplierQuotation(**dddd)

    def keyword_search(self, keyword, search_params=None):
        """关键词搜索功能"""
        search_url = f"{self.base_url}/search?k={keyword}"
        yield Request(
            search_url,
            callback=self.parse_product_list,
            meta={"keyword": keyword, "per_page": 1},
        )
