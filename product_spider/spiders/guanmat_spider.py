import re
from urllib.parse import urlencode, urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class GuanMatSpider(BaseSpider):
    name = "guanmat"
    list_url = "http://www.guanmat.com/comp/portalResProduct/list.do"
    list_page_size = 16

    def _make_list_request(self, page=1):
        d = {
            "compId": "portalResProduct_list-1655611042042",
            "orderType": 0,
            "orderColumn": "def",
            "productCateId": 9,
            "pageSize": self.list_page_size,
            "currentPage": page,
        }
        return Request(
            url=f"{self.list_url}?{urlencode(d)}",
            method='POST',
            meta={"cur_page": page}
        )

    def start_requests(self):
        yield self._make_list_request(1)

    def parse(self, response, **kwargs):
        products = response.xpath('//div[@class="p_Product proLi"]')
        for prd in products:
            rel_url = prd.xpath('./a/@href').get()
            img_url = prd.xpath('./a//img/@src').get()
            _id = (m := re.search(r'/(\d+)\.html$', rel_url)) and m.group(1)
            d = {
                "brand": self.name,
                "cat_no": f"{self.name.upper()}-{_id}",
                "chs_name": prd.xpath('./a//div[@class="p_title proTitle"]/text()').get(),
                "img_url": img_url and urljoin(response.url, img_url),
                "prd_url": rel_url and urljoin(response.url, rel_url),
            }
            yield RawData(**d)
        if len(products) == self.list_page_size:
            next_page = response.meta.get('cur_page', 1) + 1
            yield self._make_list_request(next_page)




