# coding=utf-8
import json
import re
from string import ascii_uppercase as uppercase
from time import time
from urllib.parse import urljoin, urlencode

import scrapy
from scrapy import FormRequest
from scrapy.http.request import Request
from more_itertools import first

from product_spider.items import JkItem, BestownPrdItem, RawData
from product_spider.utils.maketrans import formular_trans
from product_spider.utils.spider_mixin import BaseSpider


class JkPrdSpider(scrapy.Spider):
    name = "jk"
    allowed_domains = ["jkchemical.com"]
    base_url = "http://www.jkchemical.com"
    start_urls = map(lambda x: "http://www.jkchemical.com/CH/products/index/ProductName/{0}.html".format(x),
                     uppercase)
    prd_size_url = "http://www.jkchemical.com/Controls/Handler/GetPackAgeJsonp.ashx?callback=py27&value={value}&cid={cid}&type=product&_={ts}"

    def parse(self, response):
        for xp_url in response.xpath("//div[@class='yy toa']//a/@href"):
            tmp_url = self.base_url + xp_url.extract()
            yield Request(tmp_url.replace("EN", "CH"), callback=self.parse_prd)

    def parse_prd(self, response):
        xp_boxes = response.xpath("//table[@id]//div[@class='PRODUCT_box']")
        for xp_box in xp_boxes:
            div = xp_box.xpath(".//div[2][@class='left_right mulu_text']")
            l_chs_name = xp_box.xpath(".//a[@class='name']//span[1]/text()").extract()
            if l_chs_name:
                chs_name = l_chs_name[0].strip()
            else:
                chs_name = ""
            try:
                d = {"purity": div.xpath(".//li[1]/text()").extract()[0].split(u"：")[-1].strip(),
                     "cas": div.xpath(".//li[2]//a/text()").extract()[0].strip(),
                     "cat_no": div.xpath(".//li[4]/text()").extract()[0].split(u"：")[-1].strip(),
                     "en_name": xp_box.xpath(".//a[@class='name']/text()").extract()[0].strip(),
                     "chs_name": chs_name,
                     }
            except:
                print("WWW", xp_box.xpath(".//a[@class='name']//span/text()").extract())
                print("WRONG PARSER??", response.url)
            data_jkid = xp_box.xpath(".//div[@data-jkid]/@data-jkid").extract()[0]
            data_cid = xp_box.xpath(".//div[@data-cid]/@data-cid").extract()[0]
            yield Request(self.prd_size_url.format(value=data_jkid, cid=data_cid, ts=int(time())),
                          body=u"",
                          meta={"prd_data": d},
                          callback=self.parse_s)

    def parse_s(self, response):
        s = re.findall(r"(?<=\().+(?=\))", response.text)[0]
        l_package_objs = json.loads(s)
        for package_obj in l_package_objs:
            d = {"package": package_obj["_package"],
                 "price": package_obj["_listPrice"],
                 }
            d.update(response.meta.get('prd_data', {}))
            jkitem = JkItem(**d)
            yield jkitem


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
                'brand': 'Dalton',
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
            'brand': "Aozeal",
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


