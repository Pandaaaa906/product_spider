import json
from string import ascii_uppercase
from urllib.parse import urljoin

from scrapy import FormRequest

from product_spider.items import RawData
from product_spider.utils.functions import dumps
from product_spider.utils.spider_mixin import BaseSpider


class STDSpider(BaseSpider):
    name = "std"
    start_urls = []
    base_url = "https://www.standardpharm.com/"
    api_url = "https://www.standardpharm.com/solr/search/letter"

    custom_settings = {
        'RETRY_TIMES': 10,
    }

    def _start_requests(self):
        form_data = {
            "id": '',
            "keyword": '',
            "page": '1',
            "limit": '40',
            "ip": '',
        }
        yield FormRequest(
            self.api_url,
            formdata=form_data,
            callback=self.parse,
            meta={"form_data": form_data}
        )

    def parse(self, response, **kwargs):
        j_obj = json.loads(response.text)
        if (code := j_obj.get('code')) != 200:
            msg = j_obj.get('msg')
            self.logger.warning(f"error occurred {code=}, {msg=}, {response.url}")
            return
        data = j_obj.get('data', [])
        for product in data:
            img_url = product.get('structure')
            prd_id = product.get('id')
            d = {
                "brand": self.name,
                "parent": product.get('cat_name'),
                "cat_no": product.get('code'),
                "en_name": product.get('name'),
                "chs_name": product.get('cn_name'),
                "cas": product.get('cas'),
                "mf": product.get('numerator'),
                "mw": product.get('molecular_weight'),
                "info1": product.get('chemistry_name'),
                "img_url": img_url and urljoin(self.base_url, img_url),
                "prd_url": prd_id and f"https://www.standardpharm.com/product-detail.html?id={prd_id}",
                "attrs": dumps({
                    "remark": product.get("remark"),
                }),
            }
            yield RawData(**d)
        form_data = response.meta.get("form_data")
        total_page = j_obj.get('count', 0)
        page = int(form_data.get("page", 0))
        if page >= total_page:
            return
        form_data['page'] = str(page + 1)
        yield FormRequest(
            self.api_url,
            formdata=form_data,
            callback=self.parse,
            meta={"form_data": form_data}
        )
