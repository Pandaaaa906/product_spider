import re
from random import randint
from urllib.parse import urljoin

from scrapy import Request, FormRequest
from more_itertools import first

from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.functions import strip
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation


def parse_cost(raw_cost):
    if not raw_cost:
        return None
    cost = first(first(re.findall(r'(\d+(\.\d+)?)', raw_cost.replace(",", ''))), '')
    return cost


def parse_package(raw_package):
    if "/kit" in raw_package and "|" in raw_package:
        package = first(re.findall(r'(?<=\|) ?(.+)', raw_package), '')
        package = re.sub('(?<=\d) ', '', package)
    elif "|" in raw_package:
        package = first(re.findall(r'(?<=\|) ?([^/]+)', raw_package), '')
        package = re.sub('(?<=\d) ', '', package)
    elif "\d ?x ?\d" in raw_package:
        package = re.sub('\D*(\d+) ?x ?(\d+(\.\d+)?) ?([mMuUμkK]?[gGlL]).*', r'\1x\2\4', raw_package)
    elif "/kit" in raw_package:
        package = raw_package.replace('Analytical Standard', '')
    else:
        package = re.sub(r'\D*(\d+(\.\d+)?) ?([mMuUμkK]?[gGlL]).*', r'\1\3', raw_package)
    return package


# TODO the viewstate thing quite annoying
class CerilliantSpider(BaseSpider):
    name = "cerilliant"
    base_url = "https://www.cerilliant.com/"
    start_urls = ["https://www.cerilliant.com/products/catalog.aspx", ]

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//table[@class="hyperLnkBlackNonUnderlineToBlue"]//a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def get_d(self, response):
        ret = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__VIEWSTATE': response.xpath('//input[@id="__VIEWSTATE"]/@value').get(),
            '__VIEWSTATEGENERATOR': response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').get(),
            '__PREVIOUSPAGE': response.xpath('//input[@id="__PREVIOUSPAGE"]/@value').get(),
            '__SCROLLPOSITIONX': '0',
            '__SCROLLPOSITIONY': '0',
            '__VIEWSTATEENCRYPTED': '',
            'ctl00$txtBoxSearch': '',
            'ctl00$ContentPlaceHolder1$txtSearchCat': '',
            'ctl00$ContentPlaceHolder1$ph_ControlHandler': '',
            'ctl00$ContentPlaceHolder1$ph_EventType': '',
        }
        for i in range(2, 27):
            ret[f'ctl00$ContentPlaceHolder1$gvProdCatList$ctl{i:0>2}$txtQty'] = '1'
        return ret

    def parse_list(self, response):
        rel_urls = response.xpath('//table[@id="ContentPlaceHolder1_gvProdCatList"]//td/a/@href').getall()
        parent = response.meta.get('parent')
        page = response.meta.get('page', 1)
        for rel in rel_urls:
            target = first(re.findall(r"doPostBack\(\'([^\']+)\'", rel), None)
            d = self.get_d(response)
            d['__EVENTTARGET'] = target
            d['ctl00$ContentPlaceHolder1$gvProdCatList$ctl28$gvProdCatListPages'] = str(page)
            yield FormRequest(response.url, formdata=d, callback=self.parse_detail, meta={'parent': parent})

        next_page = response.xpath('//option[@selected]/following-sibling::option/text()').get()
        if next_page:
            d = self.get_d(response)
            d['ctl00$ContentPlaceHolder1$gvProdCatList$ctl28$gvProdCatListPages'] = str(page)
            d['ctl00$ContentPlaceHolder1$gvProdCatList$ctl28$NextButton.x'] = str(randint(0, 10))
            d['ctl00$ContentPlaceHolder1$gvProdCatList$ctl28$NextButton.y'] = str(randint(0, 10))
            yield FormRequest(response.url, formdata=d, callback=self.parse_list,
                              meta={'parent': parent, 'page': next_page}
                              )

    def parse_detail(self, response):
        tmp = '//span[@id={!r}]//text()'
        concentration = response.xpath(tmp.format("ContentPlaceHolder1_lblDescriptionSize")).get()
        package = response.xpath(tmp.format("ContentPlaceHolder1_lblBodyUnitSize")).get('')
        cat_no = response.xpath(tmp.format("ContentPlaceHolder1_lblItemNumber")).get('')
        cat_no, *_ = cat_no.split('/')
        rel_img = response.xpath('//img[@id="ContentPlaceHolder1_imgChemStructPicture"]/@src').get()
        d = {
            'brand': 'cerilliant',
            'parent': response.meta.get('parent'),
            'cat_no': strip(cat_no),
            'en_name': ''.join(response.xpath(tmp.format("ContentPlaceHolder1_lblProduct")).getall()),
            'cas': response.xpath(tmp.format("ContentPlaceHolder1_lblBodyCASNumber")).get(),
            'mw': response.xpath(tmp.format("ContentPlaceHolder1_lblBodyMolecularWeight")).get(),
            'mf': ''.join(response.xpath(tmp.format("ContentPlaceHolder1_lblBodyChemicalFormula")).getall()),
            'info3': ''.join(filter(lambda x: x, (concentration, package))),
            'info4': response.xpath(tmp.format("ContentPlaceHolder1_lblBodyUSListPrice")).get(),
            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }

        package = parse_package(d["info3"])
        cost = parse_cost(d["info4"])

        dd = {
            "brand": d["brand"],
            "cat_no": d["cat_no"],
            "package": package,
            "cost": cost,
            "currency": "USD",
        }
        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id": f'{self.name}_{d["cat_no"]}_{dd["package"]}',
            "parent": d["parent"],
            "cas": d["cas"],
            "mf": d["mf"],
            "mw": d["mw"],
            "en_name": d["en_name"],
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'cost': dd['cost'],
            "currency": dd["currency"],
            "img_url": d["img_url"],
            "prd_url": d["prd_url"],
        }
        dddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id": f'{self.name}_{d["cat_no"]}',
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'discount_price': dd['cost'],
            'price': dd['cost'],
            'cas': d["cas"],
            'currency': dd["currency"],
        }

        yield RawData(**d)
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)
