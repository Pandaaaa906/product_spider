from string import ascii_uppercase
from urllib.parse import urljoin
from scrapy import Request

from product_spider.items import RawData, SupplierProduct
from product_spider.utils.functions import strip, dumps
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class ClearsynthSpider(BaseSpider):
    name = "clearsynth"
    base_url = "https://www.clearsynth.com/"
    start_urls = [
        f"https://www.clearsynth.com/categories?c=&api={c}" for c in ascii_uppercase
    ]

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//div[@class="auto-container"]//div[@class!="btn-box"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list)

    def parse_list(self, response):
        rel_urls = response.xpath('//td[@data-column="PRODUCT"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

    def parse_detail(self, response):
        tmp_xpath = "//*[contains(text(), {!r})]/following-sibling::td[last()]//text()"
        api_name = response.xpath(tmp_xpath.format("Parent API")).get()
        img_url = response.xpath('//a[@class="lightbox-image"]/img/@src').get()

        prd_attrs = {
            "api_name": api_name,
            "category": response.xpath(tmp_xpath.format("Category")).get(),
            "inchl": response.xpath(tmp_xpath.format('Inchl')).get(),
            "iupac": response.xpath(tmp_xpath.format('IUPAC')).get(),
            "inchlkey": response.xpath(tmp_xpath.format('InchIKey')).get(),
            "hazardous": strip(response.xpath(tmp_xpath.format('Hazardous')).get()),
            "controlled_substance": response.xpath(tmp_xpath.format('Controlled Substance')).get(),
        }
        prd_attrs = {k: v for k, v in prd_attrs.items() if v}

        smiles = response.xpath(tmp_xpath.format('Smileys')).get()
        smiles = smiles or response.xpath(tmp_xpath.format('Smiles')).get()
        smiles = smiles or response.xpath(tmp_xpath.format('Canonical Smiles')).get()

        d = {
            "brand": self.name,
            "en_name": response.xpath(tmp_xpath.format('Product')).get(),
            "cat_no": strip(response.xpath(tmp_xpath.format('CAT No.')).get()),
            "cas": strip(response.xpath(tmp_xpath.format('CAS No.')).get()),
            "parent": api_name,
            "mw": strip(response.xpath(tmp_xpath.format('Mol. Wt.')).get()),
            "mf": strip(formula_trans(''.join(response.xpath(tmp_xpath.format('Mol. For.')).getall()))),
            "purity": response.xpath(tmp_xpath.format('Purity')).get(),
            "smiles": smiles,
            "info1": strip(response.xpath(tmp_xpath.format('Synonyms')).get()),
            "info2": strip(response.xpath(tmp_xpath.format('Storage Condition')).get()),
            "stock_info": strip(response.xpath(tmp_xpath.format("Status")).get()),
            "attrs": dumps(prd_attrs),
            "img_url": img_url and urljoin(response.url, img_url),
            "prd_url": response.url,
        }
        yield RawData(**d)

        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id": f'{self.name}_{d["cat_no"]}',
            "parent": d["parent"],
            "en_name": d["en_name"],
            "cas": d["cas"],
            "smiles": d["smiles"],
            "mf": d["mf"],
            "mw": d["mw"],
            'cat_no': d["cat_no"],
            "img_url": d["img_url"],
            "prd_url": d["prd_url"],
        }
        yield SupplierProduct(**ddd)
