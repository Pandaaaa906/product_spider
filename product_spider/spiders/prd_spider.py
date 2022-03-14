# coding=utf-8
import json
import re
from urllib.parse import urljoin

import scrapy
from scrapy import FormRequest
from scrapy.http.request import Request
from more_itertools import first

from product_spider.items import BestownPrdItem, RawData, SupplierProduct
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class BestownSpider(BaseSpider):
    name = "bestownprd"
    base_url = "http://bestown.net.cn/"
    start_urls = ["http://www.bestown.net.cn/?gallery-8.html"]

    def parse(self, response):
        prd_urls = response.xpath('//div[@class="items-list "]//h6/a/@href').extract()
        for prd_url in prd_urls:
            yield Request(prd_url, callback=self.detail_parse, headers=self.headers)
        next_page = response.xpath('//table[@class="pager"]//a[@class="next"]/@href').get(default=None)
        if next_page:
            yield Request(next_page, headers=self.headers)

    def detail_parse(self, response):
        prd_form = response.xpath('//form[@class="goods-action"]')
        tmp = prd_form.xpath('.//span[text()="cas编 号："]/../text()').get(default='')
        cas = first(re.findall(r'\d+-\d{2}-\d\b', tmp), None)
        d = {
            'chs_name': prd_form.xpath('./h1/text()').get(default=''),
            'en_name': prd_form.xpath('.//span[text()="英文名称："]/../text()').get(default=''),
            'country': prd_form.xpath('.//span[text()="生产国别："]/../text()').get(default=''),
            'brand': prd_form.xpath('.//span[text()="生产企业："]/../text()').get(default=''),
            'cas': cas,
            'unit': prd_form.xpath('.//span[text()="规格货号："]/../text()').get(default=''),
            'cat_no_unit': prd_form.xpath('.//span[@id="goodsBn"]/text()').get(default=''),
            'prd_type': prd_form.xpath('.//span[text()="产品类别："]/../text()').get(default=''),
            'stock': prd_form.xpath('.//span[text()="库存："]/../text()').get(default=''),
            'coupon': prd_form.xpath('.//span[@id="goodsScore"]/text()').get(default=''),
            'price': prd_form.xpath('.//span[@class="price1"]/text()').get(default=''),
            'url': response.url,
        }
        yield BestownPrdItem(**d)
        """
        for i in d.items():
            print('\t'.join(i))
        """


class NicpbpSpider(scrapy.Spider):
    name = "nicpbpprd"
    allowed_domains = ["nifdc.org.cn"]
    url = "http://app.nifdc.org.cn/sell/sgoodsQuerywaiw.do?formAction=queryGuestList"
    start_urls = [
        url,
    ]

    def empty_parse(self, response):
        pass

    def parse(self, response):
        prd_rows = response.xpath("//table[@class='list_tab003']//tr")
        for row in prd_rows:
            d = {
                'cat_no': row.xpath(".//td[1]/input/@value").get(default=""),
                'chs_name': row.xpath(".//td[2]/input/@value").get(default=""),
                'info2': row.xpath(".//td[3]/input/@value").get(default=""),
                'info1': row.xpath(".//td[4]/input/@value").get(default=""),  # 规格
                'info3': row.xpath(".//td[5]/input/@value").get(default=""),  # 批号
                'info4': row.xpath(".//td[6]/input/@value").get(default=""),  # 保存条件
                'stock_info': row.xpath(".//td[1]/font/text()").get(default=""),
            }
            yield RawData(**d)
        pager_script = response.xpath("//div[@class='page']/script/text()").re(r"(\d+),(\d+),(\d+)")
        if pager_script:
            cur_page, page_size, total_items = map(int, pager_script)
            if page_size * cur_page < total_items:
                data = [('sgoodsno', ''),
                        ('sgoodsname', ''),
                        ('curPage', str(cur_page + 1)),
                        ('pageSize', pager_script[1]),
                        ('toPage', pager_script[0]),
                        ]
                if cur_page == 1:
                    print("WWW", response.request.body)
                yield FormRequest.from_response(response, callback=self.parse, method="POST", formname="formList",
                                                formdata=data, dont_filter=True, errback=self.err_parse)

    # TODO Not Sure is a working spider
    def err_parse(self, failure):
        print(failure)


