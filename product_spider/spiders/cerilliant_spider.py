import re
from random import randint
from urllib.parse import urljoin

from scrapy import Request, FormRequest
from more_itertools import first

from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.functions import strip
from product_spider.items import RawData


# TODO the viewstate thing quite annoying
class CerilliantSpider(BaseSpider):
    name = "cerilliant"
    base_url = "https://www.cerilliant.com/"
    start_urls = ["https://www.cerilliant.com/products/catalog.aspx", ]

    def parse(self, response):
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
            'brand': 'Cerilliant',
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
        yield RawData(**d)
