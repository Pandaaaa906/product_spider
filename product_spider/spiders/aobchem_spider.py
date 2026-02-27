import json
from os import getenv

from scrapy import Request, FormRequest
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


AOBCHEM_USER = getenv('AOBCHEM_USER')
AOBCHEM_PWD = getenv('AOBCHEM_PWD')


class AobchemSpider(BaseSpider):
    name = "aobchem"
    base_url = 'https://www.aobchem.com.cn'
    start_urls = ["https://www.aobchem.com.cn/pages/437.html"]
    login_url = 'https://www.aobchem.com.cn/index.aspx?a=ajaxuserlogin'

    def _start_requests(self):
        # 发送登录请求
        yield FormRequest(
            url=self.login_url,
            formdata={
                'setsession': '1',
                'verifyid': '',
                'username': AOBCHEM_USER,
                'password': AOBCHEM_PWD,
                'loginmethod': 'password',
            },
            callback=self.after_login,
        )

    def is_login_successful(self, response):
        return True

    def after_login(self, response):
        if self.is_login_successful(response):
            # 登录成功后，获取初始页面
            yield Request(
                url=self.start_urls[0],
                callback=self.parse
            )

    def parse(self, response, **kwargs):
        urls = response.xpath("//li[@class='list-group-item']/a/@href").getall()
        for url in urls:
            yield Request('http:' + url, callback=self.parse_list)

    def parse_list(self, response):
        detail_urls = response.xpath("//h4/span/a/@href").getall()
        for url in detail_urls:
            yield Request('http:' + url, callback=self.parse_detail)
        next_url = response.xpath("//a[text()='下一页']/@href").get()
        if next_url:
            yield Request('http:' + next_url, callback=self.parse_list)

    def parse_detail(self, response):
        info_xpath = "//div[@class='table-responsive kj_cplb']//tr//td[contains(text(), {!r})]/following-sibling::td[1]/text()"
        cat_no = response.xpath(info_xpath.format('产品编号')).get()
        parent = response.xpath("//ol[@class='breadcrumb']/li[last()]/a/text()").get()
        en_name = response.xpath(info_xpath.format('英文名')).get()
        chs_name = response.xpath(
            "//div[@class=' col-lg-8 col-md-8 col-sm-7 col-xs-12 kj_promcxx']/h1/span/text()").get()
        cas = response.xpath(info_xpath.format('CAS号')).get()
        mw = response.xpath(info_xpath.format('分子量')).get()
        mf = ''.join(response.xpath('//td[text()="分子式"]/following-sibling::td[1]//text()').getall())
        prd_url = response.url
        img_url = response.xpath("//div[@class='item active']/img/@src").get()
        if img_url:
            img_url = "http:" + img_url
        mdl = response.xpath(info_xpath.format('MDL')).get()
        prd_id = response.xpath("//input[@name='productcatalog']/@productid").get()
        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": cat_no,
            "en_name": en_name,
            "chs_name": chs_name,
            "cas": cas,
            "mw": mw,
            "mf": mf,
            "prd_url": prd_url,
            "img_url": img_url,
            "mdl": mdl,
        }
        yield FormRequest(
            url="https://www.aobchem.com.cn/ajaxpro/Web960.Web.index,Web960.Web.ashx",
            method='POST',
            callback=self.parse_package,
            body=json.dumps({"pd_id": prd_id}),
            headers={'X-Ajaxpro-Method': 'LoadGoods'},
            meta={"product": d, "prd_id": prd_id},
        )

    def parse_package(self, response):
        d = response.meta.get("product")
        yield RawData(**d)
        yield SupplierProduct(SupplierProduct(**rawdata_to_supplier_product(d, self.name, self.name)))
        prd_id = response.meta.get("prd_id")
        j_obj = json.loads(response.text.strip(';/*'))
        j_str = j_obj['ObjResult'].replace('\\"', '"').replace('\\\\', '').replace('"{', '{').replace('}"', '}').replace('\\r\\n', '')
        datas = json.loads(j_str).get(f'p_{prd_id}', [])
        for data in datas:
            for i in data.get("Inventores", []):
                price = i.get("Price", None)
                raw_cat_no = i.get("Goods_no", None)
                cat_no, package = raw_cat_no.split("—")

                dd = {
                    "cat_no": cat_no,
                    "package": package,
                    "cost": price,
                    "price": price,
                    "brand": self.name,
                    "currency": "RMB",
                }
                yield ProductPackage(**dd)
                if not dd['cost']:
                    continue
                yield RawSupplierQuotation(**product_package_to_raw_supplier_quotation(d, dd, self.name, self.name))
