# coding=utf-8
import re
from urllib.parse import urljoin

import scrapy
from scrapy import FormRequest
from scrapy.http.request import Request
from more_itertools import first

from product_spider.items import BestownPrdItem, RawData
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


# class DRESpider(BaseSpider):
#     name = "dre"
#     allowd_domains = ["lgcstandards.com"]
#     start_urls = ["https://www.lgcstandards.com/US/en/search/?text=dre"]
#     base_url = "https://www.lgcstandards.com/US/en"
#
#     def start_requests(self):
#         yield scrapy.Request(
#             url='https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage=0&q=dre%3A:itemtype:LGCProduct:itemtype:ATCCProduct&country=US&lang=en&defaultB2BUnit=',
#             callback=self.parse,
#         )
#
#     def parse(self, response, **kwargs):
#         products = json.loads(response.text).get("products", [])
#         if products is []:
#             return
#         for prd in products:
#             cat_no = prd.get("code")
#             en_name = prd.get("name")
#             img_url = prd.get("analyteImageUrl")
#             prd_url = '{}{}'.format(self.base_url, prd.get("url"))
#             if (mw := prd.get("listMolecularWeight")) is None:
#                 mw = []
#             mw = ''.join(mw)
#             if (mf := prd.get("listMolecularFormula")) is None:
#                 mf = ''.join([])
#             else:
#                 mf = first(mf).replace(' ', '')
#
#             if (cas := prd.get("listCASNumber")) is None:
#                 cas = []
#             cas = ''.join(cas)
#             d = {
#                 "brand": self.name,
#                 "cat_no": cat_no,
#                 "en_name": en_name,
#                 "mf": mf,
#                 "cas": cas,
#                 "mw": mw,
#                 "prd_url": prd_url,
#                 "img_url": img_url,
#             }
#             yield RawData(**d)
#         current_page_num = int(dict(parse_qsl(urlparse(response.url).query)).get('currentPage', None))
#         if current_page_num is not None:
#             current_page_num = current_page_num + 1
#             yield scrapy.Request(
#                 url=f'https://www.lgcstandards.com/US/en/lgcwebservices/lgcstandards/products/search?pageSize=100&fields=FULL&sort=code-asc&currentPage={current_page_num}&q=dre%3A:itemtype:LGCProduct:itemtype:ATCCProduct&country=US&lang=en&defaultB2BUnit=',
#                 callback=self.parse
#             )

