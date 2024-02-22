from string import ascii_uppercase
from urllib.parse import urljoin, urlencode
from scrapy import Request

from product_spider.items import RawData, SupplierProduct, ProductPackage, RawSupplierQuotation
from product_spider.utils.functions import strip, dumps
from product_spider.utils.items_translate import product_package_to_raw_supplier_quotation, rawdata_to_supplier_product
from product_spider.utils.maketrans import formula_trans
from product_spider.utils.spider_mixin import BaseSpider


class ClearsynthSpider(BaseSpider):
    name = "clearsynth"
    base_url = "https://www.clearsynth.com/"
    start_urls = [
        "https://www.clearsynth.com/products_categories?section=Categories"
    ]

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'PROXY_POOL_REFRESH_STATUS_CODES': [403, 500],
        'RETRY_TIMES': 10,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }

    def parse(self, response, **kwargs):
        categories = response.xpath('//a[starts-with(@href, "category")]//h5/text()').getall()
        for category in categories:
            category = category.replace(" ", "-")
            for a in ascii_uppercase:
                params = urlencode({"c": category, "api": a})
                yield Request(
                    f"https://www.clearsynth.com/categories?{params}",
                    callback=self.parse_category
                )

        searches = response.xpath('//a[starts-with(@href, "search?")]/@href').getall()
        for search in searches:
            yield Request(
                urljoin(response.url, search),
                callback=self.parse_search,
            )

    def parse_search(self, response):
        rel_urls = response.xpath('//div[contains(@class, "prodcut-title-name")]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(
                urljoin(response.url, rel_url),
                callback=self.parse_detail,
            )
        # TODO might not necessary
        next_page = response.xpath('//a[text()="Next >"]/@href').get()
        if next_page:
            yield Request(
                urljoin(response.url, next_page),
                callback=self.parse_search
            )

    def parse_category(self, response, **kwargs):
        rel_urls = response.xpath('//div[@class="auto-container"]//div[@class!="btn-box"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list)

    def parse_list(self, response):
        rel_urls = response.xpath('//a[@class="pr-name"]/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

    def parse_detail(self, response):
        tmp_xpath = "//*[contains(text(), {!r})]/following-sibling::td[last()]//text()"
        api_name = strip(response.xpath(tmp_xpath.format("Parent API")).get())
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

        yield Request(
            f"https://www.clearsynth.com/stockcheck.asp?catnumber={d['cat_no']}",
            callback=self.parse_detail_stock,
            meta={"prd": d}
        )

    def parse_detail_stock(self, response):
        d = response.meta.get("prd", {})
        d["stock_info"] = response.xpath('//text()').get()
        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, self.name, self.name)
        yield SupplierProduct(**ddd)
        params = {
            "catnumber": d['cat_no'],
            "compound": d['en_name'],
        }
        yield Request(
            f"https://www.clearsynth.com/pricing_22_ajax?{urlencode(params)}",
            callback=self.parse_package,
            meta={"prd": d}
        )

    def parse_package(self, response):
        d = response.meta.get("prd", {})

        rows = response.xpath('//table/input[@name="catnumber"]')
        for row in rows:
            qty = row.xpath('./following-sibling::input[@name="qty"]/@value').get()
            unit = row.xpath('./following-sibling::input[@name="unit"]/@value').get()
            package = None
            if isinstance(qty, str) and isinstance(unit, str):
                package = f"{qty}{unit}"
            dd = {
                "brand": self.name,
                "cat_no": d['cat_no'],
                "package": package,
                "cost": row.xpath('./following-sibling::input[@id="mprice1"]/@value').get(),
                "price": row.xpath('./following-sibling::input[@id="mprice2"]/@value').get(),
                "delivery_time": d.get("stock_info"),
                "currency": 'USD',

            }
            yield ProductPackage(**dd)
            if not dd.get("cost"):
                return
            dddd = product_package_to_raw_supplier_quotation(d, dd, self.name, self.name)
            yield RawSupplierQuotation(**dddd)
