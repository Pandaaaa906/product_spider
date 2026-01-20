import json
import re
from urllib.parse import urljoin

import scrapy
from scrapy import FormRequest

from product_spider.items import ProductPackage, RawData, SupplierProduct, RawSupplierQuotation
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class TsbiochemSpider(BaseSpider):
    """陶术"""
    name = "tsbiochem"
    start_urls = ["https://www.tsbiochem.com/"]
    base_url = "https://www.tsbiochem.com/"
    img_base_url = 'https://cdn.targetmol.cn/'
    product_base_url = "https://www.targetmol.cn/"

    def parse(self, response, **kwargs):
        hrefs = response.xpath("//div[text()='生命科学产品']/following-sibling::div/a/@href").getall()
        if not hrefs:
            self.logger.warning("No first level category url!")
        hrefs.extend(['https://www.targetmol.cn/all-antibodies',
                      'https://www.targetmol.cn/all-molecular_and_cellular_research_reagents',
                      'https://www.targetmol.cn/all-disease-modeling',
                      'https://www.targetmol.cn/pathway/antibody_drug_conjugate_adc_related',
                      'https://www.targetmol.cn/all-dye-reagents',
                      'https://www.targetmol.cn/pathway/protac',
                      'https://www.targetmol.cn/standard'
                      ])
        hrefs = set(hrefs)
        for href in hrefs:
            yield scrapy.Request(
                url=urljoin(response.url, href),
                callback=self.parse_list
            )

        # TODO
        # 化合物库产品分类
        # library_catalog_hrefs = [s for s in hrefs if 'library' in s]
        # for href in library_catalog_hrefs:
        #     yield scrapy.Request(
        #         url=urljoin(response.url, href),
        #         callback=self.parse_library_list
        #     )

    custom_settings = {
        'RETRY_HTTP_CODES': [503, 504, 502],
        'RETRY_TIMES': 10,
    }

    def parse_detail(self, response):
        en_name = response.xpath(
            "//div[contains(@class,'product-info__center-header')]/h1//text()").get()
        chs_name = response.xpath(
            "//div[contains(@class,'product-info__center-catalogNo')]//span[contains(text(),'别名')]/b/text()").get()
        cat_no = response.xpath(
            "//div[contains(@class,'product-info__center-catalogNo')]//span[contains(text(),'货号')]/b/text()").get()
        if not cat_no:
            self.logger.warning(f"Cat_no not found, url:{response.url}")
            return

        introduction = response.xpath("//*[contains(@class,'product-description')]/text()").get()
        purity = response.xpath(
            "//div[contains(@class,'product-info__center-catalogNo')]//span[contains(text(),'密度')]/b/text()").get()
        cas = response.xpath(
            "//div[contains(@class,'product-info__center-catalogNo')]//span[contains(text(),'Cas号')]/b/text()"
            "|//td[contains(text(),'CAS')]/following-sibling::td[1]/text()").get()
        img_url: str = response.xpath("//div[@class='product-info__left-image']/img/@src").get()
        if img_url and not img_url.startswith('http'):
            img_url = urljoin(self.product_base_url, img_url)
        mw = response.xpath("//td[contains(text(), '分子量')]/following-sibling::td//text()").get()
        smiles = response.xpath("//td[contains(text(), 'Smiles')]/following-sibling::td//text()").get()
        stock_info = response.xpath("//td[contains(text(), '存储')]/following-sibling::td//text()").get()
        shipping_info = response.xpath("//td[contains(text(), '运输方式')]/following-sibling::td//text()").get()
        mf = ''.join(response.xpath("//td[contains(text(), '分子式')]/following-sibling::td//text()").getall())
        attrs = {
            'product_info': introduction
        }
        parent = response.xpath(
            "//nav[@class='ts-breadcrumb']/div[position()=last()-1]/text()").get() or response.meta.get('parent')
        if parent and (parent.lower() in ('其他', '其它', 'others')):
            all_parents = response.xpath("//nav[@class='ts-breadcrumb']/div//text()").getall()
            if len(all_parents) > 1:
                parent = '-'.join([x for x in all_parents[:-1] if x.lower() not in ('其他', '-', '其它', 'others')])
        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": parent,
            "en_name": en_name,
            'chs_name': chs_name,
            "purity": purity,
            "mw": mw,
            "mf": mf,
            "cas": cas,
            'smiles': smiles,
            "prd_url": response.url,
            "img_url": img_url,
            'stock_info': stock_info,
            'shipping_info': shipping_info,
            'attrs': json.dumps(attrs, ensure_ascii=False)
        }
        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        yield RawData(**d)
        yield SupplierProduct(**ddd)

        table_heads: list = response.xpath(
            "//div[contains(@class,'product-info__center-standard')]//table/thead/tr/th/text()").getall()
        if not table_heads:
            return

        package_index = table_heads.index("规格")
        stock_index = table_heads.index("库存")
        price_index = table_heads.index("价格")

        package_rows = response.xpath("//div[contains(@class,'product-info__center-standard')]//table/tbody/tr")
        for row in package_rows:
            if not (tds := row.xpath('./td')) or len(tds) <= max(stock_index, price_index, package_index):
                self.logger.warning(f"规格信息异常 prd_url:{response.url}")
                continue
            stock_num = tds[stock_index].xpath(".//text()").get()
            package = tds[package_index].xpath(".//text()").get()
            price = None
            if _ := tds[price_index].xpath(".//text()").get():
                price = _.strip("¥").replace(",", "")
            if package:
                package = package.replace(" ", "")
            dd = {
                'brand': self.name,
                'cat_no': cat_no,
                'package': package,
                'cost': price,
                'price': price,
                'currency': 'RMB',
                'stock_num': stock_num,
            }
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
            yield ProductPackage(**dd)
            yield RawSupplierQuotation(**dddd)

    def parse_library_list(self, response):
        hrefs = response.xpath("//div[@class='pro_lbylist']//a/@href").getall()
        parent = response.xpath("//div[@class='pro_secondary_intro']/h1/text()").get()
        for href in hrefs:
            yield scrapy.Request(url=urljoin(response.url, href), callback=self.parse_library_detail,
                                 meta={'parent': parent})

    # 化合物库产品详情
    def parse_library_detail(self, response):
        cat_no = response.xpath("//div[@class='product-details']//span[contains(text(),产品编号)]/b/text()"
                                "|//em[@id='productno_em']/text()").get()
        if not cat_no:
            self.logger.warning(f"Cat_no not found, url:{response.url}")

        chs_name = response.xpath(
            "//div[@class='product-details']//div/h1/strong/text()|//span[@id='productname_span']/text()").get()
        en_name = response.xpath(
            "//div[@class='product-details']//p[@style='font-size: smaller;']/text()"
            "|//div[@class='pro_des_container']//div[@class='catalog']/text()").get()
        introduction = ''.join(response.xpath("//div[@class='pro_detailed_description']//ul/li/text()").getall())
        compounds = response.xpath("//div[@class='chart-target-lby']/div/div[@class='text']//text()").getall()
        img_url = response.xpath("//div[@class='pro_base_box']//div[@class='pro_image pro_image_lib']/img/@src").get()
        attrs = {
            'compounds': compounds,
            'product_info': introduction,
        }
        d = {
            "brand": self.name,
            "cat_no": cat_no,
            'chs_name': chs_name,
            "parent": response.meta.get("parent"),
            "en_name": en_name,
            "prd_url": response.url,
            "img_url": img_url,
            'attrs': json.dumps(attrs, ensure_ascii=False)
        }
        yield RawData(**d)
        yield SupplierProduct(**rawdata_to_supplier_product(d, platform=self.name, vendor=self.name))

        package_script = response.xpath("//div[@class='pro_introduce pro_introduce_libarybox']/script").get()
        if (_ := re.findall(r'(?<==)\s*(.+)(?=;)', package_script)) and len(_) == 1:
            package_json = json.loads(_[0])
            pakages = package_json.get('list', [])
            for _p in pakages:
                price = _p.get('finalprice')
                packaging = _p.get('packagingtext', '').replace(' ', '')
                dd = {
                    "brand": self.name,
                    "cat_no": cat_no,
                    "package": packaging,
                    "cost": price,
                    "price": price,
                    "currency": "RMB",
                }
                yield ProductPackage(**dd)
                yield RawSupplierQuotation(**product_package_to_raw_supplier_quotation(d, dd, self.name, self.name))

    def parse_api_detail(self, response):
        if _data := response.json():
            _data = _data.get('data', {}).get('pros')
        if not _data:
            return
        for pro in _data:
            if (route := pro.get('route')) and (jumpurl := pro.get('jumpurl')):
                prd_url = urljoin(self.product_base_url, route + '/' + jumpurl)
                yield scrapy.Request(url=prd_url, callback=self.parse_detail, meta=response.meta)

    def parse_list(self, response):
        if 'text/html' not in str(response.headers['Content-Type']):
            self.logger.warning(f'response type is not html, url:{response.url}')
            return
        catalog_xpaths = ["//a[@class='results-content-name-card']/@href",
                          "//a[@class='rhombus']/@href", ]

        # 产品目录的url
        catalog_urls = [*response.xpath("|".join(catalog_xpaths)).getall()]
        if len(catalog_urls) > 0:
            for catalog_href in catalog_urls:
                yield scrapy.Request(urljoin(response.url, catalog_href), callback=self.parse_list)
            return

        if not (total_pages := response.xpath("//input[@aria-label='输入页码']/@max").get()):
            return
        total_pages = int(total_pages)
        parent = response.xpath("//div[contains(@class,'content-background')]/h1//text()").get()
        # product list paginator
        if raw_json := response.xpath('//script[@id="__NUXT_DATA__"]/text()').get():
            if match := re.search(r'(([0-9A-Z]+-){4}[0-9A-Z]+)', raw_json):
                if not (kind_id := match.group(1)):
                    self.logger.warning(f'kind id not found, url:{response.url}')
                    return
                kind_req_url = 'https://www.targetmol.cn/api/website2/web/search/kind'
                for i in range(1, total_pages + 1):
                    params = {
                        'page': i,
                        'kindId': kind_id
                    }
                    meta = {
                        'parent': parent
                    }
                    yield FormRequest(url=kind_req_url, method='POST',
                                      headers={'Content-Type': 'application/json', 'accept': 'application/json'},
                                      body=json.dumps(params), callback=self.parse_api_detail, meta=meta)
            else:
                self.logger.warning(f'kind id not found, url:{response.url}')
