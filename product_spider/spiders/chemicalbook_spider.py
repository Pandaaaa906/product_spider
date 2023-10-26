import re
from urllib.parse import urljoin
import scrapy
from scrapy import FormRequest, Request
from scrapy.http import Response

from product_spider.items import SupplierProduct, RawSupplier, ChemicalBookChemical
from product_spider.utils.functions import strip, dumps

from product_spider.utils.spider_mixin import BaseSpider


class ChemicalBookSpider(BaseSpider):
    """chemical_book"""
    name = "chemicalbook"
    start_urls = ["https://www.chemicalbook.com/ShowAllProductByIndexID_CAS_12_0htm"]
    base_url = "https://www.chemicalbook.com/"

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'RETRY_HTTP_CODES': [403, 500],
        'RETRY_TIMES': 10,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }

    def __init__(self, page_start=12, page_end=20, **kwargs):
        # 默认爬12-20，带CAS，不带Cas的取0-35
        super().__init__(**kwargs)
        self.page_start = page_start
        self.page_end = page_end

    def start_requests(self):
        for i in range(self.page_start, self.page_end + 1):
            url = f"https://www.chemicalbook.com/ShowAllProductByIndexID_CAS_{i}_0.htm"
            yield scrapy.Request(
                url=url,
                callback=self.parse,
            )

    def is_proxy_invalid(self, request, response):
        if response.status in {403, 500}:
            self.logger.warning(f'status code:{response.status}, {request.url}')
            return True
        if '系统忙' in response.text[:50]:
            self.logger.warning(f'system busy: {request.url}')
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
            cas = a_node.xpath('./text()').get()
            yield scrapy.Request(
                url=urljoin(self.base_url, url),
                callback=self.parse_detail,
                meta={"cas": cas}
            )
        # 翻页
        next_page = response.xpath('//div[@class="page_jp"]/b/following-sibling::a/@href').get()
        if next_page:
            yield scrapy.Request(
                url=urljoin(response.url, next_page),
                callback=self.parse,
            )

    def parse_detail(self, response):
        tmp_xpath = "//dt[contains(text(), {!r})]/following-sibling::dd/text()"
        warning_title = response.xpath("//div[@class='SearchEmpty']/h2/span/text()").get()
        if warning_title == '根据相关法律法规和政策，此产品禁止销售！':
            return
        cas = response.xpath(tmp_xpath.format('CAS号:')).get() or response.meta.get('cas')

        chem_url = response.xpath('//table[@id="ProductIntroduction"]//td/a/@href').get()

        d = {
            "brand": self.name,
            "cat_no": cas,
            "en_name": response.xpath(tmp_xpath.format('英文名称:')).get(),
            "chs_name": response.xpath(tmp_xpath.format('中文名称:')).get(),
            "cas": cas,
            "mf": response.xpath(tmp_xpath.format('分子式:')).get(),
            "mw": response.xpath(tmp_xpath.format('分子量:')).get(),
            "img_url": urljoin(self.base_url, response.xpath("//td[@class='productimg']/img/@src").get()),
            "prd_url": response.url,
        }
        if chem_url:
            yield Request(urljoin(response.url, chem_url), callback=self.parse_chemical)

        response.meta['chem'] = d
        yield from self.parse_supplier(response)

    def parse_supplier(self, response):
        d = response.meta.get('chem', {})
        dont_grab = response.meta.get('dont_grab', False)
        country_index = int(response.meta.get('country_index', 0))

        cb_code = response.xpath('//dt[text()="CBNumber:"]/following-sibling::dd/text()').get() or d['cas']
        nodes = response.xpath("//th[contains(text(), '供应商')]/parent::tr/following-sibling::tr")
        for node in nodes:
            vendor = node.xpath("./td[position()=1]/a/text()").get()
            vendor_url = node.xpath("./td[position()=1]/a/@href").get()
            phone = strip(node.xpath("./td[position()=2]/text()").get())
            email = strip(node.xpath("./td[position()=3]/text()").get())
            prd_count = strip(node.xpath("./td[position()=5]/a/text()").get())
            adv_score = strip(node.xpath("./td[position()=6]/font/text()").get())
            country = strip(node.xpath("./td[position()=4]/text()").get())
            ddd = {
                "platform": self.name,
                "vendor": vendor,
                "vendor_origin": country,
                "source_id": f"{vendor}_{cb_code}",
                "brand": self.name,
                "chs_name": d["chs_name"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                # "package": dd["package"],
                # "cost": dd["cost"],
                # "currency": dd["currency"],
                "cat_no": d["cat_no"],
                "img_url": d["img_url"],
                "prd_url": response.url,
            }
            yield SupplierProduct(**ddd)
            supplier = {
                "source": self.name,
                "name": vendor,
                "region": country,
                "phone": phone,
                "email": email,
                "attrs": {"prd_count": prd_count, "adv_score": adv_score}
            }
            yield Request(
                vendor_url, callback=self.parse_supplier_detail, meta={"supplier": supplier}
            )

        if not nodes or dont_grab:
            return

        # event_target = response.xpath('//input[@id="__EVENTTARGET"]/@value').get()
        event_arg = response.xpath('//input[@id="__EVENTARGUMENT"]/@value').get()
        last_focus = response.xpath('//input[@id="__LASTFOCUS"]/@value').get()
        view_state = response.xpath('//input[@id="__VIEWSTATE"]/@value').get()
        view_state_gen = response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').get()
        kw = response.xpath('//input[@id="kw"]/@value').get()

        countries = response.xpath('//select[@id="SupplierCountDetail"]//option/@value').getall()
        if len(countries) <= country_index + 1:
            return
        country = countries[country_index]
        yield FormRequest(
            url=response.url,
            formdata={
                '__EVENTTARGET': 'SupplierCountDetail',
                '__EVENTARGUMENT': event_arg,
                '__LASTFOCUS': last_focus,
                '__VIEWSTATE': view_state,
                '__VIEWSTATEGENERATOR': view_state_gen,
                'kw': kw,
                'q': '',
                'SupplierCountDetail': country
            },
            callback=self.parse_supplier,
            meta={
                'dont_grab': len(countries) > country_index + 1,
                'chem': d,
                'country_index': country_index + 1
            }
        )

    def parse_supplier_detail(self, response):
        supplier = response.meta.get('supplier', {})
        supplier['website'] = response.xpath('//li[text()="网址："]//a/text()').get()
        attrs = supplier['attrs']
        attrs['src_url'] = response.url
        supplier['attrs'] = dumps(attrs)
        yield RawSupplier(
            **supplier
        )

    def parse_chemical(self, response: Response):
        url = response.xpath('//meta[@property="og:url"]/@content').get()
        if not url:
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