class DaltonSpider(BaseSpider):
    name = "dalton"
    allowed_domains = ["daltonresearchmolecules.com"]
    start_urls = ["https://www.daltonresearchmolecules.com/chemical-compounds-catalog", ]
    base_url = "https://www.daltonresearchmolecules.com"

    def parse(self, response):
        l_cat = response.xpath('//ul[@style="margin-left: 16px;"]/li/a')
        for cat in l_cat:
            url_cat = cat.xpath('./@href').get()
            catalog = cat.xpath('./text()').get()
            tmp_url = urljoin(self.base_url, url_cat)

            yield Request(tmp_url,
                          callback=self.cat_parse,
                          method="GET",
                          meta={'catalog': catalog}
                          )

    def cat_parse(self, response):
        rows = response.xpath('//form/div[@class="row"]/div')
        catalog = response.meta.get('catalog')
        for row in rows:
            name = row.xpath('./a/text()').get()
            url_prd = urljoin(self.base_url, row.xpath('./a/@href').get())
            mol_text = row.xpath('./div/div/object/param/@value').get()
            text = row.xpath('./div/div[contains(text(),"Purity")]/text()').getall()
            if not text:
                # Controlled Drugs
                continue
            purity = text[0].split(':', 1)[-1].strip()
            cat_no = text[1].split(':', 1)[-1].strip()
            cas = text[2].split(':', 1)[-1].strip()
            stock = text[3].split(':', 1)[-1].strip()
            mf = text[4].split(':', 1)[-1].strip()
            if mol_text:
                mol_text = mol_text.encode('u8').decode('unicode-escape')

            d = {
                'brand': 'dalton',
                'en_name': name,
                'prd_url': url_prd,  # 产品详细连接
                'mol_text': mol_text,
                'purity': purity,
                'cat_no': cat_no,
                'cas': cas,
                'stock_info': stock,
                'mf': mf,
                'parent': catalog,
            }
            yield RawData(**d)


