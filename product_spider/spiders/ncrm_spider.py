import json
import scrapy
from urllib.parse import urljoin, urlencode

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.cost import parse_cost
from product_spider.utils.spider_mixin import BaseSpider


class NcrmSpider(BaseSpider):
    """国家标准物质资源共享平台"""
    name = "ncrm"
    start_urls = ["https://www.ncrm.org.cn/Web/Material/List?fenleiAutoID=5&pageIndex=1"]
    base_url = "https://www.ncrm.org.cn/"

    def parse(self, response, **kwargs):
        rows = response.xpath("//ul[@class='level-items']//li")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./a/@href").get())
            parent = row.xpath("./a/text()").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                meta={
                    "parent": parent,
                }
            )

    def parse_list(self, response):
        parent = response.meta.get("parent")
        rows = response.xpath("//tbody/tr")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./td[last()-3]//a/@href").get())
            chs_name = row.xpath("./td[last()-2]/a/text()").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={
                    "parent": parent,
                    "chs_name": chs_name,
                }
            )

        current_page = response.xpath("//input[@id='page-index']/@value").get()  # 首页
        max_count = response.xpath("//input[@id='page-count']/@value").get()  # 最大页
        if int(max_count) <= (current_page := int(current_page)):
            return
        next_page_d = {
            "fenleiAutoID": response.xpath('//input[@id="fenleiAutoID"]/@value').get(),
            "lingyuAutoID": response.xpath('//input[@id="lingyuAutoID"]/@value').get(),
            "pageIndex": str(current_page + 1)
        }
        url = f"https://www.ncrm.org.cn/Web/Material/List?{urlencode(next_page_d)}"
        yield scrapy.Request(
            url=url,
            callback=self.parse_list
        )

    def parse_detail(self, response):
        tmpl = '//span[contains(text(), {!r})]/parent::td/following-sibling::td/text()'
        parent = response.meta.get("parent")
        chs_name = response.meta.get("chs_name")
        en_name = response.xpath("//span[contains(text(), '英文名称')]/parent::td/following-sibling::td/text()").get()
        cat_no = response.xpath("//h5[@class='text_overflow_two']/a/text()").get()
        img_url = response.xpath("//div[@class='small-4 columns']//img/@src").get()
        appearance = response.xpath("//span[contains(text(), '特征形态')]/parent::td/following-sibling::td/text()").get()
        package = response.xpath("//span[contains(text(), '规格')]/parent::td/following-sibling::td/text()").get()
        delivery_time = response.xpath("//td[contains(text(), '状态')]/following-sibling::td/text()").get()
        shipping_info = response.xpath("//td[contains(text(), '物流')]/following-sibling::td/text()").get()
        price = parse_cost(response.xpath("//h4[@class='orange']/text()").get())

        info2 = response.xpath("//span[contains(text(), '保存条件')]/parent::td/following-sibling::td/text()").get()

        prd_attrs = json.dumps({
            "precautions_for_use": response.xpath(tmpl.format('使用注意事项')).get(),
            "substrate": response.xpath(tmpl.format('基体')).get(),
            "main_analysis_method": response.xpath(tmpl.format('主要分析方法')).get(),
            "fixed_unit": response.xpath(tmpl.format('定值单位')).get(),
            "production_org": response.xpath(tmpl.format('研制单位名称')).get(),
            "production_handler": response.xpath(tmpl.format('研制负责人')).get(),
            "approval_date": response.xpath(tmpl.format('被批准时间')).get(),
        })

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": parent,
            "chs_name": chs_name,
            "en_name": en_name,
            "appearance": appearance,
            "img_url": img_url,
            "shipping_info": shipping_info,
            "prd_url": response.url,
            "info2": info2,
            "attrs": prd_attrs,
        }

        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "cost": price,
            "package": package,
            "delivery_time": delivery_time,
            'currency': 'RMB',
        }

        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id": f'{self.name}_{d["cat_no"]}_{dd["package"]}',
            "parent": d["parent"],
            "en_name": d["en_name"],
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'cost': dd['cost'],
            "currency": dd["currency"],
            "img_url": d["img_url"],
            "prd_url": d["prd_url"],
        }
        dddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id":  f'{self.name}_{d["cat_no"]}',
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'discount_price': dd['cost'],
            'price': dd['cost'],
            'currency': dd["currency"],
        }
        yield RawData(**d)
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)
