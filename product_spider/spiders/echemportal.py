import json
from itertools import product
from string import digits

from scrapy.http import JsonRequest

from product_spider.items import EChemPortalItem
from product_spider.utils.spider_mixin import BaseSpider


class EChemPortalSpider(BaseSpider):
    name = "echemportal"
    allow_domain = ["echemportal.org"]
    start_urls = []
    search_api = "https://www.echemportal.org/echemportal/api/substance-search"

    def _build_search_data(self, keyword, page: int = 1, per_page: int = 50):
        return {
            "query_term": keyword,
            "paging": {
                "offset": (page - 1) * per_page, "limit": per_page
            },
            "filtering": [],
            "sorting": [],
            "participants": [
                40, 661, 320, 101, 3, 380, 181, 600, 701, 781, 761, 420, 5, 280, 260, 640, 7, 8, 10, 660, 440, 11, 340,
                480, 60, 12, 14, 742, 1,
                220, 620, 16, 17, 18
            ],
            "ghs_blocks": [],
            "new_query": True
        }

    def _make_request(self, keyword, page: int = 1, per_page: int = 50):
        return JsonRequest(
            self.search_api,
            data=self._build_search_data(keyword, page=page, per_page=per_page),
            meta={"keyword": keyword, "page": page, "per_page": per_page}
        )

    def start_requests(self):
        keywords = (f"{''.join(l)}-{k}{j}-{i}" for i, j, k, *l in product(digits, repeat=5))
        page = 1
        per_page = 50
        for keyword in keywords:
            yield self._make_request(keyword, page=page, per_page=per_page)

    def parse(self, response, **kwargs):
        j = response.json()
        results = j.get('results', [])
        for result in results:
            result["echem_id"] = result.pop("id")
            extra_keys = result.keys() - EChemPortalItem.fields.keys()
            attrs = {}
            for key in extra_keys:
                attrs[key] = result.pop(key)
            result['attrs'] = json.dumps(attrs, ensure_ascii=False)
            yield EChemPortalItem(**result)
        page_info = j.get('page_info', {})
        total_pages = page_info.get('total_pages', 0)
        page = response.meta.get("page", 0)
        per_page = response.meta.get("per_page", 50)
        if page >= total_pages:
            return
        keyword = response.meta.get("keyword")
        if not keyword:
            return
        yield self._make_request(keyword, page=page+1, per_page=per_page)
        pass
