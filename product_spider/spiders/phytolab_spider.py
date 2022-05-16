import re

import json

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class PhytolabSpider(BaseSpider):
    """德国中草药"""
    name = "phytolab"
    allow_domain = ["phytolab.com"]
    start_urls = ["https://phyproof.phytolab.com/api/v1/substance"]

    base_url = 'https://phyproof.phytolab.com/'

    def parse(self, response, **kwargs):
        datas = json.loads(response.text.strip('\n'))
        for data in datas:
            cat_no = str(data['productId'])
            en_name = data['en'].get('name', '')
            d = {
                "brand": self.name,
                "cat_no": cat_no,
                "cas": data['cas'].get('full', ''),
                "mw": data.get('molecularWeight', ''),
                "mf": data.get('molecularFormula', ''),
                "en_name": en_name,
                "info2": data.get('storageTemperature', ''),
                "parent": data['classification']['en'].get('subgroup3', '')
                          or data['classification']['en'].get('subgroup2', '')
                          or data['classification']['en'].get('subgroup1', ''),
                "prd_url": f'https://phyproof.phytolab.com/en/reference-substances/details/{en_name}-{cat_no}',
                "img_url": f'https://phyproof.phytolab.com/f/product_img/jpg/reference-substance-withaferin-a-{cat_no}.jpg'
            }
            yield RawData(**d)
            for key, value in data.items():
                m = re.match(r'^price(?P<unit>[a-zA-Z]{1,2})(?P<quantity>\d+)$', key)
                if not m:
                    continue
                dd = {
                    "brand": self.name,
                    "cat_no": str(data['productId']),
                    "cost": round(value, 2),
                    "package": f'{m["quantity"]}{m["unit"].lower()}',
                    "currency": "EUR"
                }
                yield ProductPackage(**dd)
