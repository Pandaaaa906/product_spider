# coding=utf-8
import re
import json
import string
from urllib.parse import urljoin

import scrapy
from scrapy import FormRequest
from scrapy.http.request import Request
from string import ascii_uppercase as uppercase, ascii_lowercase as lowercase, ascii_uppercase
from time import time
from product_spider.items import JkItem, AccPrdItem, CDNPrdItem, BestownPrdItem, RawData
from product_spider.utils.drug_list import drug_pattern
from product_spider.utils.functions import strip
from product_spider.utils.maketrans import formular_trans


class myBaseSpider(scrapy.Spider):
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


class AccPrdSpider(scrapy.Spider):
    name = "accprd"
    allowed_domains = ["accustandard.com"]
    base_url = "https://www.accustandard.com"
    start_urls = ["https://www.accustandard.com/organic.html?limit=100",
                  "https://www.accustandard.com/petrochemical.html?limit=100",
                  "https://www.accustandard.com/inorganic.html?limit=100",
                  ]

    def parse(self, response):
        r_catalog = re.findall(r"\w+(?=\.html)", response.url)
        if r_catalog:
            catalog = r_catalog[0]
        else:
            catalog = "N/A"
        prd_list = response.xpath("//ol[@class='products-list']/li")
        for prd in prd_list:
            x_description = prd.xpath(".//div[@itemprop='description']/text()").extract()
            x_stock_info = prd.xpath(".//p[@class='availability out-of-stock']/span/text()").extract()
            if x_description:
                description = x_description[0]
            else:
                description = ""
            if x_stock_info:
                stock_info = x_stock_info[0]
            else:
                stock_info = ""
            d = {
                'cat_no': prd.xpath(".//h2[@itemprop='productID']/text()").extract()[0],
                'name': prd.xpath(".//h2[@class='product-name']/a/@title").extract()[0],
                'prd_url': prd.xpath(".//h2[@class='product-name']/a/@href").extract()[0],
                'unit': prd.xpath(".//div[@itemprop='referenceQuantity']/text()").extract()[0].strip(),
                'price': prd.xpath(".//span[@itemprop='price']/text()").extract()[0],
                'stock_info': stock_info,
                'description': description,
                'catalog': catalog,
            }
            yield AccPrdItem(**d)
        x_next_page = response.xpath('//div[@class="pager"]//a[@class="next i-next"]/@href').extract()

        if x_next_page:
            url = x_next_page[0]
            yield Request(url, method="GET", callback=self.parse)


# TODO Get Blocked
class ChemServicePrdSpider(myBaseSpider):
    name = "chemsrvprd"
    base_url = "https://www.chemservice.com/"
    start_urls = ["https://www.chemservice.com/store.html?limit=100", ]
    handle_httpstatus_list = [500, ]

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


class CDNPrdSpider(myBaseSpider):
    name = "cdnprd"
    base_url = "https://www.cdnisotopes.com/"
    start_urls = [
        "https://www.cdnisotopes.com/ca/en/products/alphalistings/cdn_alphabeticallistings_a1.php?ei=nqKhfnmBjZ1/fnIS/ae0mU5Zi1jMBqtHvAe70Xf5+CipOqayXPFhemT5Xu/aOmT5eG1e8C1acd1x2rf55Tn6ermyb950Z3fmce/a6Y=y", ]

    def parse(self, response):
        tables = response.xpath("//table[contains(@class,'list')][position()>1]")
        for table in tables:
            cat_no = table.xpath('.//td[@class="listpno"]/a/text()').extract_first(default="").replace('\xa0', " ")
            name = ''.join(table.xpath('.//div[@class="listcomp"]/a//text()').extract())
            name = name[:name.find('Show ')].replace('\xa0', " ")
            purity = table.xpath('.//div[@class="listiso"]/text()').extract_first(default="").replace('\xa0', " ")
            cas = table.xpath('.//div[@class="listcas"]/text()').extract_first(default="").replace('\xa0', " ")
            trs = table.xpath(".//tr")
            for tr in trs:
                unit = tr.xpath("./*[contains(@class,'listqty')]/text()").extract_first(default="").replace('\xa0', " ")
                stock = tr.xpath("./td[@class='liststk']/text()").extract_first(default="").replace('\xa0', " ")
                price = tr.xpath('./td[@class="listprc"]/descendant-or-self::text()[last()]').extract_first(
                    default="").replace('\xa0', " ")
                d = {
                    'cat_no': cat_no,
                    'name': name,
                    'unit': unit,
                    'price': price,
                    'stock': stock,
                    'purity': purity,
                    'cas': cas,
                }
                yield CDNPrdItem(**d)
                # print(cat_no, name, purity, cas, unit, stock, price)
        next_page_url = response.xpath('//span[@class="pgntn"]/following-sibling::a[1]/@href').extract_first()
        if next_page_url:
            url = next_page_url.replace("../../../../../", self.base_url)
            yield Request(url, headers=self.headers)
        else:
            next_albt = response.xpath('//span[@class="alphalnks"]/following-sibling::a[1]/@href').extract_first()
            if next_albt:
                url = next_albt.replace("../../../../../", self.base_url)
                yield Request(url, headers=self.headers)


