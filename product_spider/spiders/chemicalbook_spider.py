import json
import logging
from urllib.parse import urljoin
import scrapy
from product_spider.items import SupplierProduct, ChemicalItem
from product_spider.utils.cost import parse_cost
from product_spider.utils.functions import strip

from product_spider.utils.spider_mixin import BaseSpider

logger = logging.getLogger(__name__)


class ChemicalBookSpider(BaseSpider):
    """chemical_book"""
    name = "chemicalbook"
    start_urls = ["https://www.chemicalbook.com/ShowAllProductByIndexID_CAS_12_0htm"]
    base_url = "https://www.chemicalbook.com/"

    # TODO range(12, 21)
    def start_requests(self):
        for i in range(12, 13):
            url = f"https://www.chemicalbook.com/ShowAllProductByIndexID_CAS_{i}_0.htm"
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "catalog_num": i,
                },
            )

    def parse(self, response, **kwargs):
        catalog_num = response.meta.get("catalog_num")
        raw_current_page = response.xpath("//div[@class='page_jp']/b[last()]/text()").get()
        raw_max_page = response.xpath("//div[@class='page_jp']/a[last()]/text()").get()

        urls = response.xpath("//div[@id='mainDiv']//tr/td[last()-1]/a/@href").getall()
        if not urls:
            logger.warning(f"product urls : {response.url} get urls fail")
            r = response.request
            r.meta.update({'refresh_proxy': True})
            yield r

        for url in urls:
            yield scrapy.Request(
                url=urljoin(self.base_url, url),
                callback=self.parse_detail,
            )
        # 翻页
        if raw_current_page is not None or raw_max_page is not None:
            current_page = int(raw_current_page)
            max_page = int(raw_max_page)
            if current_page < max_page:
                yield scrapy.Request(
                    url=f"https://www.chemicalbook.com/ShowAllProductByIndexID_CAS_{catalog_num}_{current_page * 100}.htm",
                    callback=self.parse,
                    meta={"catalog_num": catalog_num}
                )

    def parse_detail(self, response):
        tmp_xpath = "//dt[contains(text(), {!r})]/following-sibling::dd/text()"

        cas = response.xpath(tmp_xpath.format('CAS号:')).get()
        if not cas:
            warning_title = response.xpath("//div[@class='SearchEmpty']/h2/span/text()").get()
            logger.warning(warning_title)
            logger.warning(f"product detail url: {response.url} get cas fail")
            r = response.request
            r.meta.update({'refresh_proxy': True})
            yield r

        en_name = response.xpath(tmp_xpath.format('英文名称:')).get()
        chs_name = response.xpath(tmp_xpath.format('中文名称:')).get()
        mf = response.xpath(tmp_xpath.format('分子式:')).get()
        mw = response.xpath(tmp_xpath.format('分子量:')).get()
        img_url = urljoin(self.base_url, response.xpath("//td[@class='productimg']/img/@src").get())

        # 化学性质
        chemical_rows = response.xpath("//table[@id='ChemicalProperties']//td")

        chemical_attrs = [{
            chemical.xpath(".//dt/span/text()").get(): chemical.xpath(".//dd/span/text()").get()
        } for chemical in chemical_rows]

        # 安全信息
        safety_rows = response.xpath("//div[@class='detailInfoDiv']//table[@border='0']//tr")

        safety_attrs = [{
            safety.xpath("./th/span/text()").get(): safety.xpath("./td/span/text()").get()
        } for safety in safety_rows]

        d = {
            "brand": self.name,
            "cat_no": cas,
            "en_name": en_name,
            "chs_name": chs_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "img_url": img_url,
            "prd_url": response.url,
        }

        rows = response.xpath("//th[contains(text(), '产品编号')]/parent::tr/following-sibling::tr")
        for row in rows:
            cost = parse_cost(row.xpath("./td[last()]/text()").get())
            package = row.xpath("./td[last()-1]/text()").get()
            dd = {
                "brand": self.name,
                "cat_no": d["cas"],
                "cost": cost,
                "package": package,
                "currency": "RMB",
            }

            nodes = response.xpath("//th[contains(text(), '供应商')]/parent::tr/following-sibling::tr")
            for node in nodes:
                vendor = node.xpath("./td[position()=1]/a/text()").get()
                email = strip(node.xpath("./td[position()=3]/text()").get())
                country = strip(node.xpath("./td[position()=4]/text()").get())
                ddd = {
                    "platform": self.name,
                    "vendor": vendor,
                    "source_id": f"{email}_{country}",
                    "brand": self.name,
                    "chs_name": d["chs_name"],
                    "cas": d["cas"],
                    "mf": d["mf"],
                    "mw": d["mw"],
                    "package": dd["package"],
                    "cost": dd["cost"],
                    "currency": dd["currency"],
                    "cat_no": d["cat_no"],
                    "img_url": img_url,
                    "prd_url": response.url,
                }
                yield SupplierProduct(**ddd)

        chemical_item_attrs = json.dumps({
            "chemical_attrs": chemical_attrs,
            "safety_attrs": safety_attrs,
        }, ensure_ascii=False)

        dddd = {
            "cas": cas,
            "source": self.name,
            "prd_url": response.url,
            "attrs": chemical_item_attrs
        }
        yield ChemicalItem(**dddd)
