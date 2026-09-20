import json
import re
from urllib.parse import quote, urljoin

from scrapy import Request

from product_spider.items.ichembio_items import IchembioData
from product_spider.utils.spider_mixin import BaseSpider

# label（页面原文） -> item 字段
FIELD_MAP = {
    "CAS No.": "cas",
    "中文名称": "zh_name",
    "英文名称": "en_name",
    "中文同义词": "synonyms_zh",
    "英文同义词": "synonyms_en",
    "IUPAC Name": "iupac_name",
    "分子式": "mf",
    "分子量": "mw",
    "Smiles": "smiles",
    "InChI key": "inchi_key",
    "Reaxy-Rn": "reaxy_rn",
    "MDL编号": "mdl_number",
    "PubChem编号": "pubchem_id",
    "自燃温度": "autoignition_temp",
    "形态": "appearance",
    "折射率": "refractive_index",
    "熔点": "melting_point",
    "沸点": "boiling_point",
    "溶解性": "solubility",
    "密度": "density",
    "闪点(°F)": "flash_point_f",
    "闪点(°C)": "flash_point_c",
    "旋光": "optical_rotation",
    "敏感性": "sensitivity",
    "储存温度": "storage_temp",
    "运输条件": "transport_condition",
    "描述及应用": "description",
    "警示用语": "signal_word",
    "危险声明": "hazard_statements",
    "预防措施说明": "precautionary_statements",
    "危险级别": "danger_level",
    "UN编码": "un_number",
    "包装等级": "package_grade",
    "危险分类": "hazard_class",
    "储存分类代码": "storage_class",
    "WGK": "wgk",
    "个人防护装备": "ppe",
}

LABEL_XPATH = (
    '//div[@class="content-item-label"][normalize-space()={label!r}]'
    "/following-sibling::div[1]"
)


def get_value(response, label: str):
    texts = response.xpath(LABEL_XPATH.format(label=label) + "//text()").getall()
    value = " ".join("".join(texts).split())
    return None if value in {"", "-"} else value


def get_ghs_icons(response):
    srcs = response.xpath(LABEL_XPATH.format(label="象形图") + "//img/@src").getall()
    icons = [m.group(0) for s in srcs if (m := re.search(r"GHS\d+", s))]
    return json.dumps(icons, ensure_ascii=False) if icons else None


class IchembioSpider(BaseSpider):
    name = "ichembio"
    allowed_domains = ["ichembio.com"]
    base_url = "https://www.ichembio.com"
    custom_settings = {
        # "DOWNLOADER_MIDDLEWARES": {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        "PROXY_POOL_REFRESH_STATUS_CODES": [403, 503, 302],
        "RETRY_TIMES": 5,
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 1,
    }

    def __init__(self, cas_file: str = None, **kwargs):
        self.cas_file = cas_file
        super().__init__(**kwargs)

    def is_proxy_invalid(self, request, response):
        if response.status in {403, 302} or 500 <= response.status < 600:
            self.logger.warning(f"status code:{response.status}, {request.url}")
            return True
        return False

    @staticmethod
    def _read_cas_file(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                cas = line.strip()
                if cas and not cas.startswith("#"):
                    yield cas

    def _start_requests(self):
        if self.cas_file:
            for cas in self._read_cas_file(self.cas_file):
                yield Request(f"{self.base_url}/cas/{cas}", callback=self.parse_detail)
            return
        for i in range(100):
            for j in range(10):
                suffix = f"{i:02d}-{j}"
                yield Request(
                    f"{self.base_url}/search?query={suffix}&page_size=100",
                    meta={"suffix": suffix, "first_page": True},
                )

    def keyword_search(self, keyword: str, search_params: dict = None):
        yield Request(
            f"{self.base_url}/search?query={quote(keyword)}&page_size=100",
            callback=self.parse,
            meta={
                "keyword": keyword,
                "search_params": search_params,
                "task_id": self.task_id,
            },
        )

    def parse(self, response):
        suffix = response.meta.get("suffix")
        # 枚举模式第一页：结果达到单查询上限（约500条）时告警，可能漏采
        if suffix and response.meta.get("first_page"):
            total = response.xpath('//span[contains(@class,"total-num")]/text()').get(
                ""
            )
            if total.isdigit() and int(total) >= 500:
                self.logger.warning(f"后缀 {suffix} 结果达上限 {total} 条，可能漏采")

        seen = set()
        for href in response.xpath(
            '//div[contains(@class,"search-list-item")]//a[contains(@href,"/cas/")]/@href'
        ).getall():
            path = href.split("?")[
                0
            ]  # 去掉 log_rc 等追踪参数，保证跨后缀 dupefilter 去重
            if path in seen:
                continue
            seen.add(path)
            # 搜索有模糊兜底，枚举模式只保留 CAS 以 -{suffix} 结尾的条目
            if suffix and not path.rsplit("/", 1)[-1].endswith(f"-{suffix}"):
                continue
            yield Request(urljoin(response.url, path), callback=self.parse_detail)

        next_page = response.xpath('//a[@class="page-link"][@rel="next"]/@href').get()
        if next_page:
            # 翻页请求不带 first_page 标志
            meta = {k: v for k, v in response.meta.items() if k != "first_page"}
            yield Request(
                urljoin(response.url, next_page), callback=self.parse, meta=meta
            )

    def parse_detail(self, response):
        if "页面不存在" in response.xpath("//title/text()").get(""):
            self.logger.warning(f"页面不存在: {response.url}")
            return
        d = {field: get_value(response, label) for label, field in FIELD_MAP.items()}
        d["ghs_icons"] = get_ghs_icons(response)
        d["url"] = response.url
        yield IchembioData(**d)
