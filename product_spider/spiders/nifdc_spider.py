import datetime
import json
import re
from os import getenv
from urllib.parse import urljoin

from hashlib import md5
from scrapy import FormRequest, Request
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import strip
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.parsepackage import parse_package
from product_spider.utils.spider_mixin import BaseSpider

NIFDC_USER = getenv('NIFDC_USER', '')
NIFDC_PASS = getenv('NIFDC_PASS', '')


class NifdcSpider(BaseSpider):
    name = 'nifdc'
    brand = '中检所'
    start_urls = [
        'http://aoc.nifdc.org.cn/sell/sgoodsQuerywaiw.do?formAction=queryzc',  # 常规
        'http://aoc.nifdc.org.cn/sell/sgoodsQuerywaiwTs.do?formAction=queryTs',  # 特殊
    ]
    code_url = 'http://aoc.nifdc.org.cn/sell/regwwuser.do?formAction=qdyanzm'
    login_url = 'http://aoc.nifdc.org.cn/sell/loginwaiw.do?formAction=index'
    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS_PER_IP': 2,
    }

    def _start_requests(self):
        yield Request(self.code_url, callback=self.login)

    def login(self, response):
        password = md5(NIFDC_PASS.encode('utf-8')).hexdigest()
        yield FormRequest(self.login_url, formdata={
            'user_code': NIFDC_USER,
            'userpwd': password,
            'inputCode': response.text,
        }, callback=self.parse, )

    def parse(self, response, **kwargs):
        for url in self.start_urls:
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        tmp = './/input[@name={!r}]/@value'
        rows = response.xpath('//table[@class="list_tab"]//tr')
        for row in rows:
            coa = row.xpath('.//td[last()]/a/@href').get()
            batch_name = row.xpath(tmp.format('xsBatch_no')).get()  # 批号
            usage = row.xpath(tmp.format('used')).get()  # 用途
            max_purchase_num = row.xpath(".//input[@name='zdgmshu']/parent::td/text()").get()  # 最大购买数量
            prd_attrs = {
                "usage": usage,
                "max_purchase_num": strip(max_purchase_num),
            }

            d = {
                'brand': self.brand,
                'cat_no': (cat_no := row.xpath(tmp.format('sgoods_no')).get()),
                'parent': row.xpath(tmp.format('sgoods_type')).get(),
                'chs_name': row.xpath(tmp.format('sgoods_name')).get(),
                'en_name': row.xpath(tmp.format('english_name')).get(),
                'info2': row.xpath(tmp.format('save_condition')).get(),
                'stock_info': row.xpath(tmp.format('zdgmshu')).get(),
                'prd_url': coa and urljoin(response.url, coa),
            }
            package_attrs = json.dumps({
                "batch_name": batch_name,
            })
            package = parse_package(row.xpath(tmp.format('standard')).get())
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': package,
                'cost': row.xpath(tmp.format('unit_price')).get(),
                'info': row.xpath(tmp.format('xsBatch_no')).get(),
                'stock_num': row.xpath(tmp.format('zdgmshu')).get(),
                'currency': 'RMB',
                "attrs": package_attrs,
            }
            yield ProductPackage(**dd)
            ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)

            yield SupplierProduct(**ddd)
            yield RawSupplierQuotation(**dddd)

            # 标签说明书附件页(viewfujian)列出了当前批及相邻批的证书下载地址，
            # 解析后写入产品 attrs；无附件时直接产出产品数据。
            attachment_a = row.xpath("./td/a[contains(@href,'viewfujian')]/@href").get()
            if attachment_a:
                yield Request(
                    urljoin(response.url, attachment_a),
                    callback=self.parse_coa_page,
                    meta={'product': d, 'prd_attrs': prd_attrs},
                    priority=1000,
                )
            else:
                d["attrs"] = json.dumps(prd_attrs, ensure_ascii=False)
                yield RawData(**d)

        m = re.search(r'(?:buildPageCtrlOne001\()(\d+),(\d+),(\d+)', response.text)
        if not m:
            return
        cur_page, per_page, total = m.groups()
        if (cur_page := int(cur_page)) * int(per_page) > int(total):
            return
        form_data = {
            "curPage": str(cur_page + 1),
            "toPage": str(cur_page),
        }
        yield FormRequest(response.url, formdata=form_data, callback=self.parse_list)

    def parse_coa_page(self, response):
        """解析标签说明书附件页，获取所有证书批次及对应的下载 url，写入产品 attrs。"""
        d = response.meta['product']
        prd_attrs = response.meta['prd_attrs']
        datetime.date.today().strftime("%Y%m%d")

        # 页面由若干 class="edit" 的表格交替组成：信息表(含"批号")后紧跟标签说明书表(含下载链接)。
        coa_files = {}
        cur_batch = None
        for table in response.xpath('//table[@class="edit"]'):
            th_text = ''.join(table.xpath('.//th//text()').getall())
            if '标签说明书' in th_text:
                href = table.xpath('.//a[contains(@href, "uploadft")]/@href').get()
                if cur_batch and href:
                    coa_files.setdefault(cur_batch, urljoin(response.url, href))
            else:
                batch = strip(table.xpath('.//td[contains(., "批号")]/following-sibling::td[1]/text()').get())
                if batch:
                    cur_batch = batch

        prd_attrs["coa_files"] = coa_files
        d["attrs"] = json.dumps(prd_attrs, ensure_ascii=False)
        yield RawData(**d)
