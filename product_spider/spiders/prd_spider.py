# coding=utf-8
import json
import re
import string
from itertools import chain
from string import ascii_uppercase as uppercase, ascii_uppercase
from time import time
from urllib.parse import urljoin, urlencode, splitquery, parse_qsl

import scrapy
from scrapy import FormRequest
from scrapy.http.request import Request
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError, TCPTimedOutError

from product_spider.items import JkItem, BestownPrdItem, RawData
from product_spider.utils.drug_list import drug_pattern
from product_spider.utils.functions import strip
from product_spider.utils.maketrans import formular_trans


class BaseSpider(scrapy.Spider):
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, sdch, br",
        "accept-language": "zh-CN,zh;q=0.8",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    }


class JkPrdSpider(scrapy.Spider):
    name = "jk_prds"
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


class AccPrdSpider(BaseSpider):
    name = "acc_prds"
    allowed_domains = ["accustandard.com"]
    base_url = "https://www.accustandard.com"
    start_urls = ["https://www.accustandard.com/organic.html?limit=100",
                  "https://www.accustandard.com/petrochemical.html?limit=100",
                  "https://www.accustandard.com/inorganic.html?limit=100",
                  ]

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS_PER_IP': 2,
    }

    def parse(self, response):
        prd_urls = response.xpath(
            '//ol[contains(@class,"products-list")]/li//h2[@class="product-name"]/a/@href').extract()
        for prd_url in prd_urls:
            yield Request(prd_url, callback=self.detail_parse)

        next_page_url = response.xpath('//div[@class="pager"]//a[@class="next i-next"]/@href').extract_first()
        if next_page_url is not None:
            yield Request(next_page_url, method="GET", callback=self.parse)

    def detail_parse(self, response):
        d = {
            "brand": "AccuStandard",
            "parent": response.xpath('//div[@class="breadcrumbs"]//li[2]/a/span/text()').extract_first(),
            "cat_no": response.xpath('//div[@itemprop="productID"]/text()').extract_first(),
            "en_name": response.xpath('//div[@class="product-name"]//span[@itemprop="name"]/text()').extract_first(),
            "cas": ";".join(
                response.xpath('//table[@class="analytetable"]//td[contains(@class, "cas_number")]/text()').extract()),
            "mf": "".join(response.xpath(
                '//span[contains(text(), "Molecular Formula")]/../following-sibling::div[1]//text()').extract()) or None,
            "mw": response.xpath(
                '//span[contains(text(), "Molecular Weight")]/../following-sibling::div[1]//text()').extract_first(),
            "stock_info": response.xpath('//meta[@itemprop="availability"]/@content').extract_first(),
            "img_url": response.xpath('//img[@itemprop="image"]/@src').extract_first(),
            "info2": response.xpath(
                '//span[contains(text(), "Unit")]/../following-sibling::div[1]//text()').extract_first(),
            "info3": response.xpath(
                '//span[contains(text(), "Storage Condition")]/../following-sibling::div[1]//text()').extract_first(),
            "info4": response.xpath('//span[@class="price"]/text()').extract_first(),
            "prd_url": response.url,
        }
        yield RawData(**d)


# TODO Get Blocked
class ChemServicePrdSpider(BaseSpider):
    name = "chemsrvprd"
    base_url = "https://www.chemservice.com/"
    start_urls = ["https://www.chemservice.com/store.html?limit=100", ]
    handle_httpstatus_list = [500, ]

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS_PER_IP': 2,
    }

    def start_requests(self):
        yield Request(url=self.base_url, headers=self.headers, callback=self.home_parse)
        for item in self.start_urls:
            yield Request(url=item, headers=self.headers, callback=self.parse)

    def home_parse(self, response):
        self.headers["referer"] = response.url

    def parse(self, response):
        x_urls = response.xpath('//h2[@class="product-name"]/a/@href').extract()
        with open('html', 'w') as f:
            f.write(response.body_as_unicode())
        self.headers['referer'] = response.url
        for url in x_urls:
            yield Request(url, callback=self.prd_parse, headers=self.headers)
            break

    def prd_parse(self, response):
        tmp_d = {
            "name": response.xpath('//div[@itemprop="name"]/h1/text()').extract(),
            "cat_no": response.xpath('//div[@itemprop="name"]/div[@class="product-sku"]/span/text()').extract(),
            "cas": response.xpath('//div[@itemprop="name"]/div[@class="product-cas"]/span/text()').extract(),
            "unit": response.xpath('//span[@class="size"]/text()').extract(),
            "price": response.xpath('//span[@class="price"]/text()').extract(),
            "stock_available": response.xpath('//p[@class="avail-count"]/span/text()').extract(),
            "catalog": response.xpath(
                '//table[@id="product-attribute-specs-table"]//tr/th/text()[contains(.,"Classification")]/../../td/text()').extract(),
            "synonyms": response.xpath(
                '//table[@id="product-attribute-specs-table"]//tr/th/text()[contains(.,"Alternate")]/../../td/text()').extract(),
            "shipment": response.xpath('//p[contains(@class, "availability")]/span/text()')
        }
        d = dict()
        d["url"] = response.url
        for k, v in tmp_d.items():
            d[k] = v and v[0] or "N/A"
        concn_solv = response.xpath(
            '//table[@id="product-attribute-specs-table"]//tr/th/text()[contains(.,"Concentration")]/../../td/text()').extract()
        if concn_solv:
            tmp = concn_solv[0].split('in')
            d['concn'] = tmp[0].strip()
            d['solv'] = tmp[1].strip()
        else:
            d['concn'] = "N/A"
            d['solv'] = "N/A"
        for k, v in tmp_d.items():
            print(k, v)


