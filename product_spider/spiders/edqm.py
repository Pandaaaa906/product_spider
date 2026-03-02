import scrapy
from lxml.etree import XML
from more_itertools import first
from urllib.parse import urljoin, urlencode
import json
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import strip
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.parsepackage import parse_package
from product_spider.utils.spider_mixin import BaseSpider


class EDQMSpider(BaseSpider):
    name = 'ep'
    brand = 'ep'
    start_urls = ["https://crs.edqm.eu/db/4DCGI/web_catalog_XML.xml", ]
    base_url = "https://crs.edqm.eu/"

    def parse(self, response, **kwargs):
        xml = XML(response.body)
        prds = xml.xpath('//Reference')
        for prd in prds:
            cat_no = first(prd.xpath('./@Order_Code'), None)
            batch_num = first(prd.xpath("./Batch_No/text()"), None)  # 批号
            prd_url = f"https://crs.edqm.eu/db/4DCGI/View={cat_no or ''}"
            d = {
                "brand": self.brand,
                "cat_no": cat_no,
                "cas": first(prd.xpath('./CAS_Registry_Number/text()'), None),
                "en_name": first(prd.xpath('./Reference_Standard/text()'), None),
                "info2": first(prd.xpath('./Storage/text()'), None),
                "info3": first(prd.xpath('./Quantity_per_vial/text()'), None),
                "info4": first(prd.xpath('./Price/text()'), None),
                "shipping_group": first(prd.xpath('./Shipping_group/text()'), None),
                "sales_unit": first(prd.xpath('./Sale_Unit/text()'), None),
                "prd_url": prd_url,
            }
            yield scrapy.Request(
                url=prd_url,
                callback=self.parse_detail,
                meta={
                    "product": d,
                    "batch_num": batch_num,
                }
            )

    def parse_detail(self, response):
        batch_num = response.meta.get("batch_num", None)
        d = response.meta.get("product", None)

        controlled_drug = strip(response.xpath(
            "//*[contains(text(), 'Sales restriction')]/parent::td/following-sibling::td/font/text()"
        ).get())

        shipping_info = strip(response.xpath(
            "//*[contains(text(), 'Dispatching conditions')]/parent::td/following-sibling::td/font/text()"
        ).get())

        stock_info = strip(response.xpath(
            "//font[contains(text(), 'Availability')]/parent::td/following-sibling::td/font/text()"
        ).get())

        package = response.xpath(
            "//*[contains(text(), 'Unit quantity per vial')]/parent::td/following-sibling::td/font/text()"
        ).get()
        if package is not None:
            package = parse_package(package)

        cost = strip(response.xpath(
            "//*[contains(text(), 'Price')]/parent::td/following-sibling::td/font[last()-1]/text()"
        ).get())

        currency = strip(response.xpath(
            "//*[contains(text(), 'Price')]/parent::td/following-sibling::td/font[last()]/text()"
        ).get())

        sales_unit = d.pop('sales_unit', '1')
        d["shipping_info"] = shipping_info
        d["stock_info"] = stock_info
        d["attrs"] = json.dumps({
            "controlled_drug": controlled_drug,
        })
        yield RawData(**d)

        if not package:
            return

        package = package if sales_unit == '1' else f'{package}*{sales_unit}'
        package = str.lower(package) if package else package
        dd = {
            "brand": self.name,
            "cat_no": d["cat_no"],
            "package": package,
            "cost": cost,
            "currency": currency,
            "attrs": json.dumps({
                "batch_num": batch_num
            })
        }
        yield ProductPackage(**dd)

        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)

    def keyword_search(self, keyword: str, search_params: dict = None):
        """关键词搜索方法

        通过 EDQM 搜索接口查询产品，使用 Substance Name 字段进行关键词搜索。
        """
        # 构建搜索URL
        search_url = f"{self.base_url}db/4DCGI/search"

        # 搜索参数
        params = {
            'vSelectName': '1',  # 搜索 Substance Name
            'vContains': '1',    # 包含模式
            'vtUserName': keyword,
            'OK': 'Search',
            'vTypeCRS': '',
        }

        # 如果有额外的搜索参数，添加到URL中
        if search_params:
            params.update(search_params)

        # 返回搜索请求
        yield scrapy.Request(
            url=f"{search_url}?{urlencode(params)}",
            callback=self.parse_search_results,
            meta={
                'keyword': keyword,
                'search_params': search_params,
                'task_id': self.task_id,
            }
        )

    def parse_search_results(self, response):
        """解析搜索结果页面"""
        # 提取搜索结果表格中的所有产品行（跳过表头行）
        rows = response.xpath('//table//table//tr[position()>1]')

        for row in rows:
            # 提取 Cat. No. 和详情页链接
            cat_no = row.xpath('./td[2]//text()').get('').strip()
            detail_link = row.xpath('./td[2]//a/@href').get()

            if not cat_no or not detail_link:
                continue

            # 构建完整的产品详情URL
            prd_url = urljoin(self.base_url, detail_link)

            # 从搜索结果中提取基本信息
            d = {
                "brand": self.brand,
                "cat_no": cat_no,
                "en_name": row.xpath('./td[3]//text()').get('').strip() or None,
                "info3": row.xpath('./td[5]//text()').get('').strip() or None,  # Unit Quantity
                "info4": row.xpath('./td[6]//text()').get('').strip() or None,  # Price
                "prd_url": prd_url,
            }

            # 提取 batch_num
            batch_num = row.xpath('./td[4]//text()').get('').strip() or None

            # 请求产品详情页获取更多信息
            yield scrapy.Request(
                url=prd_url,
                callback=self.parse_detail,
                meta={
                    "product": d,
                    "batch_num": batch_num,
                    "keyword": response.meta.get('keyword'),
                    "search_params": response.meta.get('search_params'),
                    "task_id": response.meta.get('task_id'),
                }
            )
