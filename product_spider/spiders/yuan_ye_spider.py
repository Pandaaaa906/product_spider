import re
from urllib.parse import urljoin
from uuid import uuid4

import scrapy

from product_spider.items import (
    RawData,
    ProductPackage,
    SupplierProduct,
    RawSupplierQuotation,
)
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip
from product_spider.utils.items_translate import (
    product_package_to_raw_supplier_quotation,
    rawdata_to_supplier_product,
)
from product_spider.utils.spider_mixin import BaseSpider


class YuanYeSpider(BaseSpider):
    """上海源叶"""

    name = "yuan_ye"
    start_urls = ["https://www.shyuanye.com/"]
    base_url = "https://www.shyuanye.com/"

    # ponytail: 全站 16 并发会触发 WAF JS 挑战页(返回 200 但无内容), 限速防封
    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 1,
        # WAF 按浏览器会话标记, 重试需换新 context; 限制 context 总数防泄漏
        "PLAYWRIGHT_MAX_CONTEXTS": 20,
    }

    WAF_MAX_RETRY = 3

    @staticmethod
    def _is_waf_challenge(response):
        # 挑战页特征: 滑动验证标题, 或极小的混淆 JS 页(正常页面均 >90KB, 挑战页 ~12KB)
        return "滑动验证" in response.text or len(response.body) < 15000

    def _retry_or_warn(self, response):
        retry = response.meta.get("waf_retry", 0)
        if retry < self.WAF_MAX_RETRY:
            return scrapy.Request(
                url=response.url,
                callback=response.request.callback,
                meta={
                    **response.meta,
                    "waf_retry": retry + 1,
                    # 实测同 context 重试必败, 新 context 立即可过
                    "playwright_context": f"waf_{uuid4().hex}",
                },
                dont_filter=True,
            )
        self.logger.warning("WAF challenge after %d retries: %s", retry, response.url)
        return None

    def parse(self, response, **kwargs):
        for url in set(response.xpath("//a/@href").getall()):
            if re.fullmatch(
                r"(?:https?://www\.shyuanye\.com/)?category-\d+\.html", url
            ):
                yield scrapy.Request(
                    url=urljoin(self.base_url, url),
                    callback=self.parse_list,
                )

    def parse_list(self, response):
        if self._is_waf_challenge(response):
            req = self._retry_or_warn(response)
            if req:
                yield req
            return
        urls = response.xpath(
            "//ul[@class='product_list_ul3']//a[@class='name_btn']/@href"
        ).getall()
        for url in urls:
            yield scrapy.Request(
                url=urljoin(self.base_url, url),
                callback=self.parse_detail,
            )
        next_urls = response.xpath("//ul[@class='pagination']//a/@href").getall()
        for next_url in next_urls:
            yield scrapy.Request(
                url=urljoin(self.base_url, next_url), callback=self.parse_list
            )

    def parse_detail(self, response):
        if "product_base_info" not in response.text:
            req = self._retry_or_warn(response)
            if req:
                yield req
            return
        parent = response.xpath("//ol[@class='breadcrumb']/li/a[last()]/text()").get()
        chs_name = response.xpath("//h1/text()").get()
        purity = strip(response.xpath("//div[@id='proGuige']/text()").get())
        en_name = strip(response.xpath("//div[@class='left_name']/h2/text()").get())

        tmp_xpath = (
            "//div[@class='product_base_info']"
            "/div[@class='item'][label[contains(text(), {!r})]]/b//text()"
        )
        cat_no = strip("".join(response.xpath(tmp_xpath.format("产品编号：")).getall()))
        cas = strip("".join(response.xpath(tmp_xpath.format("CAS号：")).getall()))
        mf = strip("".join(response.xpath(tmp_xpath.format("分子式：")).getall()))
        mw = strip("".join(response.xpath(tmp_xpath.format("分子量：")).getall()))
        mdl = strip("".join(response.xpath(tmp_xpath.format("MDL：")).getall()))

        img_url = response.xpath("//img[contains(@src, 'images/info/')]/@src").get()
        if img_url:
            img_url = urljoin(self.base_url, img_url)

        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": cat_no,
            "chs_name": chs_name,
            "purity": purity,
            "en_name": en_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "mdl": mdl,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield RawData(**d)
        yield SupplierProduct(**rawdata_to_supplier_product(d, self.name, self.name))
        rows = response.xpath("//table[.//th[contains(text(), '货号')]]//tbody/tr")
        for row in rows:
            sn = strip(row.xpath("./td[1]//div[@class='pronum']/text()").get())
            if not sn:
                continue
            res = re.search(r"(?<=-).*", sn)
            if not res:
                continue
            package = res.group()
            price_text = " ".join(row.xpath("./td[3]//text()").getall())
            prices = re.findall(r"￥([\d.]+)", price_text)
            cost = parse_cost(prices[-1]) if prices else None
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "cost": cost,
                "currency": "CNY",
            }
            yield ProductPackage(**dd)
            if dd["cost"]:
                yield RawSupplierQuotation(
                    **product_package_to_raw_supplier_quotation(
                        d, dd, self.name, self.name
                    )
                )