class CDNPrdSpider(BaseSpider):
    name = "cdn_prds"
    base_url = "https://cdnisotopes.com/"
    start_urls = [
        "https://cdnisotopes.com/nf/alphabetlist/view/list/?char=ALL&limit=50", ]

    def parse(self, response):
        urls = response.xpath('//ol[@id="products-list"]/li/div[@class="col-11"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin(self.base_url, url), callback=self.detail_parse)
        next_page = response.xpath('//div[@class="pages"]//li[last()]/a/@href').extract_first()
        if next_page:
            yield Request(urljoin(self.base_url, next_page), callback=self.parse)

    # TODO Stock information (actually all product info) is described in the page js var matrixChildrenProducts
    def detail_parse(self, response):
        tmp = '//th[contains(text(),{0!r})]/following-sibling::td/descendant-or-self::text()'
        img_url = response.xpath('//th[contains(text(),"Structure")]/following-sibling::td/img/@src').extract_first()
        d = {
            "brand": "CDN",
            "cat_no": response.xpath(tmp.format("Product No.")).extract_first(),
            "parent": response.xpath(tmp.format("Category")).extract_first(),
            "info1": "".join(response.xpath(tmp.format("Synonym(s)")).extract()),
            "mw": response.xpath(tmp.format("Molecular Weight")).extract_first(),
            "mf": "".join(response.xpath(tmp.format("Formula")).extract()),
            "cas": response.xpath(tmp.format("CAS Number")).extract_first(),
            "en_name": strip(
                "".join(response.xpath('//div[@class="product-name"]/span/descendant-or-self::text()').extract())),
            "img_url": img_url and urljoin(self.base_url, img_url),
            "stock_info": response.xpath(
                '//table[@id="product-matrix"]//td[@class="unit-price"]/text()').extract_first(),
            "prd_url": response.url,
        }
        yield RawData(**d)


class BestownSpider(BaseSpider):
    name = "bestownprd"
    base_url = "http://bestown.net.cn/"
    start_urls = ["http://www.bestown.net.cn/?gallery-25.html"]

    def parse(self, response):
        prd_urls = response.xpath('//div[@class="items-list "]//h6/a/@href').extract()
        for prd_url in prd_urls:
            yield Request(prd_url, callback=self.detail_parse, headers=self.headers)
        next_page = response.xpath('//table[@class="pager"]//a[@class="next"]/@href').extract_first(default=None)
        if next_page:
            yield Request(next_page, headers=self.headers)

    def detail_parse(self, response):
        prd_form = response.xpath('//form[@class="goods-action"]')
        d = {
            'chs_name': prd_form.xpath('./h1/text()').extract_first(default=''),
            'en_name': prd_form.xpath('.//span[text()="英文名称："]/../text()').extract_first(default=''),
            'country': prd_form.xpath('.//span[text()="生产国别："]/../text()').extract_first(default=''),
            'brand': prd_form.xpath('.//span[text()="生产企业："]/../text()').extract_first(default=''),
            'unit': prd_form.xpath('.//span[text()="规格货号："]/../text()').extract_first(default=''),
            'cat_no_unit': prd_form.xpath('.//span[@id="goodsBn"]/text()').extract_first(default=''),
            'prd_type': prd_form.xpath('.//span[text()="产品类别："]/../text()').extract_first(default=''),
            'stock': prd_form.xpath('.//span[text()="库存："]/../text()').extract_first(default=''),
            'coupon': prd_form.xpath('.//span[@id="goodsScore"]/text()').extract_first(default=''),
            'price': prd_form.xpath('.//span[@class="price1"]/text()').extract_first(default=''),
        }
        yield BestownPrdItem(**d)
        """
        for i in d.items():
            print('\t'.join(i))
        """


class TLCSpider(BaseSpider):
    name = "tlc_prds"
    base_url = "http://tlcstandards.com/"
    start_urls = map(lambda x: "http://tlcstandards.com/ProductsRS.aspx?type={}&cpage=1".format(x), ascii_uppercase)
    x_template = './child::br[contains(following-sibling::text(),"{0}")]/following-sibling::font[1]/text()'

    custom_settings = {
        'CONCURRENT_REQUESTS': 32,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 64,
        'CONCURRENT_REQUESTS_PER_IP': 64,
    }

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="information"]/a/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse)
        next_page = response.xpath('//a[@class="nextPage" and text()="▶"]').extract_first()
        if next_page:
            url, q = splitquery(response.url)
            d = dict(parse_qsl(q))
            d['cpage'] = int(d.get('cpage', 0)) + 1
            q = urlencode(d)
            yield Request('?'.join((url, q)), callback=self.parse)

    @staticmethod
    def extract_value(response, title):
        ret = response.xpath(f'//p[text()={title!r}]/../following-sibling::td/p/descendant-or-self::text()').extract()
        return "".join(ret) or None

    def detail_parse(self, response):
        img_src = response.xpath('//section[@class="page"][1]//img/@src').extract_first()
        d = {
            'en_name': self.extract_value(response, "Compound Name:"),
            'cat_no': self.extract_value(response, "Catalogue Number:"),
            'img_url': img_src and urljoin(self.base_url, img_src),
            'info1': self.extract_value(response, "Synonyms:"),
            'cas': self.extract_value(response, "CAS#:"),
            'mw': self.extract_value(response, "Molecular Weight:"),
            'mf': self.extract_value(response, "Molecular Formula:"),
            'parent': response.xpath('//section[@class="page"][1]//h3[@class="title--product"]/text()').extract_first(
                default="").title() or None,
            'brand': 'TLC',
            'prd_url': response.request.url,
            'stock_info': response.xpath('//span[@class="status"]/text()').extract_first("").strip().title() or None,
        }
        yield RawData(**d)


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
                'cat_no': row.xpath(".//td[1]/input/@value").extract_first(default=""),
                'chs_name': row.xpath(".//td[2]/input/@value").extract_first(default=""),
                'info2': row.xpath(".//td[3]/input/@value").extract_first(default=""),
                'info1': row.xpath(".//td[4]/input/@value").extract_first(default=""),  # 规格
                'info3': row.xpath(".//td[5]/input/@value").extract_first(default=""),  # 批号
                'info4': row.xpath(".//td[6]/input/@value").extract_first(default=""),  # 保存条件
                'stock_info': row.xpath(".//td[1]/font/text()").extract_first(default=""),
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


class MolcanPrdSpider(BaseSpider):
    name = 'molcan_prds'
    base_url = 'http://molcan.com'
    start_urls = map(lambda x: f"http://molcan.com/product_categories/{x}", uppercase)
    pattern_cas = re.compile(r"\d+-\d{2}-\d(?!\d)")
    pattern_mw = re.compile(r'\d+\.\d+')
    pattern_mf = re.compile(r"(?P<tmf>(?P<mf>(?P<p>[A-Za-z]+\d+)+([A-Z]+[a-z])?)\.?(?P=mf)?)")

    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'CONCURRENT_REQUESTS_PER_IP': 8,
    }

    def parse(self, response):
        urls = response.xpath('//ul[@class="categories"]/li/a/@href').extract()
        api_names = response.xpath('//ul[@class="categories"]/li/a/text()').extract()
        for url, api_name in zip(urls, api_names):
            url = url.replace("..", self.base_url)
            yield Request(url, headers=self.headers, meta={'api_name': api_name}, callback=self.parent_parse)

    def parent_parse(self, response):
        detail_urls = response.xpath('//div[@class="product_wrapper"]//a[@class="readmore"]/@href').extract()
        for detail_url in detail_urls:
            url = detail_url.replace("..", self.base_url)
            yield Request(url, headers=self.headers, meta=response.meta, callback=self.detail_parse)

    def detail_parse(self, response):
        info = " ".join(response.xpath('//div[@id="description"]/*/text()').extract())
        l = self.pattern_mf.findall(info)
        if l:
            mf = "".join(map(lambda x: x[0], l))
        else:
            mf = ""
        relate_img_url = response.xpath('//a[@class="product_image lightbox"]/img/@src').extract_first()
        d = {
            'brand': "Molcan",
            'en_name': response.xpath('//p[@class="product_name"]/text()').extract_first().split(' ; ')[0],
            'cat_no': response.xpath('//span[@class="productNo"]/text()').extract_first().split('-')[0],
            'img_url': relate_img_url and self.base_url + relate_img_url,
            'cas': ' '.join(self.pattern_cas.findall(info)),
            'mw': ' '.join(self.pattern_mw.findall(info)),
            'mf': mf,
            'prd_url': response.request.url,
            'info1': "".join(response.xpath('//div[@id="description"]/descendant::*/text()').extract()),
            'parent': response.meta.get('api_name'),
        }
        yield RawData(**d)
        # TODO Finish the spider