class BestownSpider(myBaseSpider):
    name = "bestownprd"
    base_url = "http://bestown.net.cn/"
    start_urls = ["http://bestown.net.cn/?gallery-8.html"]

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


class TLCSpider(myBaseSpider):
    name = "tlc_prds"
    base_url = "http://tlcstandards.com/"
    start_urls = ["http://tlcstandards.com/ProdNameList.aspx"]
    x_template = './child::br[contains(following-sibling::text(),"{0}")]/following-sibling::font[1]/text()'

    custom_settings = {
        'CONCURRENT_REQUESTS': 32,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 64,
        'CONCURRENT_REQUESTS_PER_IP': 64,
    }

    def parse(self, response):
        l_a = response.xpath('//td[@class="namebody"]/a')
        for a in l_a:
            url = self.base_url + a.xpath('./@href').extract_first()
            api_name = a.xpath('./text()').extract_first().title()
            yield Request(url, headers=self.headers, callback=self.list_parse, meta={'api_name': api_name})

    def list_parse(self, response):
        l_r_url = response.xpath('//table[@class="image_text"]//td[@valign="top"]/a/@href').extract()
        for r_url in l_r_url:
            url = self.base_url + r_url
            yield Request(url, headers=self.headers, callback=self.detail_parse, meta=response.meta)

    def detail_parse(self, response):
        td = response.xpath('//td[@height="195px"]')
        d = {
            'en_name': "".join(td.xpath('./b/font/descendant-or-self::text()').extract()),
            'cat_no': td.xpath(self.x_template.format("TLC No.")).extract_first(),
            'img_url': self.base_url + response.xpath('//td[@align="center"]/a/img/@src').extract_first(default=""),
            'cas': td.xpath(self.x_template.format("CAS")).extract_first(),
            'mw': td.xpath(self.x_template.format("Molecular Weight")).extract_first(),
            'mf': td.xpath(self.x_template.format("Molecular Formula")).extract_first(),
            'parent': response.meta.get("api_name", ""),
            'brand': 'TLC',
            'prd_url': response.request.url,
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


class MolcanPrdSpider(myBaseSpider):
    name = 'molcan_prds'
    base_url = 'http://molcan.com'
    start_urls = map(lambda x: "http://molcan.com/product_categories/" + x, uppercase)
    pattern_cas = re.compile("\d+-\d{2}-\d(?!\d)")
    pattern_mw = re.compile('\d+\.\d+')
    pattern_mf = re.compile("(?P<tmf>(?P<mf>(?P<p>[A-Za-z]+\d+)+([A-Z]+[a-z])?)\.?(?P=mf)?)")

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


class SimsonSpider(myBaseSpider):
    name = "simson_prds"
    allowd_domains = ["simsonpharma.com"]
    start_urls = [
        "http://simsonpharma.com//search-by-index.php?seacrh_by_index=search_value&type=product_name&value=A&methodType=", ]
    base_url = "http://simsonpharma.com"

    def parse(self, response):
        l_values = list(lowercase) + ["others", ]
        tmp_url = "http://www.simsonpharma.com//functions/Ajax.php?action=products&type=product_name&methodType=ajax&value={0}"
        urls = map(lambda x: tmp_url.format(x), l_values)
        for url in urls:
            yield Request(url=url, method="GET", callback=self.detail_parse)

    def detail_parse(self, response):
        try:
            j_objs = json.loads(response.text)
        except ValueError:
            yield
        for j_obj in j_objs:
            en_name = j_obj.get("product_name")
            if en_name:
                en_name = en_name.strip()

            catalog = j_obj.get("product_categoary_id")
            if re.search('[\s-]', en_name) is None:
                parent = en_name
            elif "Drug Substance" in catalog:
                parent = en_name
            elif catalog == "Speciality Chemicals":
                parent = catalog
            else:
                result = drug_pattern.findall(en_name)
                # print(en_name, catalog)
                # print(result)
                if result:
                    parent = result[0]
                else:
                    parent = catalog

            stock_i = j_obj.get("stk")
            if stock_i == "1":
                stock_info = "In Stock"
            else:
                stock_info = None
            d = {
                "brand": "Simson",
                "en_name": en_name,
                "prd_url": "http://simsonpharma.com//products.php?product_id=" + j_obj.get("product_id"),  # 产品详细连接
                "info1": j_obj.get("product_chemical_name"),
                "cat_no": j_obj.get("product_cat_no"),
                "cas": j_obj.get("product_cas_no", "").strip(),
                "mf": formular_trans(j_obj.get("product_molecular_formula")),
                "mw": j_obj.get("product_molecular_weight"),
                "img_url": "http://simsonpharma.com//simpson/images/productimages/" + j_obj.get("product_image"),
                "parent": parent,
                "info2": j_obj.get("product_synonyms"),
                "info3": j_obj.get("status"),
                "info4": catalog,
                "stock_info": stock_info,
            }
            yield RawData(**d)


class DaltonSpider(myBaseSpider):
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


class LGCSpider(myBaseSpider):
    name = "lgc_prds"
    allowd_domains = ["lgcstandards.com"]
    start_urls = ["https://www.lgcstandards.com/CN/en/LGC-impurity-and-API-standards/cat/154584", ]
    base_url = "https://www.lgcstandards.com"

    def parse(self, response):
        urls = response.xpath('//table[@class="subCategoryTable"]//a/@href').extract()
        for url in urls:
            yield Request(url=self.base_url + url, callback=self.drug_list_parse)

    def drug_list_parse(self, response):
        urls = response.xpath('//table[@class="subCategoryTable"]//a/@href').extract()
        for url in urls:
            yield Request(url=self.base_url + url, callback=self.product_list_parse)

    def product_list_parse(self, response):
        urls = response.xpath('//table[@class="subCategoryTable"]//a/@href').extract()
        for url in urls:
            yield Request(url=self.base_url + url, callback=self.detail_parse)
        np_url = response.xpath('//div[@class="pagination"]/strong/following-sibling::a/@href').extract_first(
            default="")
        if np_url:
            yield Request(url=self.base_url + np_url, callback=self.product_list_parse)

    def detail_parse(self, response):
        analyte = response.xpath(
            '//span[text()="Analyte:"]/parent::*/parent::*/following-sibling::td//a/text()').extract_first(
            default="").strip()
        synonyms = response.xpath(
            '//span[text()="Synonyms:"]/parent::*/parent::*/following-sibling::td//a/text()').extract_first(
            default="").strip()
        related_categories = response.xpath('//td[contains(@class,"RelatedproductTd2")]//a/text()').extract_first(
            default="").strip()
        parent = response.xpath(
            '//h3[@class="summarysection-paragraph"]/a[@class="summarysection"]/text()').extract_first(
            default="").strip()
        d = {
            "brand": "LGC",
            "parent": parent or related_categories,
            "cat_no": response.xpath('//span[@itemprop="sku"]/text()').extract_first(default="").replace('-', ""),
            "en_name": response.xpath('//span[@itemprop="name"]/text()').extract_first(default="").strip(),
            "cas": response.xpath(
                '//span[text()="CAS no"]/parent::*/parent::*/following-sibling::td/h2/text()').extract_first(
                default=""),
            "mf": response.xpath(
                '//span[text()="Mol for:"]/parent::*/parent::*/following-sibling::td//a/text()').extract_first(
                default=""),
            "mw": response.xpath(
                '//span[text()="Txtleft outline"]/parent::*/parent::*/following-sibling::td/h3/text()').extract_first(
                default=""),
            "stock_info": response.xpath(
                '//div[contains(@class,"rmAvailabilityInnerWrap")]/span[contains(@class,"rmStatusFlagText")]/text()').extract_first(
                default="").strip(),
            "img_url": response.xpath('//img[@itemprop="image"]/@src').extract_first(default=""),
            "info1": analyte + ";" + synonyms,
            "prd_url": response.request.url,
        }
        yield RawData(**d)


# TODO
class AozealSpider(myBaseSpider):
    name = "aozeal_prds"
    allowd_domains = ["aozeal.com"]
    start_urls = ["http://aozeal.com/list.php", ]
    base_url = "http://aozeal.com"

    def parse(self, response):
        values = response.xpath('//select[@id="pf-selected"]/option/@value').extract()
        for value in values:
            if not value:
                continue
            yield Request(url=f"http://aozeal.com/list.php?sub=&typename={value}", callback=self.list_parse)

    def list_parse(self, response):
        urls = response.xpath('//li[@class="item"]/div[@class="img-wrap"]/a/@href').extract()
        for rel_url in urls:
            yield Request(url=urljoin(self.base_url, rel_url), callback=self.detail_parse)
        next_url = response.xpath('//a[@class="nxt"]/@href').extract_first()
        if next_url is None:
            return
        yield Request(url=urljoin(self.base_url, next_url), callback=self.list_parse)

    def detail_parse(self, response):
        rel_url = response.xpath('//div[@class="p-product-detail"]//img/@src').extract_first()
        if rel_url is not None:
            img_url = urljoin(self.base_url, rel_url)
        else:
            img_url = None
        d = {
            'brand': "Aozeal",
            'en_name': response.xpath('//div[@class="content"]/p/text()').extract_first(),
            'prd_url': response.request.url,  # 产品详细连接
            'cat_no': response.xpath(
                '//div[@class="content"]/dl/dt[contains(text(),"Catalogue No:")]/following-sibling::dd/text()').extract_first(
                default=""),
            'cas': response.xpath(
                '//div[@class="content"]/dl/dt[contains(text(),"CAS No.:")]/following-sibling::dd/text()').extract_first(
                default=""),
            'mf': response.xpath(
                '//div[@class="content"]/dl/dt[contains(text(),"Mol. Formula:")]/following-sibling::dd/text()').extract_first(
                default=""),
            'mw': response.xpath(
                '//div[@class="content"]/dl/dt[contains(text(),"Mol.Weight:")]/following-sibling::dd/text()').extract_first(
                default=""),
            'info1': response.xpath(
                '//div[@class="content"]/dl/dt[contains(text(),"Synonyms:")]/following-sibling::dd/text()').extract_first(
                default="").strip(),
            'parent': response.xpath('//div[contains(@class, "cath1title")]/h1/text()').extract_first(default=""),
            'img_url': img_url,
        }
        yield RawData(**d)


class AnantSpider(myBaseSpider):
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


class AcanthusSpider(myBaseSpider):
    name = "acanthus_prds"
    allowd_domains = ["acanthusresearch.com"]
    start_urls = map(lambda x: "http://www.acanthusresearch.com/product_catalogue.asp?alp=" + x, uppercase)
    base_url = "http://www.acanthusresearch.com/"

    def parse(self, response):
        l_a = response.xpath('//td[@align="left"]/a[@class="rightNavLink"]')
        for a in l_a:
            r_url = a.xpath('./@href').extract_first().strip()
            parent = a.xpath('./span/text()').extract_first()
            meta = {'parent': parent}
            yield Request(self.base_url + r_url, callback=self.list_parse, meta=meta)

    def list_parse(self, response):
        products = response.xpath('//div[@id="ContainerTCell2"]/table//tr')
        tmp_xpath = './/strong[contains(text(),"{0}")]/following-sibling::text()'
        for product in products:
            raw_mf = product.xpath(
                './/strong[contains(text(),"Molecular Formula")]/following-sibling::span/text()').extract()
            en_name = product.xpath(tmp_xpath.format("Name")).extract_first(default="").strip()
            cas = product.xpath(tmp_xpath.format("CAS Number")).extract_first(default="").strip()
            d = {
                'brand': "Acanthus",
                'cat_no': product.xpath(tmp_xpath.format("Catalogue Number")).extract_first(default="").strip(),
                'en_name': en_name,
                'prd_url': response.request.url,  # 产品详细连接
                'cas': cas == "NA" and None or cas,
                'mf': ''.join(raw_mf),
                'mw': None,
                'info1': product.xpath(tmp_xpath.format("Synonyms")).extract_first(default="").strip(),
                'parent': product.xpath(tmp_xpath.format("Parent Drug")).extract_first(default="").strip(),
                'img_url': self.base_url + product.xpath('.//p/img/@src').extract_first(),
            }

            yield RawData(**d)


class SynzealSpider(myBaseSpider):
    name = "synzeal_prds"
    allowd_domains = ["synzeal.com"]
    base_url = "https://www.synzeal.com"

    @property
    def start_urls(self):
        for char in ascii_uppercase:
            yield f"https://www.synzeal.com/category/{char}"

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
class TRCSpider(myBaseSpider):
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


class VeeprhoSpider(myBaseSpider):
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


class StannumSpider(myBaseSpider):
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


class SynPharmatechSpider(myBaseSpider):
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
            "stock_info": strip(response.xpath('normalize-space(//div[@class="product2"]//tr[position()>1]/td[4]/text())').extract_first()) or None,
            "prd_url": response.url,
            "img_url": self.base_url + response.xpath('//div[@class="product1"]/img/@src').extract_first()
        }
        yield RawData(**item)
