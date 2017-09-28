# coding=utf-8
import re
import json
import scrapy
from scrapy import FormRequest
from scrapy.http.request import Request
from string import ascii_uppercase as uppercase, lowercase
from time import time
from product_spider.items import JkItem, AccPrdItem, CDNPrdItem, BestownPrdItem, RawData


class myBaseSpider(scrapy.Spider):
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, sdch, br",
        "accept-language": "zh-CN,zh;q=0.8",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    }


class JkPrdSpider(scrapy.Spider):
    name = "jkprd"
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
    name = "tlcprd"
    base_url = "http://tlcstandards.com/"
    start_urls = ["http://tlcstandards.com/ProdNameList.aspx"]
    pattern_cas = re.compile("\d+-\d{2}-\d(?!\d)")
    pattern_mf = re.compile("(?P<tmf>(?P<mf>(?P<p>[A-Za-z]+\d+)+([A-Z]+[a-z])?)\.?(?P=mf)?)")
    pattern_mw = re.compile('\d+\.\d+')

    def parse(self, response):
        l_a = response.xpath('//td[@class="namebody"]/a')
        for a in l_a:
            url = self.base_url + a.xpath('./@href').extract_first()
            api_name = a.xpath('./text()').extract_first().title()
            yield Request(url, headers=self.headers, callback=self.list_parse, meta={'api_name': api_name})

    def list_parse(self,response):
        l_r_url = response.xpath('//table[@class="image_text"]//td[@valign="top"]/a/@href').extract()
        for r_url in l_r_url:
            url = self.base_url + r_url
            yield Request(url, headers=self.headers, callback=self.detail_parse, meta=response.meta)

    def detail_parse(self, response):
        d = {
            'en_name': response.xpath('//font[@class="sectionHeading1"]/text()').extract_first(),
            'cat_no': prd_td.xpath('.//b[2]/text()').extract_first(default=""),
            'img_url': self.base_url + response.xpath('//td[@style="border: solid #CCCCCC 1px; background-color: #ffffff"]//img/@src').extract_first(),
            'cas': ' '.join(self.pattern_cas.findall(info)),
            'mw': ' '.join(self.pattern_mw.findall(info)),
            'mf': mf,
            'parent': response.meta.get("api_name", ""),
            'brand': 'TLC',
        }

    def list_parse(self, response):
        prd_tds = response.xpath('//table[@class="image_text"]//td[@valign="top"]')
        for prd_td in prd_tds:
            info = u'\t'.join(prd_td.xpath('./text()').extract()).replace(u'\xa0', u' ')
            l = self.pattern_mf.findall(info)
            if l:
                mf = "".join(map(lambda x: x[0], l))
            else:
                mf = ""
            d = {
                'en_name': prd_td.xpath('.//b[1]/text()').extract_first(default=""),
                'cat_no': prd_td.xpath('.//b[2]/text()').extract_first(default=""),
                'img_url': self.base_url + prd_td.xpath('.//img/@src').extract_first(default=""),
                'cas': ' '.join(self.pattern_cas.findall(info)),
                'mw': ' '.join(self.pattern_mw.findall(info)),
                'mf': mf,
                'info1': info,
                'parent': response.meta.get("api_name", ""),
                'brand': 'TLC',
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
    name = 'molcanprd'
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
            'img_url': relate_img_url and self.base_url+relate_img_url,
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
    start_urls = ["http://simsonpharma.com//search-by-index.php?seacrh_by_index=search_value&type=product_name&value=A&methodType=",]
    base_url = "http://simsonpharma.com"

    def parse(self, response):
        cookies = response.headers.getlist('Set-Cookie')
        l_values = list(lowercase) + ["others", ]
        tmp_url = "http://simsonpharma.com//functions/Ajax.php?action=pagination&start=0&limit=20000&methodType=ajax&value={0}"
        urls = map(lambda x:tmp_url.format(x), l_values)
        for url in urls:
            yield Request(url=url, method="GET", callback=self.detail_parse)

    def detail_parse(self, response):
        print response.request.headers
        try:
            j_objs = json.loads(response.text)
        except ValueError:
            yield
        for j_obj in j_objs:
            d = {
                "brand":"Simson",
                "en_name":j_obj.get("product_name"),
                "prd_url": "http://simsonpharma.com//products.php?product_id=" + j_obj.get("product_id"),  # 产品详细连接
                "info1": j_obj.get("product_chemical_name"),
                "cat_no": j_obj.get("product_cat_no"),
                "cas": j_obj.get("product_cas_no"),
                "mf": j_obj.get("product_molecular_formula"),
                "mw": j_obj.get("product_molecular_weight"),
                "img_url": "http://simsonpharma.com//simpson/images/productimages/" + j_obj.get("product_image"),
                "parent": j_obj.get("product_categoary_id"),
                "info2": j_obj.get("product_synonyms"),
                "info3": j_obj.get("status"),
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
            yield Request(url=self.base_url+url, callback=self.drug_list_parse)

    def drug_list_parse(self, response):
        urls = response.xpath('//table[@class="subCategoryTable"]//a/@href').extract()
        for url in urls:
            yield Request(url=self.base_url+url, callback=self.product_list_parse)

    def product_list_parse(self, response):
        urls = response.xpath('//table[@class="subCategoryTable"]//a/@href').extract()
        for url in urls:
            yield Request(url=self.base_url+url, callback=self.detail_parse)

    def detail_parse(self, response):
        analyte = response.xpath('//span[text()="Analyte:"]/parent::*/parent::*/following-sibling::td//a/text()').extract_first(default="").strip()
        synonyms = response.xpath('//span[text()="Synonyms:"]/parent::*/parent::*/following-sibling::td//a/text()').extract_first(default="").strip()
        related_categories = response.xpath('//td[contains(@class,"RelatedproductTd2")]//a/text()').extract_first(default="").strip()
        parent = response.xpath('//h3[@class="summarysection-paragraph"]/a[@class="summarysection"]/text()').extract_first(default="").strip()
        d = {
            "brand": "LGC",
            "parent": parent or related_categories,
            "cat_no": response.xpath('//span[@itemprop="sku"]/text()').extract_first(default="").replace('-',""),
            "en_name": response.xpath('//span[@itemprop="name"]/text()').extract_first(default="").strip(),
            "cas": response.xpath('//span[text()="CAS no"]/parent::*/parent::*/following-sibling::td/h2/text()').extract_first(default=""),
            "mf": response.xpath('//span[text()="Mol for:"]/parent::*/parent::*/following-sibling::td//a/text()').extract_first(default=""),
            "mw": response.xpath('//span[text()="Txtleft outline"]/parent::*/parent::*/following-sibling::td/h3/text()').extract_first(default=""),
            "stock_info":response.xpath('//div[contains(@class,"rmAvailabilityInnerWrap")]/span[contains(@class,"rmStatusFlagText")]/text()').extract_first(default="").strip(),
            "img_url":response.xpath('//img[@itemprop="image"]/@src').extract_first(default=""),
            "info1": analyte + ";" + synonyms,
            "prd_url": response.request.url,
        }
        yield RawData(**d)