class SimsonSpider(BaseSpider):
    name = "simson_prds"
    allowd_domains = ["simsonpharma.com"]
    base_url = "http://simsonpharma.com"

    def start_requests(self):
        url = "http://simsonpharma.com/category/products"
        for i in range(20):
            d = {
                "category_id": str(i),
                "pageno": '1',
                "page_per_row": '9999',
            }
            yield FormRequest(url, formdata=d)

    def parse(self, response):
        try:
            j_objs = json.loads(response.text)
        except ValueError:
            return
        prds = j_objs.get("list", [])
        for prd in prds:
            tmp = prd.get("Page_Url")
            yield Request(urljoin(self.base_url, "/product/" + tmp), callback=self.detail_parse)

    @staticmethod
    def extract_value(response, title):
        ret = response.xpath(f'//td[text()={title!r}]/following-sibling::td/descendant-or-self::text()').extract()
        return ''.join(ret).strip() or None

    def detail_parse(self, response):
        img_url = response.xpath('//div[@class="product-img"]//img/@src').extract_first()
        d = {
            "brand": "Simson",
            "en_name": response.xpath('//h5[contains(@class, "pro-title")]/text()').extract_first(),
            "prd_url": response.url,
            "info1": self.extract_value(response, "Chemical Name"),
            "cat_no": self.extract_value(response, "Cat. No."),
            "cas": self.extract_value(response, "CAS. No."),
            "mf": formular_trans(self.extract_value(response, "Molecular Formula")),
            "mw": self.extract_value(response, "Formula Weight"),
            "img_url": img_url or urljoin(self.base_url, img_url),
            "info4": self.extract_value(response, "Category"),
            "stock_info": self.extract_value(response, "Product Stock Status"),
        }
        yield RawData(**d)


class DaltonSpider(BaseSpider):
    name = "dalton_prds"
    allowed_domains = ["daltonresearchmolecules.com"]
    start_urls = ["https://www.daltonresearchmolecules.com/chemical-compounds-catalog", ]
    base_url = "https://www.daltonresearchmolecules.com"

    def parse(self, response):
        l_cat = response.xpath('//ul[@style="margin-left: 16px;"]/li/a')
        for cat in l_cat:
            url_cat = cat.xpath('./@href').extract_first()
            catalog = cat.xpath('./text()').extract_first()
            tmp_url = self.base_url + url_cat

            yield Request(tmp_url,
                          callback=self.cat_parse,
                          method="GET",
                          meta={'catalog': catalog}
                          )

    def cat_parse(self, response):
        rows = response.xpath('//form/div[@class="row"]/div')
        catalog = response.meta.get('catalog')
        print(len(rows))
        for row in rows:
            name = row.xpath('./a/text()').extract_first()
            url_prd = row.xpath('./a/@href').extract_first()
            mol_text = row.xpath('./div/div/object/param/@value').extract_first()
            text = row.xpath('./div/div[contains(text(),"Purity")]/text()').extract()
            purity = text[0]
            cat_no = text[1]
            cas = text[2]
            stock = text[3]
            mol = text[4].strip()
            if mol_text:
                mol_text = mol_text.decode('string_escape')

            d = {
                'en_name': name,
                'prd_url': url_prd,  # 产品详细连接
                'mol_text': mol_text,
                'purity': purity,
                'cat_no': cat_no,
                'cas': cas,
                'stock_info': stock,
                'mf': mol,
                'parent': catalog,
            }
            yield RawData(**d)


class LGCSpider(BaseSpider):
    name = "lgc_prds"
    allowd_domains = ["lgcstandards.com"]
    start_urls = ["https://www.lgcstandards.com/CN/en/Pharmaceutical/cat/279492", ]
    base_url = "https://www.lgcstandards.com"

    def parse(self, response):
        urls = response.xpath('//div[@class="outline"]//h4/a/@href').extract()
        for url in urls:
            yield Request(url=urljoin(self.base_url, url), callback=self.detail_parse)



    def detail_parse(self, response):
        tmp = '//div[contains(@class,"product__item")]/h2[text()={!r}]/following-sibling::*/descendant-or-self::text()'
        parents = response.xpath(
            '//div[contains(@class,"product page-section")]//div[contains(@class,"product__item")]/h2[contains(text(),"API Family")]/following-sibling::*/descendant-or-self::text()').extract()
        parent = "".join(parents)
        related_categories = response.xpath(
            '//ul[contains(@class,"breadcrumb")]/li[position()=last()-1]/a/text()').extract_first(default="").strip()
        d = {
            "brand": "LGC",
            "parent": parent or related_categories,
            "cat_no": response.xpath(tmp.format("Product Code")).extract_first(),
            "en_name": response.xpath('//h1[@class="product__title"]/text()').extract_first(default="").strip(),
            "cas": response.xpath(tmp.format("CAS Number")).extract_first(default="").strip() or None,
            "mf": response.xpath(tmp.format("Molecular Formula")).extract_first("").replace(" ", "") or None,
            "mw": response.xpath(tmp.format("Molecular Weight")).extract_first(),
            "stock_info": response.xpath(
                '//h4[contains(@class,"orderbar__stock-title")]/descendant-or-self::text()').extract_first(
                "").strip() or None,
            "img_url": response.xpath('//div[contains(@class, "product__brand-img")]/img/@src').extract_first(),
            "info1": response.xpath(tmp.format("IUPAC")).extract_first(default="").strip(),
            "prd_url": response.request.url,
        }

        yield RawData(**d)


