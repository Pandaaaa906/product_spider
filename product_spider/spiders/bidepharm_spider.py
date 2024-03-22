import json
import re
from base64 import b64encode
from itertools import product
from string import digits
from urllib.parse import urljoin, urlencode

from scrapy.http import JsonRequest

from product_spider.items import RawData, ProductPackage, RawSupplierQuotation
from product_spider.utils.spider_mixin import BaseSpider


def clean_highlights(value):
    if not value:
        return
    return re.sub(r'</?em>', '', value)


class BidepharmSpider(BaseSpider):
    name = "bidepharm"
    brand = "毕得"
    start_urls = ["https://www.bidepharm.com/", ]
    base_url = "https://www.bidepharm.com/"
    products_url = "https://www.bidepharm.com/webapi/v1/productlistbykeyword"

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'RETRY_HTTP_CODES': [503, 504],
        'RETRY_TIMES': 20,
        'CONCURRENT_REQUESTS': 3
    }

    def is_proxy_invalid(self, request, response):
        proxy = request.meta.get('proxy')
        is_detected = False
        if response.status in {503, 403, 504}:
            is_detected = True
        try:
            j = json.loads(response.text)
            if j.get('value', {}).get('errmsg'):
                is_detected = True
        except Exception as e:
            self.logger.warning(e)
            pass
        if is_detected:
            self.logger.warning(f'status code:{response.status}, {request.url}, using proxy {proxy}')
            return True
        return False

    def _search_request(self, response, keyword, page=1, per_page=50, **kwargs):
        meta = kwargs.pop("meta", {})
        if not (_xsrf := response.meta.get('_xsrf')):
            cookies = response.headers.getlist('Set-Cookie')[0]
            _xsrf = (m := re.search(rb'_xsrf=(?P<_xsrf>[^;]+)', cookies)) and m.group(1)
        j = {"keyword": keyword, "pageindex": page, "pagesize": per_page}
        p = {
            "params": b64encode(json.dumps(j).encode()),
            "_xsrf": _xsrf,
        }
        return JsonRequest(
            url=f"{self.products_url}?{urlencode(p)}",
            meta={"keyword": keyword, "_xsrf": _xsrf, **meta},
            **kwargs
        )

    def parse(self, response, **kwargs):
        for t in product(digits, repeat=2):
            keyword = ''.join(t)
            yield self._search_request(
                response, keyword,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        j = json.loads(response.text)
        if not (value := j['value']):
            return
        for row in (rows := value.get('result', [])):
            d = {
                "brand": self.brand,
                "cat_no": clean_highlights(row.get("p_bd")),
                "en_name": clean_highlights(row.get("p_name_en")),
                "chs_name": clean_highlights(row.get("p_name_cn")),
                "cas": clean_highlights(row.get("p_cas")),
                "purity": clean_highlights(row.get("p_purity")),
                "info2": clean_highlights(row.get("p_storage")),
                "img_url": urljoin(response.url, row.get("p_proimg")),
                "prd_url": urljoin("https://www.bidepharm.com/products/", row.get("s_url")),
            }
            yield RawData(**d)
            for package in row.get('priceList', []):
                dd = {
                    "brand": self.brand,
                    "cat_no": d['cat_no'],
                    "package": package.get('pr_size'),
                    "cost": package.get('pr_rmb'),
                    "currency": "RMB",
                    "delivery_time": 'in-stock' if row.get('p_ishasstock') else None
                }
                ddd = {
                    "platform": self.name,
                    "source_id": f"{self.name}_{dd['cat_no']}",
                    "vendor": self.name,
                    "brand": self.name,
                    "cat_no": dd['cat_no'],
                    "package": dd['package'],
                    "discount_price": dd['cost'],
                    "price": dd['cost'],
                    "currency": dd["currency"],
                    "stock_num": '1' if row.get('p_ishasstock') else None,
                    "cas": d["cas"],
                }
                yield ProductPackage(**dd)
                yield RawSupplierQuotation(**ddd)

        total = value.get('total', 0)
        per_page = value.get('pagesize', 0)
        page_index = value.get('pageindex', 0)
        keyword = response.meta.get('keyword')
        # if per_page * page_index >= total:
        #     return
        if len(rows) == 0:
            return
        yield self._search_request(
            response, keyword, page=page_index+1, per_page=per_page,
            callback=self.parse_list,
        )