class AozealSpider(BaseSpider):
    name = "aozeal"
    allowd_domains = ["aozeal.com"]
    start_urls = ["https://www.aozeal.com/shop-2/", ]
    base_url = "http://aozeal.com"

    def parse(self, response):
        categories = response.xpath('//ul[@class="product-categories"]/li/a')
        for cat in categories:
            cat_url = cat.xpath('./@href').get()
            parent_drug = cat.xpath('./text()').get()
            yield Request(cat_url, callback=self.list_parse, meta={"parent_drug": parent_drug})

    def list_parse(self, response):
        urls = response.xpath('//div[@class="hb-product-meta"]//a/@href').extract()
        for rel_url in urls:
            yield Request(url=urljoin(self.base_url, rel_url), callback=self.detail_parse, meta=response.meta)
        next_url = response.xpath('//a[@class="next page-numbers"]/@href').get()
        if next_url is None:
            return
        yield Request(url=next_url, callback=self.list_parse)

    def detail_parse(self, response):
        tmp_xpath = '//div[contains(@class, "summary entry-summary")]//span[text()={0!r}]/../following-sibling::span/text()'
        d = {
            'brand': "aozeal",
            'en_name': response.xpath('//h3[@itemprop="name"]//text()').get(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': response.xpath(tmp_xpath.format("Catalogue No.")).get(default=""),
            'cas': response.xpath(tmp_xpath.format("CAS No.")).get(default="N/A"),
            'mf': response.xpath(tmp_xpath.format("Mol. Formula")).get(default=""),
            'mw': response.xpath(tmp_xpath.format("Mol. Weight")).get(default=""),
            'stock_info': response.xpath(tmp_xpath.format("Stock Info")).get(default=None),
            'info1': "".join(response.xpath('//div[@id="tab-description"]//text()').extract()).strip(),
            'parent': response.meta.get("parent_drug"),
            'img_url': response.xpath('//figure//a/@href').get(),
        }
        yield RawData(**d)


# Dead website 20200522
class StannumSpider(BaseSpider):
    name = "stannum"
    start_urls = ("http://www.stannumusa.com/?page_id=13",)
    base_url = "http://www.stannumusa.com/"

    def parse(self, response):
        ref_urls = response.xpath('//ol/li/div//a/@href').extract()
        for ref_url in ref_urls:
            url = self.base_url + ref_url
            yield Request(url, callback=self.list_parse)

    def list_parse(self, response):
        parent = response.xpath('//h2[@class="art-postheader"]/text()').get()
        rows = response.xpath('//table//tr[position()>1]')
        for row in rows:
            mw = mf = None
            tmp = row.xpath('./td[4]/text()').extract()
            if len(tmp) >= 2:
                mw, *_, mf = tmp
            elif len(tmp) == 1:
                mw = tmp[0]
            item = {
                'brand': 'stannum',
                'parent': parent,
                'cat_no': row.xpath('./td/text()').get(),
                'en_name': ''.join(row.xpath('./td[2]/descendant::text()').extract()),
                'cas': row.xpath('./td[3]/descendant::text()').get(),
                'mw': mw,
                'mf': mf,
                'img_url': row.xpath('./td[5]/img/@src').get(),
            }
            yield RawData(**item)


class AcornSpider(BaseSpider):
    name = "acorn"
    start_urls = ["http://www.acornpharmatech.com/18501/index.html", ]
    base_url = "http://www.acornpharmatech.com"

    def parse(self, response):
        a_nodes = response.xpath('//table[@width="100%"]//tr//a')
        for a_node in a_nodes:
            parent = a_node.xpath('./img/@alt').get()
            href = a_node.xpath('./@href').get()
            if href is None or href.startswith('#'):
                continue
            yield Request(urljoin(self.base_url, href), callback=self.parse_list, meta={"parent": parent})

    def parse_list(self, response):
        rows = response.xpath('//td[@valign="top"]/table[not(@width)]//tr[position()>1]')
        parent = response.meta.get("parent", "")
        parent = parent.split(" - List")[0]

        for row in rows:
            cat_no = "".join(row.xpath('normalize-space(./td[1]//text())').extract()).strip() or None
            en_name = "".join(row.xpath('normalize-space(./td[3]/text())').extract()).strip() or None
            stock_info = row.xpath('normalize-space(./td[5]/descendant::text())').get()
            img_rel_url = row.xpath('./td[4]/img/@src').get()
            d = {
                "brand": "acorn",
                "parent": parent,
                "cat_no": cat_no,
                "cas": row.xpath('./td[2]/text()').get("N/A").strip(),
                "en_name": en_name,
                "info1": en_name,
                "img_url": img_rel_url and img_rel_url.replace("./..", self.base_url),
                "stock_info": stock_info and stock_info.strip(),
                "prd_url": response.url,
            }
            yield RawData(**d)


class HICSpider(BaseSpider):  # dead website 20200522
    name = "hic"
    start_urls = ["http://www.hi-chemical.com/parent-drug/", ]
    base_url = "http://www.hi-chemical.com/"

    def parse(self, response):
        tmp = "http://www.hi-chemical.com/?s={}&post_type=product"
        parents = response.xpath('//table[contains(@id,"table")]//tr[position()>1]/td/input/@value').extract()
        for parent in parents:
            yield Request(tmp.format(parent), meta={"parent": parent}, callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//div[@class="ContentDesc"]/a/@href').extract()
        for url in urls:
            yield Request(url, meta=response.meta, callback=self.detail_parse)

    def detail_parse(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td/text()'
        d = {
            "brand": "hic",
            "parent": response.meta.get("parent"),
            "cat_no": response.xpath('//h1[@class="header-post-title-class"]/text()').get(),
            "cas": response.xpath(tmp.format("CAS:")).get(),
            "en_name": response.xpath(tmp.format("Chemical name:")).get(),
            "info1": response.xpath(tmp.format("Synonyms:")).get(),
            "img_url": response.xpath('//div[@class="images"]//img/@src').get(),
            "mf": formula_trans(response.xpath(tmp.format("Molecular form:")).get()),
            "mw": response.xpath(tmp.format("Mol. Weight:")).get(),
            "prd_url": response.url,
            "stock_info": response.xpath('//div[@class="InventoryStatus"]/strong/text()').get(),
        }
        yield RawData(**d)


class CILSpider(BaseSpider):
    name = "cil"
    base_url = "https://shop.isotope.com/"
    start_urls = ["https://shop.isotope.com/category.aspx", ]

    def parse(self, response):
        urls = response.xpath('//div[@class="tcat"]//a/@href').extract()
        for url in urls:
            if "10032191" not in url:
                continue
            yield Request(url, callback=self.get_all_list)

    # There is one category having too much products, fetching all of them will cause timeout
    def get_all_list(self, response):
        x_query = '//form[@name="aspnetForm"]/div/input[@id="{0}"]/@value'
        d = {
            "ctl00_ToolkitScriptManager1_HiddenField": response.xpath(
                x_query.format("ctl00_ToolkitScriptManager1_HiddenField")).get(),
            "__EVENTTARGET": response.xpath(x_query.format("__EVENTTARGET")).get(),
            "__EVENTARGUMENT": response.xpath(x_query.format("__EVENTARGUMENT")).get(),
            "__LASTFOCUS": response.xpath(x_query.format("__LASTFOCUS")).get(),
            "__VIEWSTATE": response.xpath(x_query.format("__VIEWSTATE")).get(),
            "__VIEWSTATEENCRYPTED": response.xpath(x_query.format("__VIEWSTATEENCRYPTED")).get(),
            "__EVENTVALIDATION": response.xpath(x_query.format("__EVENTVALIDATION")).get(),
            "addtocartconfirmresult": "",
            "ctl00$topSectionctl$SearchBar1$txtkeyword": "Product Search...",
            "ctl00$cpholder$ctl00$ItemList1$SortByCtl$dbsort": "Name",
            "ctl00$cpholder$ctl00$ItemList1$PageSizectl$dlPageSize": "9999",
        }
        yield FormRequest(response.url, formdata=d, callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//td[@class="itemnotk"]/a/@href').extract()
        meta = {"parent": response.xpath('//td[@class="product_text"]/h3/text()').get()}
        for url in urls:
            yield Request(url, callback=self.detail_parse, meta=meta)
        x_query = '//form[@name="aspnetForm"]/div/input[@id="{0}"]/@value'
        next_page = response.xpath('//input[@class="pageon"]/following-sibling::input[1]/@value').get()
        if not next_page:
            return
        d = {
            "ctl00_ToolkitScriptManager1_HiddenField": response.xpath(
                x_query.format("ctl00_ToolkitScriptManager1_HiddenField")).get(),
            "__EVENTTARGET": response.xpath(x_query.format("__EVENTTARGET")).get(),
            "__EVENTARGUMENT": response.xpath(x_query.format("__EVENTARGUMENT")).get(),
            "__LASTFOCUS": response.xpath(x_query.format("__LASTFOCUS")).get(),
            "__VIEWSTATE": response.xpath(x_query.format("__VIEWSTATE")).get(),
            "__VIEWSTATEENCRYPTED": response.xpath(x_query.format("__VIEWSTATEENCRYPTED")).get(),
            "__EVENTVALIDATION": response.xpath(x_query.format("__EVENTVALIDATION")).get(),
            "addtocartconfirmresult": "",
            "ctl00$topSectionctl$SearchBar1$txtkeyword": "Product Search...",
            "ctl00$cpholder$ctl00$ItemList1$SortByCtl$dbsort": "Name",
            "ctl00$cpholder$ctl00$ItemList1$ctlPaging$btn2": next_page,
            "ctl00$cpholder$ctl00$ItemList1$PageSizectl$dlPageSize": "20",
        }
        yield FormRequest(response.url, formdata=d, callback=self.list_parse)

    def detail_parse(self, response):
        tmp = '//td[@class="dleft" and contains(./p/text(), "{}")]/following-sibling::td/p/text()'
        cas = response.xpath(tmp.format("Labeled CAS#")).get()
        unlabeled_cas = response.xpath(tmp.format("Unlabeled CAS#")).get()
        r_img_url = response.xpath('//div[@class="image-section"]/p//img/@src').get()
        d = {
            "brand": "cil",
            "parent": response.meta.get("parent"),
            "cat_no": response.xpath(tmp.format("Item Number")).get(),
            "cas": f"{cas}; Unlabeled Cas:{unlabeled_cas}",
            "en_name": response.xpath('//h1[@class="ldescription"]/text()').get(),
            "img_url": urljoin(response.url, r_img_url),
            "mf": formula_trans(response.xpath(tmp.format("Chemical Formula")).get()),
            "mw": response.xpath(tmp.format("Molecular Weight")).get(),
            "prd_url": response.url,
        }
        yield RawData(**d)


class DRESpider(BaseSpider):
    name = "dre"
    allowd_domains = ["lgcstandards.com"]
    start_urls = ["https://www.lgcstandards.com/US/en/search/?text=dre"]
    base_url = "https://www.lgcstandards.com/US/en"
    base_url_v2 = "https://www.tansoole.com/"
    search_url = "https://www.lgcstandards.com/lgccommercewebservices/v2/lgcstandards/products/search?"

    def start_requests(self):
        yield scrapy.Request(
            url='https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=dre%3A:itemtype:LGCProduct:itemtype:ATCCProduct&country=US&lang=en&defaultB2BUnit=',
            callback=self.parse,
        )

    def parse(self, response, **kwargs):
        products = json.loads(response.text).get("products")
        for prd in products:
            cat_no = prd.get("code")
            en_name = prd.get("name")
            img_url = prd.get("analyteImageUrl")
            prd_url = '{}{}'.format(self.base_url, prd.get("url"))
            if (mw := prd.get("listMolecularWeight")) is None:
                mw = []
            mw = ''.join(mw)
            if (mf := prd.get("listMolecularFormula")) is None:
                mf = ''.join([])
            else:
                mf = first(mf).replace(' ', '')

            if (cas := prd.get("listCASNumber")) is None:
                cas = []
            cas = ''.join(cas)
            d = {
                "brand": self.name,
                "cat_no": cat_no,
                "en_name": en_name,
                "mf": mf,
                "cas": cas,
                "mw": mw,
                "prd_url": prd_url,
                "img_url": img_url,
            }
            yield RawData(**d)
        # TODO
        for i in range(1, 190):
            yield scrapy.Request(
                url=f'https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage={i}&q=dre%3A:itemtype:LGCProduct:itemtype:ATCCProduct&country=US&lang=en&defaultB2BUnit=',
                callback=self.parse
            )
        yield scrapy.Request(
            url='https://www.tansoole.com/search/search.htm?gloabSearchVo.queryString=dre&gloabSearchVo.nav=1&t=0.10001398760159042&page.currentPageNo=1',
            callback=self.parse_list
        )

    def parse_list(self, response):
        """dre价格在泰坦官网获取"""
        rows = response.xpath("//ul[@class='show-list show-list-head']/following-sibling::ul/li[position()=1]")
        for row in rows:
            url = urljoin(self.base_url_v2, row.xpath("./a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_package
            )
        # 获取下一页
        next_url = response.xpath("//input[@value='下页']/@onclick").get()
        if next_url is not None:
            next_page_number = re.search(r'(?<==)\d+(?=;)', next_url).group()
            yield scrapy.Request(
                url=f"https://www.tansoole.com/search/search.htm?gloabSearchVo.queryString=dre&gloabSearchVo.nav=1&t=0.10001398760159042&page.currentPageNo={next_page_number}",
                callback=self.parse_list
            )

    def parse_package(self, response):
        chs_name = response.xpath("//div[@class='title']/text()").get()
        cat_no = response.xpath("//div[contains(text(), '原始编号：')]/following-sibling::div/text()").get()
        source_id = response.xpath("//div[contains(text(), '探索编号：')]/following-sibling::div/text()").get()
        img_url = urljoin(self.base_url_v2, response.xpath("//div[@id='big-box']/img/@src").get())
        package = response.xpath("//div[contains(text(), '包装规格：')]/following-sibling::div/text()").get('')
        if package is not None:
            package = ''.join(package.split())

        price = response.xpath("//span[@id='bigDecimalFormatPriceDesc']/text()").get()
        delivery = ''.join(response.xpath("//div[contains(text(), '货期：')]/following-sibling::div/span/text()").get('').split())
        stock_info = response.xpath("//div[contains(text(), '库存：')]/following-sibling::div/span/text()").get()
        expiry_date = response.xpath("//div[contains(text(), '有效期至：')]/following-sibling::div/text()").get()

        dd = {
            "brand": "dre",
            "cat_no": cat_no,
            "prd_url": response.url,
            "platform": "tansoole",
            "source_id": source_id,
            "img_url": img_url,
            "price": price,
            "chs_name": chs_name,
            "delivery": delivery,
            "stock_info": stock_info,
            "expiry_date": expiry_date,
            "package": package,
            "currency": "RMB",
        }

        yield SupplierProduct(**dd)


class APIChemSpider(BaseSpider):
    name = "apichem"
    base_url = "http://chemmol.com/chemmol/suppliers/apichemistry/texts.php"
    start_urls = [base_url, ]

    def parse(self, response):
        rows = response.xpath('//table[@class="tableborder"]//tr[position() mod 2=1]')
        first_cat_no = None
        for row in rows:
            en_name = row.xpath('./td/font/text()').get("").replace("Name:", "")
            rel_img_url = row.xpath('./following-sibling::tr[1]//img/@src').get()
            cat_no = row.xpath(
                './following-sibling::tr[1]//font[contains(text(), "Catalog No: ")]/text()').get().replace(
                "Catalog No: ", "").strip()
            if not first_cat_no:
                first_cat_no = cat_no
            d = {
                "brand": "apichem",
                "parent": None,
                "cat_no": cat_no,
                "en_name": en_name,
                "cas": row.xpath(
                    './following-sibling::tr[1]//font[contains(text(), "CAS No: ")]/text()').get().replace(
                    "CAS No: ", ""),
                "mf": None,
                "mw": None,
                "img_url": rel_img_url and urljoin(self.base_url, rel_img_url),
                "info1": en_name,
                "prd_url": response.request.url,
            }
            print(d)
            yield RawData(**d)
        next_page = response.xpath('//img[@src="/images/aaanext.gif"]/../@onclick').get("")
        if next_page:
            page = re.findall("\d+", next_page)[0]
            d = {
                "cdelete": "No",
                "page": page,
                "keywords": "",
                "mid": '30122898',
                "ucid": first_cat_no,
            }
            yield FormRequest(self.base_url, formdata=d, callback=self.parse)