class AozealSpider(BaseSpider):
    name = "aozeal_prds"
    allowd_domains = ["aozeal.com"]
    start_urls = ["https://www.aozeal.com/shop-2/", ]
    base_url = "http://aozeal.com"

    def parse(self, response):
        categories = response.xpath('//ul[@class="product-categories"]/li/a')
        for cat in categories:
            cat_url = cat.xpath('./@href').extract_first()
            parent_drug = cat.xpath('./text()').extract_first()
            yield Request(cat_url, callback=self.list_parse, meta={"parent_drug": parent_drug})

    def list_parse(self, response):
        urls = response.xpath('//div[@class="hb-product-meta"]//a/@href').extract()
        for rel_url in urls:
            yield Request(url=urljoin(self.base_url, rel_url), callback=self.detail_parse, meta=response.meta)
        next_url = response.xpath('//a[@class="next page-numbers"]/@href').extract_first()
        if next_url is None:
            return
        yield Request(url=next_url, callback=self.list_parse)

    def detail_parse(self, response):
        tmp_xpath = '//div[contains(@class, "summary entry-summary")]//span[text()={0!r}]/../following-sibling::span/text()'
        d = {
            'brand': "Aozeal",
            'en_name': response.xpath('//h3[@itemprop="name"]//text()').extract_first(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': response.xpath(tmp_xpath.format("Catalogue No.")).extract_first(default=""),
            'cas': response.xpath(tmp_xpath.format("CAS No.")).extract_first(default="N/A"),
            'mf': response.xpath(tmp_xpath.format("Mol. Formula")).extract_first(default=""),
            'mw': response.xpath(tmp_xpath.format("Mol. Weight")).extract_first(default=""),
            'stock_info': response.xpath(tmp_xpath.format("Stock Info")).extract_first(default=None),
            'info1': "".join(response.xpath('//div[@id="tab-description"]//text()').extract()).strip(),
            'parent': response.meta.get("parent_drug"),
            'img_url': response.xpath('//figure//a/@href').extract_first(),
        }
        yield RawData(**d)


class AnantSpider(BaseSpider):
    name = "anant_prds"
    allowd_domains = ["anantlabs.com"]
    start_urls = ["http://anantlabs.com/", ]
    base_url = "http://anantlabs.com"
    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS_PER_IP': 2,
    }

    def parse(self, response):
        l_parent = response.xpath(
            '//div[@class="categoryfilter asl_sett_scroll"]/div/div[@class="label"]/text()').extract()
        for parent in l_parent:
            if parent.strip() == "Products":
                continue
            parent = parent.strip().replace(' ', '-')
            url = "http://anantlabs.com/category/{0}/".format(parent)
            meta = {'parent': parent}
            yield Request(url, callback=self.list_parse, meta=meta, headers=self.headers)

    def list_parse(self, response):
        urls = response.xpath('//div[contains(@class,"product")]/h5/a/@href').extract()
        for url in urls:
            yield Request(url, callback=self.detail_parse, meta=response.meta, headers=self.headers)

    def detail_parse(self, response):
        div = response.xpath('//div[contains(@class,"heading")]')
        tmp_xpath = './h6[contains(text(),"{0}")]/parent::*/following-sibling::*/h5/descendant-or-self::*/text()'
        tmp_xpath_2 = './h6[contains(text(),"{0}")]/parent::*/following-sibling::*/h5/text()'
        # TODO untested
        mf = ''.join(div.xpath(tmp_xpath.format("Molecular Formula")).extract()).strip()
        d = {
            'brand': "Anant",
            'en_name': response.xpath('//div[contains(@class,"prod-details")]//h1/text()').extract_first(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': response.xpath('//h5[@class="prod-cat"]/text()').extract_first(default="").strip(),
            'cas': div.xpath(tmp_xpath_2.format("CAS")).extract_first(default="").strip(),
            'stock_info': div.xpath(tmp_xpath_2.format("Stock Status")).extract_first(default="").strip(),
            'mf': formular_trans(mf),
            'mw': div.xpath(tmp_xpath_2.format("Molecular Weight")).extract_first(default="").strip(),
            'info1': response.xpath('//b[contains(text(),"Synonyms : ")]/following-sibling::text()').extract_first(
                default="").strip(),
            'parent': response.meta.get('parent'),
            'img_url': response.xpath('//div[contains(@class,"entry-thumb")]/a/img/@src').extract_first(),
        }
        yield RawData(**d)


class AcanthusSpider(BaseSpider):
    name = "acanthus_prds"
    allowd_domains = ["acanthusresearch.com"]
    start_urls = ["http://acanthusresearch.com/products/", ]
    base_url = "http://www.acanthusresearch.com/"

    def parse(self, response):
        prd_urls = response.xpath('//ul[@class="products"]/li//div[@class="prod-detail"]//h2/a/@href').extract()
        for prd_url in prd_urls:
            yield Request(prd_url, callback=self.detail_parse)
        next_page_url = response.xpath('//a[@class="next page-numbers"]/@href').extract_first()
        if next_page_url:
            yield Request(next_page_url, callback=self.parse)

    def detail_parse(self, response):
        tmp_xpath = '//span[@class="spec" and contains(text(), {0!r})]/following-sibling::span//text()'

        raw_mf = response.xpath(tmp_xpath.format("Molecular Formula")).extract()
        en_name = response.xpath('//h1[contains(@class, "product_title")]/text()').extract_first(default="").strip()
        cas = response.xpath(tmp_xpath.format("CAS Number")).extract_first(default="N/A").strip()
        d = {
            'brand': "Acanthus",
            'cat_no': response.xpath(tmp_xpath.format("Product Number")).extract_first(default="").strip(),
            'en_name': en_name,
            'prd_url': response.request.url,  # 产品详细连接
            'cas': cas == "NA" and "N/A" or cas,
            'mf': ''.join(raw_mf),
            'mw': None,
            'info1': response.xpath('//div[@class="tags"]/a/text()').extract_first("").strip() or None,
            'stock_info': "".join(response.xpath('//div[@class="row"]//div[contains(@class, "stock-opt")]//text()').extract()).strip(),
            'parent': response.xpath(tmp_xpath.format("Parent Drug")).extract_first(default="").strip(),
            'img_url': urljoin(self.base_url, response.xpath('//div[@class="row"]//img/@src').extract_first()),
        }
        yield RawData(**d)


class SynzealSpider(BaseSpider):
    name = "synzeal_prds"
    allowd_domains = ["synzeal.com"]
    base_url = "https://www.synzeal.com"
    start_urls = map(lambda x: f"https://www.synzeal.com/category/{x}", ascii_uppercase)

    def parse(self, response):
        l_url = response.xpath("//h4[@class='title']/a/@href").extract()
        for rel_url in l_url:
            yield Request(self.base_url + rel_url, callback=self.list_parse, meta=response.meta, headers=self.headers)

    def list_parse(self, response):
        urls = response.xpath('//div[@class="product-item"]//h2/a/@href').extract()
        for rel_url in urls:
            yield Request(self.base_url + rel_url, callback=self.detail_parse, meta=response.meta, headers=self.headers)

    def detail_parse(self, response):
        en_name = response.xpath('//h1[@class="titleproduct"]/text()').extract_first(default="")
        en_name = re.sub(r'\r?\n', "", en_name)
        d = {
            'brand': "SynZeal",
            'en_name': en_name.strip(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': response.xpath('//span[contains(@id,"sku")]/text()').extract_first(default=""),
            'cas': response.xpath('//span[contains(@id,"mpn")]/text()').extract_first(default=""),
            'stock_info': response.xpath('//span[contains(@id,"ProductInstockStatus")]/text()').extract_first(
                default=""),
            'mf': response.xpath(
                '//span[contains(text(),"Molecular Formula")]/following-sibling::span/text()').extract_first(
                default=""),
            'mw': response.xpath(
                '//span[contains(text(),"Molecular Weight")]/following-sibling::span/text()').extract_first(default=""),
            'info1': response.xpath('//b[contains(text(),"Synonyms")]/following-sibling::span/text()').extract_first(
                default="").strip(),
            'parent': response.xpath('//div[contains(@class, "cath1title")]/h1/text()').extract_first(default=""),
            'img_url': response.xpath(
                '//div[@class="maindiv-productdetails"]//div[@class="picture"]//img/@src').extract_first(),
        }
        yield RawData(**d)


# TODO untested
class TRCSpider(BaseSpider):
    name = "trc_prds"
    allow_domain = ["trc-canada.com", ]
    start_urls = ["https://www.trc-canada.com/parent-drug/", ]
    search_url = "https://www.trc-canada.com/parentdrug-listing/"
    base_url = "https://www.trc-canada.com"

    custom_settings = {
        'CONCURRENT_REQUESTS': 32,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 64,
        'CONCURRENT_REQUESTS_PER_IP': 64,
    }

    def parse(self, response):
        api_names = response.xpath('//table[contains(@id, "table")]//td/input/@value').extract()
        for api_name in api_names:
            if api_name.lower().startswith("a") or api_name.lower().startswith("b"):
                continue
            d = {
                "keyword": api_name,
                "t": "product",
                "advanced": "yes"
            }
            yield FormRequest(url=self.search_url, formdata=d, callback=self.list_parse, meta={"api_name": api_name})

    def list_parse(self, response):
        rel_urls = response.xpath(
            '//div[@class="product_list_left"]//ul/li//div[@class="rightSearchContent"]/div/a/@href').extract()
        for rel_url in rel_urls:
            yield Request(self.base_url + rel_url, callback=self.detail_parse, meta=response.meta)

    def detail_parse(self, response):
        tmp_format = '//table[contains(@class,"shop_table")]//tr/td[contains(text(), "{}")]/following-sibling::td/text()'
        item = {
            "brand": "TRC",
            'parent': response.meta.get("api_name", None),
            "en_name": response.xpath(tmp_format.format('Chemical name:')).extract_first(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': response.xpath('//div[@class="post-title-wrapper"]/h1/text()').extract_first(),
            'cas': response.xpath(tmp_format.format('CAS Number:')).extract_first(),
            'mf': formular_trans(response.xpath(tmp_format.format('Molecular form.:')).extract_first()),
            'mw': response.xpath(tmp_format.format('Mol. Weight:')).extract_first(),
            'img_url': self.base_url + response.xpath('//img[@id="mainimg"]/@src').extract_first(),
            'stock_info': response.xpath('//div[@class="InventoryStatus"]/strong/text()').extract_first(),
            'info1': response.xpath(tmp_format.format('Synonyms:')).extract_first(),
        }
        yield RawData(**item)


class VeeprhoSpider(BaseSpider):
    name = "veeprho_prds"
    base_url = "http://www.veeprhopharma.com/"
    start_urls = (f"http://www.veeprhopharma.com/product_view.php?char={char}" for char in string.ascii_uppercase)

    def parse(self, response):
        rel_urls = response.xpath('//select[@name="selector"]/option/@value').extract()
        for rel_url in rel_urls:
            url = self.base_url + rel_url
            yield Request(url, self.list_parse)

    def list_parse(self, response):
        parent = "".join(response.xpath('//div[@class="productheading"]/strong/descendant::text()').extract())
        prds = response.xpath('//div[@class="item"]')

        for prd in prds:
            rel_img_src = prd.xpath('./div[@class="impurityimage"]/img/@src').extract_first()
            cat_no = prd.xpath('./b/text()').extract_first()
            item = {
                "brand": "Veeprho",
                "parent": parent,
                "cat_no": cat_no and cat_no.replace("Catalogue No : ", ""),
                "en_name": prd.xpath('.//div[@class="subproductheading"]/strong/descendant::text()').extract_first(),
                "img_url": rel_img_src and self.base_url + rel_img_src,
                "info1": strip(prd.xpath('./div[@style]/text()').extract_first()),
                "cas": prd.xpath('./text()').re_first('\d+-\d{2}-\d{1}\b'),
                "prd_url": response.url,
            }
            yield RawData(**item)


class StannumSpider(BaseSpider):
    name = "stannum_prds"
    start_urls = ("http://www.stannumusa.com/?page_id=13",)
    base_url = "http://www.stannumusa.com/"

    def parse(self, response):
        ref_urls = response.xpath('//ol/li/div//a/@href').extract()
        for ref_url in ref_urls:
            url = self.base_url + ref_url
            yield Request(url, callback=self.list_parse)

    def list_parse(self, response):
        parent = response.xpath('//h2[@class="art-postheader"]/text()').extract_first()
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
                'cat_no': row.xpath('./td/text()').extract_first(),
                'en_name': ''.join(row.xpath('./td[2]/descendant::text()').extract()),
                'cas': row.xpath('./td[3]/descendant::text()').extract_first(),
                'mw': mw,
                'mf': mf,
                'img_url': row.xpath('./td[5]/img/@src').extract_first(),
            }
            yield RawData(**item)


class SynPharmatechSpider(BaseSpider):
    name = "syn_prds"
    base_url = "http://www.synpharmatech.com"
    start_urls = (f'http://www.synpharmatech.com/products/search.asp?type=sign&twd={char}' for char in
                  string.ascii_uppercase)

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="submit"]/a[@id="submit3"]/@href').extract()
        for rel_url in rel_urls:
            yield Request("".join((self.base_url, "/products/", rel_url)), callback=self.detail_parse)

        next_href = response.xpath('//div[@class="fy"]/a[contains(text(), "Next >")]/@href').extract_first()
        if next_href and next_href != "javascript:;":
            yield Request(next_href, callback=self.parse)

    def detail_parse(self, response):
        tmp = 'normalize-space(//div[@class="product1_l"]//span[contains(text(), "{}")]/../text())'

        item = {
            "brand": "SynPharmaTech",
            "cat_no": strip(response.xpath(tmp.format("Cat. No")).extract_first()),
            "en_name": strip(response.xpath('//div[@class="product1_l"]//h1/text()').extract_first()),
            "info1": strip(response.xpath(tmp.format("Synonyms")).extract_first()),
            "cas": strip(response.xpath(tmp.format("CAS No")).extract_first()),
            "mf": strip(response.xpath(tmp.format("Formula")).extract_first()),
            "mw": strip(response.xpath(tmp.format("F.W")).extract_first()),
            "purity": strip(response.xpath(tmp.format("Purity")).extract_first()),
            "stock_info": strip(response.xpath(
                'normalize-space(//div[@class="product2"]//tr[position()>1]/td[4]/text())').extract_first()) or None,
            "prd_url": response.url,
            "img_url": self.base_url + response.xpath('//div[@class="product1"]/img/@src').extract_first()
        }
        yield RawData(**item)


class ChromaDexSpider(BaseSpider):
    name = "chromadex_prds"
    start_urls = map(lambda x: f"https://standards.chromadex.com/search?type=product&q={x}", ("ASB", "KIT"))
    base_url = "https://standards.chromadex.com/"

    def parse(self, response):
        rel_urls = response.xpath('//h2[@itemprop="name"]/a/@href').extract()
        for url in rel_urls:
            yield Request(urljoin(self.base_url, url), callback=self.detail_parse)
        next_url = response.xpath('//a[@title="Next »"]/@href').extract_first()
        if next_url:
            yield Request(urljoin(self.base_url, next_url), callback=self.parse)

    @staticmethod
    def extract_value(response, title):
        ret = response.xpath(f'//p[contains(text(), {title!r})]/text()').extract_first()
        return ret.replace(title, '').strip() or None

    def detail_parse(self, response):
        cat_no = response.xpath('//h1[@itemprop="name"][2]/text()').extract_first("")
        m = re.match(r'[A-Z]{3}-\d+', cat_no)
        if m:
            cat_no = m.group(0)
        d = {
            "brand": "ChromaDex",
            "parent": self.extract_value(response, "Chemical Family: "),
            "cat_no": cat_no,
            "en_name": response.xpath('//h1[@itemprop="name"][1]/text()').extract_first("").title().rsplit(' - ', 1)[0],
            "cas": self.extract_value(response, "CAS: "),
            "mf": self.extract_value(response, "Chemical Formula: "),
            "mw": self.extract_value(response, "Formula Weight: "),
            "info2": self.extract_value(response, "Long Term Storage: "),
            "info4": self.extract_value(response, "Appearance: "),
            "purity": self.extract_value(response, "Purity: "),
            "prd_url": response.url,
        }
        pass
        yield RawData(**d)


class AcornSpider(BaseSpider):
    name = "acorn_prds"
    start_urls = ["http://www.acornpharmatech.com/18501/index.html", ]
    base_url = "http://www.acornpharmatech.com"

    def parse(self, response):
        a_nodes = response.xpath('//table[@width="100%"]//tr//a')
        for a_node in a_nodes:
            parent = a_node.xpath('./img/@alt').extract_first()
            href = a_node.xpath('./@href').extract_first()
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
            stock_info = row.xpath('normalize-space(./td[5]/descendant::text())').extract_first()
            img_rel_url = row.xpath('./td[4]/img/@src').extract_first()
            d = {
                "brand": "Acorn",
                "parent": parent,
                "cat_no": cat_no,
                "cas": row.xpath('./td[2]/text()').extract_first("N/A").strip(),
                "en_name": en_name,
                "info1": en_name,
                "img_url": img_rel_url and img_rel_url.replace("./..", self.base_url),
                "stock_info": stock_info and stock_info.strip(),
                "prd_url": response.url,
            }
            yield RawData(**d)


class SincoSpider(BaseSpider):
    name = "sinco_prds"
    start_urls = (f"http://www.sincopharmachem.com/category.asp?c={c}" for c in chain(ascii_uppercase, ('OTHER', )))
    base_url = "http://www.sincopharmachem.com"

    def parse(self, response):
        a_nodes = response.xpath('//li[@class="product-category-item"]/a')
        for a in a_nodes:
            url = urljoin(self.base_url, a.xpath('./@href').extract_first())
            parent = a.xpath('./@title').extract_first()
            yield Request(url, meta={"parent": parent}, callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//li[@class="product-item"]/div[1]/a/@href').extract()
        for url in urls:
            yield Request(url, meta=response.meta, callback=self.detail_parse)

    def detail_parse(self, response):
        tmp_xpath = '//strong[text()={0!r}]/../following-sibling::td//text()'
        d = {
            "brand": "Sinco",
            "parent": response.meta.get('parent'),
            "cat_no": "".join(response.xpath(tmp_xpath.format("CAT#: ")).extract()),
            "cas": "".join(response.xpath(tmp_xpath.format("CAS#: ")).extract()),
            "en_name": "".join(response.xpath(tmp_xpath.format("Product Name: ")).extract()),
            "mf": "".join(response.xpath(tmp_xpath.format("M.F.: ")).extract()),
            "mw": "".join(response.xpath(tmp_xpath.format("M.W.: ")).extract()),
            "img_url": response.xpath('//img[@class="smallImg"]/@src').extract_first(),
            "prd_url": response.url,
        }
        yield RawData(**d)


class QCCSpider(BaseSpider):
    name = "qcc_prds"
    start_urls = (f"http://www.qcchemical.com/index.php/Index/api?letter={c.lower()}&mletter={c}" for c in
                  ascii_uppercase)
    base_url = "http://www.qcchemical.com/"

    def parse(self, response):
        a_nodes = response.xpath('//div[@id="pros"]/ul/a')
        for a in a_nodes:
            url = urljoin(self.base_url, a.xpath('./@href').extract_first())
            parent = a.xpath('./li/text()').extract_first()
            yield Request(url, callback=self.list_parse, meta={"parent": parent and parent.strip()})

    def list_parse(self, response):
        rel_urls = response.xpath('//div[@id="list"]//a[contains(text(), "Details")]/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse, meta=response.meta)

    def detail_parse(self, response):
        tmp = '//td[contains(descendant-or-self::text(), "{}")]//following-sibling::td/text()'
        d = {
            "brand": "QCC",
            "parent": response.meta.get('parent'),
            "cat_no": response.xpath(tmp.format("QCC Cat No.:")).extract_first(),
            "cas": strip(response.xpath(tmp.format("CAS No.:")).extract_first()),
            "en_name": strip(response.xpath(tmp.format("Chemical Name:")).extract_first()),
            "info1": strip(response.xpath(tmp.format("Synonyms:")).extract_first()),
            "img_url": urljoin(self.base_url, response.xpath('//table//td/div[@style]/img/@src').extract_first()),
            "mf": strip(response.xpath(tmp.format("Molecular Formula:")).extract_first()),
            "mw": strip(response.xpath(tmp.format("Molecular Weight:")).extract_first()),
            "prd_url": response.url,
        }
        yield RawData(**d)


class STDSpider(BaseSpider):
    name = "std_prds"
    start_urls = ["http://www.standardpharm.com/portal/list/index/id/11.html", ]
    base_url = "http://www.standardpharm.com/"

    def parse(self, response):
        a_nodes = response.xpath('//ul[@class="pro"]/li/a')
        for a in a_nodes:
            url = urljoin(self.base_url, a.xpath('./@href').extract_first(""))
            parent = getattr(re.search(r'.+(?=\s\()', a.xpath('./text()').extract_first()), "group")()
            yield Request(url, callback=self.list_parse, meta={"parent": parent})

    def list_parse(self, response):
        uls = response.xpath('//ul[@class="pro"]')
        for ul in uls:
            d = {
                "brand": "STD",
                "parent": response.meta.get('parent'),
                "cat_no": ul.xpath('.//b[contains(text(), "STD No. : ")]/text()').extract_first("").replace(
                    "STD No. : ", "").strip(),
                "cas": ul.xpath('.//b[contains(text(), "CAS No. :")]/text()').extract_first("").replace("CAS No. : ",
                                                                                                        "").strip(),
                "en_name": ul.xpath('.//h3/a/descendant-or-self::text()').extract_first(),
                "img_url": urljoin(self.base_url, ul.xpath('.//img/@src').extract_first()),
                "mf": ul.xpath('.//b[contains(text(), "Chemical Formula :")]/text()').extract_first("").replace(
                    "Chemical Formula : ", "").strip(),
                "prd_url": urljoin(self.base_url, ul.xpath('.//a[@class="p-link"]/@href').extract_first()),
            }
            yield RawData(**d)


class CPRDSpider(BaseSpider):
    name = "cprd_prds"
    start_urls = (f"http://c-prd.com/product/{c}.html" for c in ascii_uppercase)
    base_url = "http://c-prd.com/"

    def parse(self, response):
        a_nodes = response.xpath('//ul[@class="categories"]//a')
        for a in a_nodes:
            yield Request(urljoin(self.base_url, a.xpath('./@href').extract_first()),
                          meta={"parent": a.xpath('./text()')},
                          callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//a[@class="sorts"]/@href').extract()
        for url in urls:
            yield Request(url, callback=self.detail_parse)

    def detail_parse(self, response):
        d = {
            "brand": "CPRD",
            "parent": response.xpath('//p[@class="catalogue_number"]/a/text()').extract_first(),
            "cat_no": response.xpath('//span[@class="productNo"]/text()').extract_first(),
            "cas": response.xpath(
                '//b[contains(text(), "CAS Number:")]/parent::p/child::text()[last()]').extract_first(),
            "en_name": response.xpath(
                '//b[contains(text(), "Product Name:")]/parent::p/child::text()[last()]').extract_first(),
            "img_url": urljoin(self.base_url,
                               response.xpath('//div[@id="left_description"]//img/@src').extract_first()),
            "mf": response.xpath(
                '//b[contains(text(), "Molecular formula")]/parent::p/child::text()[last()]').extract_first(),
            "mw": response.xpath(
                '//b[contains(text(), "Molecular formula")]/parent::p/child::text()[last()]').extract_first(),
            "prd_url": response.url,
        }
        yield RawData(**d)


class ECOSpicer(BaseSpider):
    name = "eco_prds"
    start_urls = ["http://eco-canada.com/search/", ]
    base_url = "http://eco-canada.com/"

    def parse(self, response):
        values = tuple(set(response.xpath('//div[@class="pardrug"]//select/option[position()>1]/@value').extract()))
        for value in values:
            url = f"http://eco-canada.com/search/?ptag={value}"
            yield Request(url, meta={"parent": value}, callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//div[contains(@class, "pro_list")]/div[@class="pro_title"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin(self.base_url, url), meta=response.meta, callback=self.detail_parse)

    def detail_parse(self, response):
        tmp = '//span[contains(text(),"{}")]/following-sibling::font/text()'
        d = {
            "brand": "ECO",
            "parent": response.meta.get("parent"),
            "cat_no": response.xpath(tmp.format("Catalogue number")).extract_first(),
            "cas": response.xpath(tmp.format("CAS Number")).extract_first(),
            "en_name": response.xpath('//div[@class="p_vtitle"]/text()').extract_first(),
            "img_url": urljoin(self.base_url,
                               response.xpath('//div[@class="p_viewimg pcshow"]//img/@src').extract_first()),
            "mf": response.xpath(tmp.format("Molecular Formula")).extract_first(),
            "mw": response.xpath(tmp.format("Molecular Weight")).extract_first(),
            "prd_url": response.url,
        }
        yield RawData(**d)


class HICSpider(BaseSpider):
    name = "hic_prds"
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
            "cat_no": response.xpath('//h1[@class="header-post-title-class"]/text()').extract_first(),
            "cas": response.xpath(tmp.format("CAS:")).extract_first(),
            "en_name": response.xpath(tmp.format("Chemical name:")).extract_first(),
            "info1": response.xpath(tmp.format("Synonyms:")).extract_first(),
            "img_url": response.xpath('//div[@class="images"]//img/@src').extract_first(),
            "mf": formular_trans(response.xpath(tmp.format("Molecular form:")).extract_first()),
            "mw": response.xpath(tmp.format("Mol. Weight:")).extract_first(),
            "prd_url": response.url,
            "stock_info": response.xpath('//div[@class="InventoryStatus"]/strong/text()').extract_first(),
        }
        yield RawData(**d)


class WitegaSpider(BaseSpider):
    name = "witega_prds"
    base_url = "https://auftragssynthese.com/"
    start_urls = ["https://auftragssynthese.com/katalog_e.php", ]

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="blue3"]//a[not(@target)]/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.list_parse)

    def list_parse(self, response):
        rows = response.xpath('//table[@class="tabelle-chemikalien"]//tr')
        for row in rows:
            d = {
                "brand": "Witega",
                "cat_no": row.xpath('./td[3]/text()').extract_first(),
                "en_name": row.xpath('./td[1]/text()').extract_first(),
                "cas": row.xpath('./td[2]/text()').extract_first(),
            }
            yield RawData(**d)


class CILSpider(BaseSpider):
    name = "cil_prds"
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
                x_query.format("ctl00_ToolkitScriptManager1_HiddenField")).extract_first(),
            "__EVENTTARGET": response.xpath(x_query.format("__EVENTTARGET")).extract_first(),
            "__EVENTARGUMENT": response.xpath(x_query.format("__EVENTARGUMENT")).extract_first(),
            "__LASTFOCUS": response.xpath(x_query.format("__LASTFOCUS")).extract_first(),
            "__VIEWSTATE": response.xpath(x_query.format("__VIEWSTATE")).extract_first(),
            "__VIEWSTATEENCRYPTED": response.xpath(x_query.format("__VIEWSTATEENCRYPTED")).extract_first(),
            "__EVENTVALIDATION": response.xpath(x_query.format("__EVENTVALIDATION")).extract_first(),
            "addtocartconfirmresult": "",
            "ctl00$topSectionctl$SearchBar1$txtkeyword": "Product Search...",
            "ctl00$cpholder$ctl00$ItemList1$SortByCtl$dbsort": "Name",
            "ctl00$cpholder$ctl00$ItemList1$PageSizectl$dlPageSize": "9999",
        }
        yield FormRequest(response.url, formdata=d, callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//td[@class="itemnotk"]/a/@href').extract()
        meta = {"parent": response.xpath('//td[@class="product_text"]/h3/text()').extract_first()}
        for url in urls:
            yield Request(url, callback=self.detail_parse, meta=meta)
        x_query = '//form[@name="aspnetForm"]/div/input[@id="{0}"]/@value'
        next_page = response.xpath('//input[@class="pageon"]/following-sibling::input[1]/@value').extract_first()
        if not next_page:
            return
        d = {
            "ctl00_ToolkitScriptManager1_HiddenField": response.xpath(
                x_query.format("ctl00_ToolkitScriptManager1_HiddenField")).extract_first(),
            "__EVENTTARGET": response.xpath(x_query.format("__EVENTTARGET")).extract_first(),
            "__EVENTARGUMENT": response.xpath(x_query.format("__EVENTARGUMENT")).extract_first(),
            "__LASTFOCUS": response.xpath(x_query.format("__LASTFOCUS")).extract_first(),
            "__VIEWSTATE": response.xpath(x_query.format("__VIEWSTATE")).extract_first(),
            "__VIEWSTATEENCRYPTED": response.xpath(x_query.format("__VIEWSTATEENCRYPTED")).extract_first(),
            "__EVENTVALIDATION": response.xpath(x_query.format("__EVENTVALIDATION")).extract_first(),
            "addtocartconfirmresult": "",
            "ctl00$topSectionctl$SearchBar1$txtkeyword": "Product Search...",
            "ctl00$cpholder$ctl00$ItemList1$SortByCtl$dbsort": "Name",
            "ctl00$cpholder$ctl00$ItemList1$ctlPaging$btn2": next_page,
            "ctl00$cpholder$ctl00$ItemList1$PageSizectl$dlPageSize": "20",
        }
        yield FormRequest(response.url, formdata=d, callback=self.list_parse)

    def detail_parse(self, response):
        tmp = '//td[@class="dleft" and contains(./p/text(), "{}")]/following-sibling::td/p/text()'
        cas = response.xpath(tmp.format("Labeled CAS#")).extract_first()
        unlabeled_cas = response.xpath(tmp.format("Unlabeled CAS#")).extract_first()
        r_img_url = response.xpath('//div[@class="image-section"]/p//img/@src').extract_first()
        d = {
            "brand": "CIL",
            "parent": response.meta.get("parent"),
            "cat_no": response.xpath(tmp.format("Item Number")).extract_first(),
            "cas": f"{cas}; Unlabeled Cas:{unlabeled_cas}",
            "en_name": response.xpath('//h1[@class="ldescription"]/text()').extract_first(),
            "img_url": urljoin(response.url, r_img_url),
            "mf": formular_trans(response.xpath(tmp.format("Chemical Formula")).extract_first()),
            "mw": response.xpath(tmp.format("Molecular Weight")).extract_first(),
            "prd_url": response.url,
        }
        yield RawData(**d)


class DRESpider(BaseSpider):
    name = "dre_prds"
    allowd_domains = ["lgcstandards.com"]
    start_urls = [
        "https://www.lgcstandards.com/lgccommercewebservices/v2/lgcstandards/categories/279492/products?currentPage=1&q=&sort=relevance-code&pageSize=20&country=CN&lang=en&fields=FULL", ]
    base_url = "https://www.lgcstandards.com/CN/en"
    search_url = "https://www.lgcstandards.com/lgccommercewebservices/v2/lgcstandards/products/search?"

    def parse(self, response):
        total_page = int(response.xpath('//pagination/totalPages/text()').extract_first())
        cur_page = int(response.xpath('//pagination/currentPage/text()').extract_first())
        per_page = int(response.xpath('//pagination/pageSize/text()').extract_first())
        next_page = cur_page + 1

        products = response.xpath('//products')

        for product in products:
            url = product.xpath('./url/text()').extract_first()
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
            '//ul[contains(@class,"breadcrumb")]/li[position()=last()-1]/a/text()').extract_first(default="").strip()

        color = response.xpath('//h2[text()="Color"]/following-sibling::p/text()').extract_first("")
        appearance = response.xpath('//h2[text()="Appearance/Form"]/following-sibling::p/text()').extract_first("")
        d = {
            "brand": "DRE",
            "parent": parent or related_categories,
            "cat_no": response.xpath(tmp.format("Product Code")).extract_first(),
            "en_name": response.xpath('//h1[@class="product__title"]/text()').extract_first(default="").strip(),
            "cas": response.xpath(tmp.format("CAS Number")).extract_first(default="").strip() or None,
            "mf": response.xpath(tmp.format("Molecular Formula")).extract_first("").replace(" ", "") or None,
            "mw": response.xpath(tmp.format("Molecular Weight")).extract_first(),
            "stock_info": response.xpath(
                '//h4[contains(@class,"orderbar__stock-title")]/descendant-or-self::text()').extract_first(
                "").strip() or None,
            "img_url": response.xpath('//div[contains(@class, "product__brand-img")]/img/@src').extract_first(),
            "info1": response.xpath(tmp.format("IUPAC")).extract_first(default="").strip(),
            "info2": response.xpath('//h2[text()="Storage Temperature"]/following-sibling::p/text()').extract_first(),
            "info3": response.xpath('//h2[text()="Shipping Temperature"]/following-sibling::p/text()').extract_first(),
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
            en_name = row.xpath('./td/font/text()').extract_first("").replace("Name:", "")
            rel_img_url = row.xpath('./following-sibling::tr[1]//img/@src').extract_first()
            cat_no = row.xpath(
                './following-sibling::tr[1]//font[contains(text(), "Catalog No: ")]/text()').extract_first().replace(
                "Catalog No: ", "").strip()
            if not first_cat_no:
                first_cat_no = cat_no
            d = {
                "brand": "APIChem",
                "parent": None,
                "cat_no": cat_no,
                "en_name": en_name,
                "cas": row.xpath(
                    './following-sibling::tr[1]//font[contains(text(), "CAS No: ")]/text()').extract_first().replace(
                    "CAS No: ", ""),
                "mf": None,
                "mw": None,
                "img_url": rel_img_url and urljoin(self.base_url, rel_img_url),
                "info1": en_name,
                "prd_url": response.request.url,
            }
            print(d)
            yield RawData(**d)
        next_page = response.xpath('//img[@src="/images/aaanext.gif"]/../@onclick').extract_first("")
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


class DaicelSpider(BaseSpider):
    name = "daicel_prds"
    base_url = "http://www.daicelpharmastandards.com/"
    start_urls = ["http://www.daicelpharmastandards.com/products.php", ]

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="Catalogue"]/a/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse)

    def detail_parse(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td/text()'
        img_rel_url = response.xpath('//div[@class="modal-body"]/img/@src').extract_first()
        d = {
            "brand": "Daicel",
            "parent": strip(response.xpath(tmp.format("API Name :")).extract_first()),
            "cat_no": response.xpath('//div[@class="Catalogue"]/text()').extract_first().split(': ')[-1],
            "en_name": response.xpath(tmp.format("Name of Compound :")).extract_first(),
            "cas": strip(response.xpath('//b[text()="CAS number : "]/following-sibling::text()[1]').extract_first()),
            "mf": strip(response.xpath('//b[text()="Mol. Formula : "]/following-sibling::text()[1]').extract_first()),
            "mw": response.xpath(tmp.format("Molecular Weight :")).extract_first(),
            "img_url": img_rel_url and urljoin(self.base_url, img_rel_url),
            "info1": strip(response.xpath(tmp.format('IUPAC Name :')).extract_first()),
            "info2": strip(response.xpath(tmp.format('Storage Condition :')).extract_first()),
            "info4": strip(response.xpath(tmp.format('Appearance :')).extract_first()),
            "prd_url": response.request.url,
            "stock_info": strip(response.xpath(tmp.format('Stock Status :')).extract_first()),
        }
        yield RawData(**d)


class ClearsynthSpider(BaseSpider):
    name = "clearsynth_prds"
    base_url = "https://www.clearsynth.com/en/"
    start_urls = ["https://www.clearsynth.com/en/", ]

    def parse(self, response):
        categories = response.xpath('//ul[@class="menu"]//a/text()').extract()
        for category in categories:
            params = {
                "search": category,
                "Therapeutic": "",
                "api": "",
                "industry": "",
                "category": "",
                "t": "",
                "limit": 20,
                "start": 1,
                "_": int(time()*1000),
            }
            url = "https://www.clearsynth.com/en/fetch.asp?" + urlencode(params)
            yield Request(url, callback=self.list_parse, meta={'params': params})

    def list_parse(self, response):
        rel_urls = response.xpath('//div[@class="product-image"]//a/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(response.request.url, rel_url), callback=self.detail_parse)
        if rel_urls:
            params = response.meta.get('params')
            params["start"] = params["start"] + params["limit"]
            url = "https://www.clearsynth.com/en/fetch.asp?" + urlencode(params)
            yield Request(url, callback=self.list_parse, meta={'params': params})

    def detail_parse(self, response):
        tmp = 'normalize-space(//td[contains(text(),{!r})]/following-sibling::td//text())'
        tmp2 = '//strong[contains(text(), {!r})]/../following-sibling::td/text()'
        parent = response.xpath(tmp.format("Parent API")).extract_first()
        category = response.xpath(tmp.format("Category")).extract_first()
        img_rel_url = response.xpath('//div[@class="product-media"]//img/@src').extract_first()
        d = {
            "brand": "Clearsynth",
            "parent": parent or category,
            "cat_no": response.xpath(tmp.format("CAT No.")).extract_first(),
            "en_name": response.xpath('//div[@class="product-name"]//text()').extract_first(),
            "cas": response.xpath(tmp.format("CAS")).extract_first(),
            "mf": formular_trans(strip("".join(response.xpath("//td[contains(text(),'Mol. Formula')]/following-sibling::td//text()").extract()))),  # TODO
            "mw": response.xpath(tmp.format("Mol. Weight")).extract_first(),
            "img_url": img_rel_url and urljoin(response.request.url, img_rel_url),
            "info1": strip(response.xpath(tmp2.format('Synonyms')).extract_first()),
            "info2": strip(response.xpath(tmp2.format("Storage Conditions")).extract_first()),
            "smiles": strip(response.xpath(tmp2.format("Smiles")).extract_first()),
            "prd_url": response.request.url,
            "stock_info": strip(response.xpath(tmp2.format("Stock Status")).extract_first()),
        }
        yield RawData(**d)
