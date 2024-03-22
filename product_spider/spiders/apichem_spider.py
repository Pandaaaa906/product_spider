import re
from urllib.parse import urljoin

from scrapy import FormRequest

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class APIChemSpider(BaseSpider):
    name = "apichem"
    base_url = "http://chemmol.com/chemmol/suppliers/apichemistry/texts.php"
    start_urls = [base_url, ]

    def parse(self, response, **kwargs):
        rows = response.xpath('//table[@class="tableborder"]//tr[position() mod 2=1]')
        first_cat_no = None
        for row in rows:
            en_name = row.xpath('./td/font/text()').get("").replace("Name:", "")
            rel_img_url = row.xpath('./following-sibling::tr[1]//img/@src').get()
            cat_no = row.xpath(
                './following-sibling::tr[1]//font[contains(text(), "Catalog No: ")]/text()').get().replace(
                "Catalog No: ", "").strip()
            packages = row.xpath(
                './following-sibling::tr[1]//font[contains(text(), "Availability:")]/text()').get().replace(
                "Availability:", ''
            ).strip()
            if not first_cat_no:
                first_cat_no = cat_no
            d = {
                "brand": "apichem",
                "parent": None,
                "cat_no": cat_no,
                "en_name": en_name,
                "cas": row.xpath(
                    './following-sibling::tr[1]//font[contains(text(), "CAS No: ")]/text()').get().replace(
                    "CAS No: ", ""),
                "mf": None,
                "mw": None,
                "img_url": rel_img_url and urljoin(self.base_url, rel_img_url),
                "info1": en_name,
                "prd_url": response.request.url,
            }
            yield RawData(**d)
            if packages:
                for package in packages.split(','):
                    dd = {
                        "brand": "apichem",
                        "cat_no": cat_no,
                        "package": package,
                    }
                    yield ProductPackage(**dd)
        next_page = response.xpath('//img[@src="/images/aaanext.gif"]/../@onclick').get("")
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
