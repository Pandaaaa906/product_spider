import re
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class HuiChengChemSpider(BaseSpider):
    name = "huichengchem"
    start_urls = ["http://huichengchem.weba.testwebsite.cn/pro.html"]
    allowed_domains = ["huichengchem.com"]

    def parse(self, response, **kwargs):
        rows = response.xpath('//table[@id="tb"]/tr[./td[@align="center"]]')
        tmpl = './/td[text()={!r}]/following-sibling::td//text()'
        for row in rows:
            img_url = row.xpath('./td/img/@src').get()
            cas = row.xpath(tmpl.format("CAS #：")).get()
            cas = cas.strip('[]') if isinstance(cas, str) else None
            rel_url = row.xpath('.//a/@href').get()
            _id = (m := re.search(r'id/(\d+)\.html', rel_url)) and m.group(1)
            d = {
                "brand": self.name,
                "cat_no": cas or _id,
                "chs_name": ''.join(row.xpath('.//a/strong//text()').getall()),
                "mf": ''.join(row.xpath(tmpl.format("分子式：")).getall()),
                "mw": ''.join(row.xpath(tmpl.format("分子量：")).getall()),
                "cas": cas,
                "prd_url": rel_url and urljoin(response.url, rel_url),
                "img_url": img_url and urljoin(response.url, img_url),
            }
            yield RawData(**d)

        next_page = response.xpath('//a[text()="下一页"]/@href').get()
        if next_page:
            yield Request(
                url=urljoin(response.url, next_page),
                callback=self.parse,
                dont_filter=True
            )