# TODO untested
class TRCSpider(BaseSpider):
    name = "trc"
    allow_domain = ["trc-canada.com", ]
    start_urls = ["https://www.trc-canada.com/parent-drug/", ]
    search_url = "https://www.trc-canada.com/products-listing/?"
    base_url = "https://www.trc-canada.com"

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS_PER_IP': 2,
    }

    def parse(self, response):
        api_names = response.xpath('//table[contains(@id, "table")]//td/input/@value').extract()
        for api_name in api_names:
            d = {
                "searchBox": api_name,
                "type": "searchResult",
            }
            url = self.search_url + urlencode(d)
            yield Request(url=url, callback=self.list_parse, meta={"parent": api_name})

    def list_parse(self, response):
        rel_urls = response.xpath(
            '//div[@class="chemCard"]/a[not(@data-lity)]/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse, meta=response.meta)

    def detail_parse(self, response):
        tmp_format = '//td[contains(text(), {!r})]/following-sibling::td/text()'
        item = {
            "brand": "TRC",
            'parent': response.meta.get("parent", None),
            "en_name": response.xpath(tmp_format.format('Chemical Name:')).get(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': response.xpath('//div[@class="post-title-wrapper"]/h1/text()').get(),
            'cas': response.xpath(tmp_format.format('CAS Number:')).get(),
            'mf': formular_trans(response.xpath(tmp_format.format('Molecular Formula:')).get()),
            'mw': response.xpath(tmp_format.format('Molecular Weight:')).get(),
            'img_url': self.base_url + response.xpath('//div[@id="productImage"]/img/@src').get(),
            'stock_info': response.xpath('//b[text()="Inventory Status : "]/../text()').get(),
            'info1': response.xpath(tmp_format.format('Synonyms:')).get(),
        }
        yield RawData(**item)


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
                'brand': 'Stannum',
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
                "brand": "Acorn",
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
            "brand": "HIC",
            "parent": response.meta.get("parent"),
            "cat_no": response.xpath('//h1[@class="header-post-title-class"]/text()').get(),
            "cas": response.xpath(tmp.format("CAS:")).get(),
            "en_name": response.xpath(tmp.format("Chemical name:")).get(),
            "info1": response.xpath(tmp.format("Synonyms:")).get(),
            "img_url": response.xpath('//div[@class="images"]//img/@src').get(),
            "mf": formular_trans(response.xpath(tmp.format("Molecular form:")).get()),
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
            "brand": "CIL",
            "parent": response.meta.get("parent"),
            "cat_no": response.xpath(tmp.format("Item Number")).get(),
            "cas": f"{cas}; Unlabeled Cas:{unlabeled_cas}",
            "en_name": response.xpath('//h1[@class="ldescription"]/text()').get(),
            "img_url": urljoin(response.url, r_img_url),
            "mf": formular_trans(response.xpath(tmp.format("Chemical Formula")).get()),
            "mw": response.xpath(tmp.format("Molecular Weight")).get(),
            "prd_url": response.url,
        }
        yield RawData(**d)


class DRESpider(BaseSpider):
    name = "dre"
    allowd_domains = ["lgcstandards.com"]
    start_urls = [
        "https://www.lgcstandards.com/lgccommercewebservices/v2/lgcstandards/categories/279492/products?currentPage=1&q=&sort=relevance-code&pageSize=20&country=CN&lang=en&fields=FULL", ]
    base_url = "https://www.lgcstandards.com/CN/en"
    search_url = "https://www.lgcstandards.com/lgccommercewebservices/v2/lgcstandards/products/search?"

    def parse(self, response):
        total_page = int(response.xpath('//pagination/totalPages/text()').get())
        cur_page = int(response.xpath('//pagination/currentPage/text()').get())
        per_page = int(response.xpath('//pagination/pageSize/text()').get())
        next_page = cur_page + 1

        products = response.xpath('//products')

        for product in products:
            url = product.xpath('./url/text()').get()
            yield Request(url=self.base_url + url, callback=self.detail_parse)

        if next_page <= total_page:
            data = {
                "currentPage": next_page,
                "q": "DRE",  # INFO hardcoding
                "sort": "relevance",
                "pageSize": per_page,
                "country": "CN",
                "lang": "en",
                "fields": "FULL",
            }
            yield Request(self.search_url + urlencode(data), callback=self.parse)

    def detail_parse(self, response):
        tmp = '//div[contains(@class,"product__item")]/h2[text()={!r}]/following-sibling::*/descendant-or-self::text()'
        parents = response.xpath(
            '//div[contains(@class,"product page-section")]//div[contains(@class,"product__item")]/h2[contains(text(),"API Family")]/following-sibling::*/descendant-or-self::text()').extract()
        parent = "".join(parents)
        related_categories = response.xpath(
            '//ul[contains(@class,"breadcrumb")]/li[position()=last()-1]/a/text()').get(default="").strip()

        color = response.xpath('//h2[text()="Color"]/following-sibling::p/text()').get("")
        appearance = response.xpath('//h2[text()="Appearance/Form"]/following-sibling::p/text()').get("")
        d = {
            "brand": "DRE",
            "parent": parent or related_categories,
            "cat_no": response.xpath(tmp.format("Product Code")).get(),
            "en_name": response.xpath('//h1[@class="product__title"]/text()').get(default="").strip(),
            "cas": response.xpath(tmp.format("CAS Number")).get(default="").strip() or None,
            "mf": response.xpath(tmp.format("Molecular Formula")).get("").replace(" ", "") or None,
            "mw": response.xpath(tmp.format("Molecular Weight")).get(),
            "stock_info": response.xpath(
                '//h4[contains(@class,"orderbar__stock-title")]/descendant-or-self::text()').get(
                "").strip() or None,
            "img_url": response.xpath('//div[contains(@class, "product__brand-img")]/img/@src').get(),
            "info1": response.xpath(tmp.format("IUPAC")).get(default="").strip(),
            "info2": response.xpath('//h2[text()="Storage Temperature"]/following-sibling::p/text()').get(),
            "info3": response.xpath('//h2[text()="Shipping Temperature"]/following-sibling::p/text()').get(),
            "info4": ' '.join((color, appearance)),
            "prd_url": response.request.url,
        }

        yield RawData(**d)


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
                "brand": "APIChem",
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


