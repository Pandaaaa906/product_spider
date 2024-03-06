import json
import re
from datetime import datetime, timedelta
from enum import Enum
from urllib.parse import urljoin
from uuid import uuid4

import psycopg2
from scrapy import Request

from product_spider.items.chemsrc_items import ChemSrcChemical
from product_spider.sql.chemsrc_sql import sql_fetch_cas
from product_spider.utils.spider_mixin import BaseSpider


class ChemSrcStrategy(str, Enum):
    CATO_PROD = 'CATO_PROD'
    LOCAL = 'LOCAL'


class ChemSrcSpider(BaseSpider):
    name = "chemsrc"
    start_urls = ['https://www.chemsrc.com/searchResult/106897-30-7/']
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'PROXY_POOL_REFRESH_STATUS_CODES': [403, 503, 302],
        'RETRY_TIMES': 10,
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 2,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }

    def __init__(
            self, strategy: ChemSrcStrategy = ChemSrcStrategy.CATO_PROD,
            itersize: int = 5000,
            ignore_days: int = 60,
            **kwargs
    ):
        self.strategy = strategy
        self.itersize = itersize
        self.ignore_days = ignore_days
        super().__init__(**kwargs)

    def get_urls_from_db(self):
        db_settings = self.settings["DATABASE"]
        now = datetime.now()
        with psycopg2.connect(**db_settings['params']) as conn:
            with conn.cursor(name=f"chemsrc_{uuid4().hex}") as cur:
                cur.itersize = self.itersize
                cur.execute(sql_fetch_cas, [now - timedelta(days=self.ignore_days)])
                for (cas, ) in cur:
                    yield f"https://www.chemsrc.com/searchResult/{cas}/"

    def start_requests(self):
        if self.strategy == ChemSrcStrategy.CATO_PROD:
            for url in self.get_urls_from_db():
                yield Request(url)
        else:
            return super().start_requests()

    def parse(self, response, **kwargs):
        # 如果搜索结果直接跳转到明细页，则直接处理
        if response.meta.get('redirect_reasons') == [301]:
            yield from self.parse_detail(response)
            return
        prd_urls = response.xpath('//tr[@class="rowDat"]/td[2]/a[1]/@href').getall()
        for rel_url in prd_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

        next_page = response.xpath('//li[@class="active"]/following-sibling::li/a/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse)

    def parse_detail(self, response):
        tmpl = '//table[@id="baseTbl"]//th[text()={!r}]/following-sibling::td[1]//text()'
        chemsrc_id = (m := re.search(r'cas/([^.]+).html', response.url)) and m.group(1)

        tmp_cas, *_ = chemsrc_id.split('_')

        if h := response.xpath('//h3[text()="根据国家相关法律法规、政策规定，特殊危化品不显示该产品信息！"]').get():
            yield ChemSrcChemical(**{
                "chemsrc_id": chemsrc_id,
                "url": response.url,
                "cas": tmp_cas,
                "content_html": h,
            })
            return

        raw_chemsrc_update_time = response.xpath('//div[contains(text(), "更新时间：")]/text()').get()
        chemsrc_update_time = raw_chemsrc_update_time and (m := re.sub(r'^更新时间：', '', raw_chemsrc_update_time))
        d = {
            "chemsrc_id": chemsrc_id,
            "chemsrc_update_time": chemsrc_update_time,
            "url": response.url,

            "generic_name": response.xpath(tmpl.format("常用名")).get(),
            "en_name": ''.join(response.xpath(tmpl.format("英文名")).getall()),
            "cas": ''.join(response.xpath(tmpl.format("CAS号")).getall()) or tmp_cas,
            "mw": response.xpath(tmpl.format("分子量")).get(),
            "mf": ''.join(response.xpath(tmpl.format("分子式")).getall()),
            "density": response.xpath(tmpl.format("密度")).get(),
            "boiling_point": response.xpath(tmpl.format("沸点")).get(),
            "melting_point": response.xpath(tmpl.format("熔点")).get(),
            "flash_point": response.xpath(tmpl.format("闪点")).get(),

            "data_category": json.dumps(
                response.xpath('//ul[@id="nav"]/li[@class="disno"]/a/text()').getall(),
                ensure_ascii=False),
            "content_html": response.xpath('//div[@id="myScrollspy"]/following-sibling::div').get()
        }
        yield ChemSrcChemical(**d)
