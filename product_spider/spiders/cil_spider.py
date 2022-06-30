from urllib.parse import urljoin

import scrapy
from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class CILSpider(BaseSpider):
    name = "cil"
    base_url = "https://shop.isotope.com/"
    start_urls = ["https://shop.isotope.com/category.aspx", ]

    def parse(self, response, **kwargs):
        urls = response.xpath('//div[@class="tcat"]//a/@href').extract()
        for url in urls:
            if "10032191" not in url:
                continue
            yield scrapy.Request(url, callback=self.get_all_list)

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
        yield scrapy.FormRequest(response.url, formdata=d, callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//td[@class="itemnotk"]/a/@href').extract()
        meta = {"parent": response.xpath('//td[@class="product_text"]/h3/text()').get()}
        for url in urls:
            yield scrapy.Request(url, callback=self.detail_parse, meta=meta)
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
        yield scrapy.FormRequest(response.url, formdata=d, callback=self.list_parse)

    def detail_parse(self, response):
        tmp = '//td[@class="dleft" and contains(./p/text(), "{}")]/following-sibling::td/p/text()'
        cas = response.xpath(tmp.format("Labeled CAS#")).get()
        unlabeled_cas = response.xpath(tmp.format("Unlabeled CAS#")).get()
        r_img_url = response.xpath('//div[@class="image-section"]/p//img/@src').get()
        cat_no = response.xpath(tmp.format("Item Number")).get()
        d = {
            "brand": "cil",
            "parent": response.meta.get("parent"),
            "cat_no": cat_no,
            "cas": cas,
            "info1": f"Unlabeled Cas:{unlabeled_cas}",
            "en_name": response.xpath('//h1[@class="ldescription"]/text()').get(),
            "img_url": urljoin(response.url, r_img_url),
            "mf": formula_trans(response.xpath(tmp.format("Chemical Formula")).get()),
            "mw": response.xpath(tmp.format("Molecular Weight")).get(),
            "prd_url": response.url,
        }
        yield RawData(**d)
        rows = response.xpath("//tr[@class='ChildItemWrap']")
        for row in rows:
            cost = row.xpath("./td[position()=2]/span/text()").get()
            if cost is not None:
                cost = cost.replace('$', '')
            package = row.xpath("./td[position()=3]//span/span/text()").get()
            if package:
                package = package.replace(' ', '').lower()
            dd = {
                "brand": "cil",
                "cat_no": cat_no,
                "cost": cost,
                "package": package,
                "currency": "USD",
            }

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "parent": d["parent"],
                "en_name": d["en_name"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
                "prd_url": d["prd_url"],
            }
            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)
