import re
from enum import Enum
from urllib.parse import urljoin, parse_qsl, urlencode
import scrapy
from scrapy import Request
from scrapy.http import Response

from product_spider.items import SupplierProduct, RawSupplier, ChemicalBookChemical
from product_spider.utils.functions import strip, dumps, clean_dict

from product_spider.utils.spider_mixin import BaseSpider


class ChemicalBookStrategy(str, Enum):
    FROM_CB_CHEM = 'FROM_CB_CHEM'
    WALK_THROUGH_CAS = 'WALK_THROUGH_CAS'
    CUSTOM_CB_CODES = 'CUSTOM_CB_CODES'


class ChemicalBookSpider(BaseSpider):
    """chemical_book"""
    name = "chemicalbook"
    start_urls = ["https://www.chemicalbook.com/ShowAllProductByIndexID_CAS_12_0htm"]
    base_url = "https://www.chemicalbook.com/"

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'PROXY_POOL_REFRESH_STATUS_CODES': [403, 500, 302],
        'RETRY_TIMES': 20,
        'CONCURRENT_REQUESTS': 8,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }

    def __init__(
            self,
            strategy: ChemicalBookStrategy = ChemicalBookStrategy.WALK_THROUGH_CAS,
            page_start=1, page_end=35, crawl_chem_detail=False, **kwargs
    ):
        # 默认爬12-20，带CAS，不带Cas的取1-35
        super().__init__(**kwargs)
        self.strategy = strategy
        self.page_start = int(page_start)
        self.page_end = int(page_end)
        self.crawl_chem_detail = crawl_chem_detail

    def start_requests(self):
        if self.strategy == ChemicalBookStrategy.WALK_THROUGH_CAS:
            for i in range(self.page_start, self.page_end + 1):
                url = f"https://www.chemicalbook.com/ShowAllProductByIndexID_CAS_{i}_0.htm"
                yield scrapy.Request(
                    url=url,
                    callback=self.parse,
                    meta={'dont_redirect': True, 'handle_httpstatus_list': [302]}
                )
        elif self.strategy == ChemicalBookStrategy.CUSTOM_CB_CODES:
            with open('data/cb_codes') as f:
                for line in f:
                    cb_id = line.strip()
                    # yield Request(
                    #     url=f"https://www.chemicalbook.com/ProdSupplierGN.aspx?CBNumber={cb_id}&ProvID=1001",
                    #     callback=self.parse_cb_supplier_list,
                    #     meta={'dont_redirect': True, 'handle_httpstatus_list': [302]}
                    # )
                    yield Request(
                        url=f"https://www.chemicalbook.com/productlist.aspx?cbn={cb_id}",
                        callback=self.parse_cb_product_list,
                        meta={'dont_redirect': True, 'handle_httpstatus_list': [302]}
                    )
        else:
            raise NotImplemented

    def is_proxy_invalid(self, request, response):
        if response.status in {403, 500, 302}:
            self.logger.warning(f'status code:{response.status}, {request.url}')
            return True
        if '系统忙' in response.text[:50]:
            self.logger.warning(f'system busy: {request.url}')
            return True
        if response.xpath('//p[text()="请进行人机身份验证"]'):
            self.logger.warning(f'进行人机验证, 准备更换代理: {request.url}')
            return True
        if request.url.startswith('https://www.chemicalbook.com/ShowAllProductByIndexID') \
                and not bool(response.xpath("//div[@id='mainDiv']//tr/td[1]/a")):
            self.logger.warning(f'empty cas list: {request.url}')
            return True
        return False

    def parse(self, response, **kwargs):
        a_nodes = response.xpath("//div[@id='mainDiv']//tr/td[1]/a")

        for a_node in a_nodes:
            url = a_node.xpath('./@href').get()
            cb_id = (m := re.search(r'CB\d+', url)) and m.group()
            if not cb_id:
                self.logger.warning(f"doesn't have cb_id in : {response.url}")
                continue

            if self.crawl_chem_detail:
                yield scrapy.Request(
                    url=f"https://www.chemicalbook.com/ProductChemicalProperties{cb_id}.htm",
                    callback=self.parse_chemical,
                    meta={'dont_redirect': True, 'handle_httpstatus_list': [302]},
                    priority=10,
                )

            # yield scrapy.Request(
            #     url=f"https://www.chemicalbook.com/ProdSupplierGN.aspx?CBNumber={cb_id}&ProvID=1001",
            #     callback=self.parse_cb_supplier_list,
            #     meta={'dont_redirect': True, 'handle_httpstatus_list': [302]},
            #     priority=10,
            # )
            yield Request(
                url=f"https://www.chemicalbook.com/productlist.aspx?cbn={cb_id}",
                callback=self.parse_cb_product_list,
                meta={'dont_redirect': True, 'handle_httpstatus_list': [302]},
                priority=10,
            )
        # 翻页
        next_pages = response.xpath('//div[@class="page_jp"]/b/following-sibling::a/@href').getall()
        for idx, next_page in enumerate(next_pages):
            if idx > 32:
                break
            if idx not in {0, 2, 8, 32}:
                continue
            yield Request(
                url=urljoin(response.url, next_page),
                callback=self.parse,
                meta={'dont_redirect': True, 'handle_httpstatus_list': [302]}
            )

    def parse_cb_supplier_list(self, response):
        """
        parse url like:
        https://www.chemicalbook.com/ProdSupplierGNCB5433869.htm
        https://www.chemicalbook.com/ProdSupplierGN.aspx?CBNumber=CB3108758&ProvID=1001
        :param response:
        :return:
        """
        cb_id = response.xpath('//a[@data-cbnumber]/@data-cbnumber').get()
        cn_name = response.xpath('//td[text()="中文名称:"]/following-sibling::td//text()').get()
        cas = response.xpath('//td[text()="CAS号:"]/following-sibling::td//text()').get()
        mf = response.xpath('//td[text()="分子式:"]/following-sibling::td//text()').get()
        mw = response.xpath('//td[text()="分子量:"]/following-sibling::td//text()').get()
        img_url = response.xpath('//div[@class="basis_img"]/img/@src').get()
        if img_url:
            img_url = urljoin(response.url, img_url)

        div_supplier_nodes = response.xpath('//div[@class="supplier_list_li"]')

        for supp_node in div_supplier_nodes:
            supp_id = supp_node.xpath('./@data-cbsid').get()
            vendor = strip(supp_node.xpath('.//div[@class="supplier_name"]/div/text()').get())
            ddd = {
                "platform": self.name,
                "vendor": vendor,
                "source_id": f"{supp_id or vendor}_{cb_id}",
                "brand": vendor,
                "chs_name": cn_name,
                "cas": cas,
                "mf": mf,
                "mw": mw,
                "cat_no": cb_id,
                "img_url": img_url,
                "prd_url": response.url,
            }
            yield SupplierProduct(**ddd)

            supp_url = f'https://www.chemicalbook.com/ShowSupplierProductsList{supp_id}/0.htm'
            raw_prd_count = supp_node.xpath('//span[text()="相关信息："]/following-sibling::a[1]/text()').get('')
            prd_count = (m := re.search(r'\((\d+)\)', raw_prd_count)) and m.group(1)
            attrs = {
                "prd_count": prd_count,
                "adv_score": supp_node.xpath('.//span[text()="CB指数："]/parent::div/a/text()').get(),
                "src_url": supp_url,
            }
            attrs = {k: v for k, v in attrs.items() if v}
            supplier = {
                "src_type": self.name,
                "src_id": supp_id,
                "name": vendor,
                "phone": supp_node.xpath('.//span[text()="联系电话："]/parent::div/text()').get(),
                "email": supp_node.xpath('.//span[text()="电子邮件："]/parent::div/text()').get(),
                "website": supp_node.xpath('.//span[text()="网址："]/parent::div/a/@href').get(),
                "attrs": dumps(attrs),
            }
            yield Request(
                url=supp_url,
                callback=self.parse_supplier,
                meta={
                    'dont_redirect': True, 'handle_httpstatus_list': [302, 404],
                    "supp_id": supp_id, "supplier": supplier
                },
                priority=10,
            )

        next_page = response.xpath('//a[./span/text()="下一页"]/@data-page-number').get()
        if next_page:
            url, query = response.url.split('?')
            params = dict(parse_qsl(query))
            params['start'] = next_page
            yield Request(
                url=f"{url}?{urlencode(params)}",
                callback=self.parse_cb_supplier_list,
                meta={'dont_redirect': True, 'handle_httpstatus_list': [302]},
                priority=10,
            )

    def parse_cb_product_list(self, response):
        """
        https://www.chemicalbook.com/productlist.aspx?cbn=CB8265719
        :param response:
        :return:
        """
        tmpl = '//dt[strong/text()={!r}]/following-sibling::dd/text()'

        cb_id = response.xpath('//*[contains(@data-cbnumber, "CB")]/@data-cbnumber').get()
        cn_name = ''.join(response.xpath('//div[@class="PLbox"][1]/h2//text()').getall())
        cas = response.xpath(tmpl.format("CAS号：")).get()
        mf = response.xpath(tmpl.format("分子式：")).get()
        mw = response.xpath(tmpl.format("分子量：")).get()
        img_url = response.xpath('//div[@class="PLbox"]//a/img/@src').get()

        div_supplier_nodes = response.xpath('//div[contains(@class, "ProLbox") and not(contains(@class, "ProLboxTit"))]')

        for supp_node in div_supplier_nodes:
            supp_id = supp_node.xpath('.//h1/div/@data-cbsid').get()
            vendor = supp_node.xpath('.//h1/div[@data-suppliername]/@data-suppliername').get()
            raw_top = supp_node.xpath('./@class').get()
            if raw_top:
                is_top = "Top"
            else:
                is_top = None
            attrs = {
                "tags": [*filter(bool, (
                    is_top,
                    supp_node.xpath('.//span[@class="gold"]/text()').get(),
                    supp_node.xpath('.//i[text()="大货"]/text()').get(),
                ))]
            }
            ddd = {
                "platform": self.name,
                "vendor": vendor,
                "source_id": f"{supp_id or vendor}_{cb_id}",
                "brand": vendor,
                "chs_name": cn_name,
                "cas": cas,
                "mf": mf,
                "mw": mw,
                "cat_no": cb_id,
                "img_url": img_url,
                "prd_url": response.url,
                "attrs": dumps(clean_dict(attrs)),
            }
            yield SupplierProduct(**ddd)

            supp_url = f'https://www.chemicalbook.com/ShowSupplierProductsList{supp_id}/0.htm'
            raw_prd_count = ''.join(supp_node.xpath('.//span[text()="相关信息："]/following-sibling::a[1]//text()').getall())
            prd_count = (m := re.search(r'\((\d+)\)', raw_prd_count)) and m.group(1)
            supp_attrs = {
                "prd_count": prd_count,
                "adv_score": supp_node.xpath('.//span[text()="CB指数："]/following-sibling::b/text()').get(),
                "src_url": supp_url,
            }
            phone = supp_node.xpath('.//span[text()="联系电话："]/following-sibling::p/text()').get()
            if phone:
                phone = re.sub(r'\s+', ' ', strip(phone))
            supplier = {
                "src_type": self.name,
                "src_id": supp_id,
                "name": vendor,
                "phone": phone,
                "website": supp_node.xpath('.//span[text()="公司网址："]/following-sibling::b/a/@href').get(),
                "attrs": dumps(clean_dict(supp_attrs)),
            }
            yield Request(
                url=supp_url,
                callback=self.parse_supplier,
                meta={
                    'dont_redirect': True, 'handle_httpstatus_list': [302, 404],
                    "supp_id": supp_id, "supplier": supplier
                },
                priority=10,
            )

        next_page = response.xpath('//div[@class="page"]//li[@class]/following-sibling::li/a/@data-page-number').get()
        if next_page:
            url, query = response.url.split('?')
            params = dict(parse_qsl(query))
            params['page'] = next_page
            params['current'] = "page"
            yield Request(
                url=f"{url}?{urlencode(params)}",
                callback=self.parse_cb_product_list,
                meta={'dont_redirect': True, 'handle_httpstatus_list': [302]},
                priority=10,
            )

    def parse_supplier(self, response):
        supplier = response.meta.get("supplier")
        if response.status == 404:
            yield RawSupplier(**supplier)
            return
        supp_id = response.meta.get("supp_id")
        attrs = {
            "prd_count": response.xpath('//li[text()="产品总数："]/span/text()').get(),
            "adv_score": response.xpath('//li[text()="CB指数："]/span/text()').get(),
            "src_url": response.url,
        }
        attrs = {k: v for k, v in attrs.items() if v}
        phones = response.xpath('//li[text()="手机：" or text()="电话："]//span/text()').getall()
        region = response.xpath('//li[text()="国籍："]/span/text()').get()
        supplier = {
            'src_type': self.name,
            'src_id': supp_id,
            "name": response.xpath('//div[@id="Content_SupplierContact"]//h3//text()').get(),
            "phone": ';'.join(phones),
            "email": response.xpath('//li[text()="邮箱："]//a/text()').get(),
            "website": response.xpath('//li[text()="网址："]//a/text()').get(),
            "attrs": dumps(attrs),
        }
        if region:
            supplier["region"] = region

        yield RawSupplier(**supplier)

    def parse_chemical(self, response: Response):
        url = response.url
        if not url.startswith("https://www.chemicalbook.com/"):
            self.logger.warning(f"Cannot find url property: {response.url}")
            return
        tmpl = '//th[text()={!r}]/following-sibling::td//text()'
        # 化学性质
        chemical_rows = response.xpath("//div[@id='ProductChemPropertyA']//tr")

        chemical_attrs = [{
            chemical.xpath("./th//text()").get(): chemical.xpath("./td//text()").get()
        } for chemical in chemical_rows]

        # 安全信息
        safety_rows = response.xpath("//div[@id='ProductChemSafePropertyA']//tr")

        safety_attrs = [{
            safety.xpath("./th//text()").get(): safety.xpath("./td//text()").get()
        } for safety in safety_rows]
        attrs = {
            "chemical_attrs": chemical_attrs,
            "safety_attrs": safety_attrs,
        }
        cb_id = (m := re.search(r"CB\d+", url)) and m.group()
        if not cb_id:
            self.logger.warning(f"Cannot find cb_id: {response.url}")
        rel_img = response.xpath('//th[text()="结构式"]/following-sibling::td/img/@src').get()
        d = {
            "cb_id": cb_id,
            "cn_name": ''.join(response.xpath(tmpl.format("中文名称")).getall()),
            "en_name": ''.join(response.xpath(tmpl.format("英文名称")).getall()),
            "cn_synonyms": ''.join(response.xpath(tmpl.format("中文同义词")).getall()),
            "en_synonyms": ''.join(response.xpath(tmpl.format("英文同义词")).getall()),

            "cas": ''.join(response.xpath(tmpl.format("CAS号")).getall()),
            "mf": ''.join(response.xpath(tmpl.format("分子式")).getall()),
            "mw": ''.join(response.xpath(tmpl.format("分子量")).getall()),
            "einecs": ''.join(response.xpath(tmpl.format("EINECS号")).getall()),
            "categories": ''.join(response.xpath(tmpl.format("相关类别")).getall()),

            "mol_url": response.xpath('//th[text()="Mol文件"]/following-sibling::td/a/@href').get(),
            "img_url": rel_img and urljoin(response.url, rel_img),

            "url": response.url,
            "attrs": dumps(attrs),
            "html": response.text,
        }
        yield ChemicalBookChemical(**d)
