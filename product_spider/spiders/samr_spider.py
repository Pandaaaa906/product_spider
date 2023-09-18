import json
from urllib.parse import urlencode

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.functions import strip


class SamrSpider(BaseSpider):
    name = 'samr'
    url_api = "https://std.samr.gov.cn/gsm/search/gsmPage"
    url_detail = "https://std.samr.gov.cn/gsm/search/gsmDetailed"

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'RETRY_HTTP_CODES': [403, 504, 503, ],
        'RETRY_TIMES': 10,
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'PROXY_POOL_REFRESH_STATUS_CODES': {401, },
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }

    def _make_reqeust(
            self, keyword: str = '', page=1, page_size=10,
            level=1, state=None, sort_order='asc',
    ):
        d = {
            "searchText": keyword,
            "level": level,
            "state": state,
            "sortOrder": sort_order,
            "pageSize": page_size,
            "pageNumber": page,
            "_": 1695018094815
        }
        return Request(
            f"https://std.samr.gov.cn/gsm/search/gsmPage?{urlencode(d)}",
            meta={"page": page, "page_size": page_size},
            callback=self.parse,
        )

    def start_requests(self):
        yield self._make_reqeust()

    def parse(self, response, **kwargs):
        j = json.loads(response.text)
        for row in j.get('rows', []):
            yield Request(f"{self.url_detail}?id={row['id']}", callback=self.parse_detail)

        total = j.get('total', 0)
        page_size = response.meta.get('page_size', 10)
        page = response.meta.get('page', 0)

        if total < page_size * page:
            return

        yield self._make_reqeust(
            "", page=page+1, page_size=page_size,
        )

    def parse_detail(self, response):
        tmpl = "//dt[text()={!r}]/following-sibling::dd[1]/text()"
        attrs = {
            "desc": strip(''.join(response.xpath('//div/p//text()').getall())),
            "prj_code": response.xpath(tmpl.format("计划项目编号")).get(),
            "valuation_date": response.xpath(tmpl.format("定值日期")).get(),
            "approval_date": response.xpath(tmpl.format("批准日期")).get(),
            "expiry_date": response.xpath(tmpl.format("有效截止日期")).get(),
            "status": response.xpath(tmpl.format("状态")).get(),
            "organizations": response.xpath('//div[./h2/text()="研/复制单位"]/following-sibling::div//a/text()').getall(),
        }
        d = {
            "brand": self.name,
            "cat_no": response.xpath(tmpl.format("标准样品编号")).get(),
            "chs_name": ''.join(response.xpath("//h4//text()").getall()),
            "en_name": ''.join(response.xpath("//h5//text()").getall()),
            "info4": response.xpath(tmpl.format("备注")).get(),
            "prd_url": response.url,
            "attrs": json.dumps(attrs),
        }
        yield RawData(**d)
