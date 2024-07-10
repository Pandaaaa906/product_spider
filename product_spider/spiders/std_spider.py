import json
from urllib.parse import urljoin

import requests
from scrapy import FormRequest

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


def get_total_page(response) -> int:
    if response.ok:
        data = json.loads(response.text)
        return data['count']
    print('获取页数失败')
    return 0


class STDSpider(BaseSpider):
    name = "std"
    start_urls = [f"http://www.standardpharm.com/portal/list/index/id/11/shorttag/{char}.html"
                  for char in ascii_uppercase ]
    base_url = "http://www.standardpharm.com/"

    def parse(self, response, **kwargs):
        a_nodes = response.xpath('//ul[@class="pro"]/li/a')
        for a in a_nodes:
            url = urljoin(self.base_url, a.xpath('./@href').get(""))
            parent = getattr(re.search(r'.+(?=\s\()', a.xpath('./text()').get()), "group")()
            yield Request(url, callback=self.list_parse, meta={"parent": parent})

    def list_parse(self, response):
        nodes = response.xpath('//ul[@class="pro"]/li')
        tmp = './/*[contains(text(),{!r})]/text()'
        for node in nodes:
            d = {
                "brand": "std",
                "parent": response.meta.get('parent'),
                "cat_no": node.xpath(tmp.format("STD No.")).get("").replace("STD No.", "").strip(),
                "cas": node.xpath(tmp.format("CAS No.")).get("").replace("CAS No.", "").strip(),
                "en_name": node.xpath('./h3//p/text()').get(),
                "img_url": urljoin(self.base_url, node.xpath('./span//img/@src').get()),
                "mf": node.xpath(tmp.format("Chemical Formula")).get("").replace("Chemical Formula :", "").strip(),
                "prd_url": urljoin(self.base_url, node.xpath('./a/@href').get('')),
            }
            yield RawData(**d)


    def parse_api_list(self, response):
        data = json.loads(response.text)['data']
        for api in data:
            page1_response = requests.post(self.cat_url, data={
                'page': '1',
                'limit': '200',
                'keyword': str(api['cat_id']),
                'id': str(api['cat_id']),
                'ip': ''
            })
            total_page = get_total_page(page1_response)
            for i in range(0, total_page):
                yield FormRequest(url=self.cat_url, formdata={
                    'id': str(api['cat_id']),
                    'keyword': str(api['cat_id']),
                    'ip': '',
                    'page': str(i + 1),
                    'limit': '200',
                }, callback=self.parse_cat_list)

    def parse_cat_list(self, response):
        data = json.loads(response.text)['data']
        for d in data:
            _d = {
                'brand': self.brand,
                'parent': strip(d['cat_cn_name']),
                'cat_no': d['code'],
                'chs_name': strip(d['cn_name']),
                'en_name': strip(d['name']),
                'cas': d['cas'],
                'mf': d['numerator'],
                'mw': d['molecular_weight'],
                'img_url': urljoin(self.img_base_url, d['structure']),
                'prd_url': f'{self.base_url}/product-detail.html?id={d["id"]}&catid={d["cat_id"]}',
            }
            yield RawData(**_d)
