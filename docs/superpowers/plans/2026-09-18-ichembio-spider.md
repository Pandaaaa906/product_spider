# IchembioSpider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `IchembioSpider`，采集 ichembio.com 化学品详情页全部 38 个字段（重点为安全信息章节），支持后缀枚举、CAS 文件、API 关键词搜索三种模式。

**Architecture:** 单 spider 三模式（继承 `BaseSpider`），SSR 页面纯 XPath 解析（无 Playwright）；新增 `IchembioData` item（`scrapyautodb.OrderedItem`），扩展 `KeywordSearchRedisPipeline` 支持该类型。

**Tech Stack:** Scrapy, scrapyautodb, pytest（fixture HTML 离线测试）。

**Spec:** `docs/superpowers/specs/2026-09-18-ichembio-spider-design.md`

**项目规则：所有 commit 步骤必须先获得用户明确批准（CLAUDE.md：NEVER Auto-Commit）。**

---

## 已验证的页面事实（实现依据，勿再猜测）

- 详情页字段结构统一：`//div[@class="content-item-label"][normalize-space()="LABEL"]/following-sibling::div[1]`
- 38 个 label 原文见 spec 字段表（如 `CAS No.`、`Smiles`、`InChI key`、`闪点(°F)`、`象形图`、`UN编码`、`包装等级`）
- GHS 图标：象形图 value 内 `<img src="/datasite/images/image/GHS/GHS02.svg">`，从文件名正则提取
- 空值显示为 `-`，转 None
- 无效 CAS 详情页：HTTP 200，title 含 `页面不存在`，无 `content-item-label`
- 列表页条目：`//div[contains(@class,"search-list-item")]//a[contains(@href,"/cas/")]/@href`，每个卡片 3 个相同链接，需页内去重；href 带 `?log_rc=...` 查询串，须取 `?` 前路径
- 搜索有模糊兜底：无精确匹配时也返回无关条目 → 枚举模式过滤掉 CAS 不以 `-{suffix}` 结尾的条目
- 下一页：`//a[@class="page-link"][@rel="next"]/@href`；总数：`//span[contains(@class,"total-num")]/text()`
- 每页条数参数：`page_size=100`（已实测生效）
- 现有 pipelines 按字段存在性判断，`IchembioData`（无 `cat_no`、有 `cas`）可安全穿过 `DropNullCatNoPipeline` / `FilterNAValue` 等，无需改动
- fixture 已就位：`tests/fixtures/ichembio_detail_67-56-1.html`（甲醇详情页，UTF-8）

---

### Task 1: IchembioData Item

**Files:**
- Create: `product_spider/items/ichembio_items.py`
- Modify: `product_spider/items/__init__.py`

- [ ] **Step 1: 创建 item**

```python
# product_spider/items/ichembio_items.py
import scrapyautodb as scrapy


class IchembioData(scrapy.OrderedItem):
    cas = scrapy.Field()  # CAS No.
    zh_name = scrapy.Field()  # 中文名称
    en_name = scrapy.Field()  # 英文名称
    synonyms_zh = scrapy.Field()  # 中文同义词
    synonyms_en = scrapy.Field()  # 英文同义词
    iupac_name = scrapy.Field()  # IUPAC Name
    mf = scrapy.Field()  # 分子式
    mw = scrapy.Field()  # 分子量
    smiles = scrapy.Field()  # Smiles
    inchi_key = scrapy.Field()  # InChI key
    reaxy_rn = scrapy.Field()  # Reaxy-Rn
    mdl_number = scrapy.Field()  # MDL编号
    pubchem_id = scrapy.Field()  # PubChem编号

    autoignition_temp = scrapy.Field()  # 自燃温度
    appearance = scrapy.Field()  # 形态
    refractive_index = scrapy.Field()  # 折射率
    melting_point = scrapy.Field()  # 熔点
    boiling_point = scrapy.Field()  # 沸点
    solubility = scrapy.Field()  # 溶解性
    density = scrapy.Field()  # 密度
    flash_point_f = scrapy.Field()  # 闪点(°F)
    flash_point_c = scrapy.Field()  # 闪点(°C)
    optical_rotation = scrapy.Field()  # 旋光
    sensitivity = scrapy.Field()  # 敏感性
    storage_temp = scrapy.Field()  # 储存温度
    transport_condition = scrapy.Field()  # 运输条件
    description = scrapy.Field()  # 描述及应用

    ghs_icons = scrapy.Field()  # 象形图，GHS 代码 JSON 列表
    signal_word = scrapy.Field()  # 警示用语
    hazard_statements = scrapy.Field()  # 危险声明
    precautionary_statements = scrapy.Field()  # 预防措施说明
    danger_level = scrapy.Field()  # 危险级别
    un_number = scrapy.Field()  # UN编码
    package_grade = scrapy.Field()  # 包装等级
    hazard_class = scrapy.Field()  # 危险分类
    storage_class = scrapy.Field()  # 储存分类代码
    wgk = scrapy.Field()  # WGK
    ppe = scrapy.Field()  # 个人防护装备

    url = scrapy.Field()

    class Meta:
        indexes = (
            (('cas',), True),
        )
```

- [ ] **Step 2: 导出**

`product_spider/items/__init__.py` 末尾追加：

```python
from .ichembio_items import IchembioData
```

- [ ] **Step 3: 验证导入**

Run: `uv run python -c "from product_spider.items import IchembioData; print(len(IchembioData.fields))"`
Expected: 输出 `39`

- [ ] **Step 4: Commit（需用户确认）**

```bash
git add product_spider/items/ichembio_items.py product_spider/items/__init__.py
git commit -m "feat: add IchembioData item"
```

---

### Task 2: parse_detail 失败测试

**Files:**
- Test: `tests/test_ichembio_spider.py`
- Fixture: `tests/fixtures/ichembio_detail_67-56-1.html`（已存在）

- [ ] **Step 1: 写测试**

```python
# tests/test_ichembio_spider.py
import json
from pathlib import Path

from scrapy.http import Request, TextResponse

from product_spider.spiders.ichembio_spider import IchembioSpider

FIXTURE = Path(__file__).parent / 'fixtures' / 'ichembio_detail_67-56-1.html'
DETAIL_URL = 'https://www.ichembio.com/cas/67-56-1'


def make_response(body: bytes, url: str = DETAIL_URL) -> TextResponse:
    return TextResponse(url=url, body=body, encoding='utf-8', request=Request(url))


def test_parse_detail_extracts_fields():
    spider = IchembioSpider()
    items = list(spider.parse_detail(make_response(FIXTURE.read_bytes())))
    assert len(items) == 1
    item = items[0]
    assert item['cas'] == '67-56-1'
    assert item['zh_name'] == '甲醇 溶液'
    assert item['en_name'] == 'Methanol'
    assert item['smiles'] == 'CO'
    assert item['mf'] == 'CH4O'  # 页面为 CH<SUB>4</SUB>O，join 后无空格
    assert item['mw'] == '32.04'
    assert item['mdl_number'] == 'MFCD00004595'
    assert item['appearance'] == 'liquid'
    assert item['un_number'] == 'UN1230'
    assert item['package_grade'] == 'II'
    assert item['danger_level'] == 'Danger'
    assert item['hazard_statements'] == 'H225,H301,H311,H331,H370'
    assert item['precautionary_statements'] == 'P210 - P260 - P280 - P301 + P310 - P311'
    assert item['wgk'] == 'WGK 1'
    assert json.loads(item['ghs_icons']) == ['GHS02', 'GHS06', 'GHS08']
    assert item['url'] == DETAIL_URL


def test_parse_detail_dash_to_none():
    spider = IchembioSpider()
    (item,) = list(spider.parse_detail(make_response(FIXTURE.read_bytes())))
    assert item['inchi_key'] is None  # 页面显示 '-'
    assert item['signal_word'] is None
    assert item['reaxy_rn'] is None


def test_parse_detail_not_found_page():
    body = '<html><head><title>页面不存在｜iChemBio</title></head><body></body></html>'
    resp = make_response(body.encode('utf-8'), url='https://www.ichembio.com/cas/000-00-0')
    spider = IchembioSpider()
    assert list(spider.parse_detail(resp)) == []
```

- [ ] **Step 2: 确认测试失败**

Run: `uv run pytest tests/test_ichembio_spider.py -v`
Expected: FAIL，`ModuleNotFoundError: product_spider.spiders.ichembio_spider`

---

### Task 3: Spider 骨架与 parse_detail

**Files:**
- Create: `product_spider/spiders/ichembio_spider.py`
- Test: `tests/test_ichembio_spider.py`

- [ ] **Step 1: 实现**

```python
# product_spider/spiders/ichembio_spider.py
import json
import re
from urllib.parse import quote, urljoin

from scrapy import Request

from product_spider.items.ichembio_items import IchembioData
from product_spider.utils.spider_mixin import BaseSpider

# label（页面原文） -> item 字段
FIELD_MAP = {
    'CAS No.': 'cas',
    '中文名称': 'zh_name',
    '英文名称': 'en_name',
    '中文同义词': 'synonyms_zh',
    '英文同义词': 'synonyms_en',
    'IUPAC Name': 'iupac_name',
    '分子式': 'mf',
    '分子量': 'mw',
    'Smiles': 'smiles',
    'InChI key': 'inchi_key',
    'Reaxy-Rn': 'reaxy_rn',
    'MDL编号': 'mdl_number',
    'PubChem编号': 'pubchem_id',
    '自燃温度': 'autoignition_temp',
    '形态': 'appearance',
    '折射率': 'refractive_index',
    '熔点': 'melting_point',
    '沸点': 'boiling_point',
    '溶解性': 'solubility',
    '密度': 'density',
    '闪点(°F)': 'flash_point_f',
    '闪点(°C)': 'flash_point_c',
    '旋光': 'optical_rotation',
    '敏感性': 'sensitivity',
    '储存温度': 'storage_temp',
    '运输条件': 'transport_condition',
    '描述及应用': 'description',
    '警示用语': 'signal_word',
    '危险声明': 'hazard_statements',
    '预防措施说明': 'precautionary_statements',
    '危险级别': 'danger_level',
    'UN编码': 'un_number',
    '包装等级': 'package_grade',
    '危险分类': 'hazard_class',
    '储存分类代码': 'storage_class',
    'WGK': 'wgk',
    '个人防护装备': 'ppe',
}

LABEL_XPATH = (
    '//div[@class="content-item-label"][normalize-space()={label!r}]'
    '/following-sibling::div[1]'
)


def get_value(response, label: str):
    texts = response.xpath(LABEL_XPATH.format(label=label) + '//text()').getall()
    value = ' '.join(''.join(texts).split())
    return None if value in {'', '-'} else value


def get_ghs_icons(response):
    srcs = response.xpath(LABEL_XPATH.format(label='象形图') + '//img/@src').getall()
    icons = [m.group(0) for s in srcs if (m := re.search(r'GHS\d+', s))]
    return json.dumps(icons, ensure_ascii=False) if icons else None


class IchembioSpider(BaseSpider):
    name = "ichembio"
    allowed_domains = ["ichembio.com"]
    base_url = "https://www.ichembio.com"
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'PROXY_POOL_REFRESH_STATUS_CODES': [403, 503, 302],
        'RETRY_TIMES': 5,
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 1,
    }

    def is_proxy_invalid(self, request, response):
        if response.status in {403, 500, 302}:
            self.logger.warning(f'status code:{response.status}, {request.url}')
            return True
        return False

    def parse_detail(self, response):
        if '页面不存在' in response.xpath('//title/text()').get(''):
            self.logger.warning(f'页面不存在: {response.url}')
            return
        d = {field: get_value(response, label) for label, field in FIELD_MAP.items()}
        d['ghs_icons'] = get_ghs_icons(response)
        d['url'] = response.url
        yield IchembioData(**d)
```

- [ ] **Step 2: 跑测试**

Run: `uv run pytest tests/test_ichembio_spider.py -v`
Expected: 3 passed

- [ ] **Step 3: Commit（需用户确认）**

```bash
git add product_spider/spiders/ichembio_spider.py tests/test_ichembio_spider.py tests/fixtures/ichembio_detail_67-56-1.html
git commit -m "feat: add IchembioSpider parse_detail"
```

---

### Task 4: 三种入口模式与列表解析

**Files:**
- Modify: `product_spider/spiders/ichembio_spider.py`

- [ ] **Step 1: 在 `IchembioSpider` 中追加（`is_proxy_invalid` 之后）**

```python
    def __init__(self, cas_file: str = None, **kwargs):
        self.cas_file = cas_file
        super().__init__(**kwargs)

    @staticmethod
    def _read_cas_file(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                cas = line.strip()
                if cas and not cas.startswith('#'):
                    yield cas

    def _start_requests(self):
        if self.cas_file:
            for cas in self._read_cas_file(self.cas_file):
                yield Request(f'{self.base_url}/cas/{cas}', callback=self.parse_detail)
            return
        for i in range(100):
            for j in range(10):
                suffix = f'{i:02d}-{j}'
                yield Request(
                    f'{self.base_url}/search?query={suffix}&page_size=100',
                    meta={'suffix': suffix, 'first_page': True},
                )

    def keyword_search(self, keyword: str, search_params: dict = None):
        yield Request(
            f'{self.base_url}/search?query={quote(keyword)}&page_size=100',
            callback=self.parse,
            meta={'keyword': keyword, 'search_params': search_params, 'task_id': self.task_id},
        )

    def parse(self, response):
        suffix = response.meta.get('suffix')
        # 枚举模式第一页：结果达到单查询上限（约500条）时告警，可能漏采
        if suffix and response.meta.get('first_page'):
            total = response.xpath('//span[contains(@class,"total-num")]/text()').get('')
            if total.isdigit() and int(total) >= 500:
                self.logger.warning(f'后缀 {suffix} 结果达上限 {total} 条，可能漏采')

        seen = set()
        for href in response.xpath(
                '//div[contains(@class,"search-list-item")]//a[contains(@href,"/cas/")]/@href'
        ).getall():
            path = href.split('?')[0]  # 去掉 log_rc 等追踪参数，保证跨后缀 dupefilter 去重
            if path in seen:
                continue
            seen.add(path)
            # 搜索有模糊兜底，枚举模式只保留 CAS 以 -{suffix} 结尾的条目
            if suffix and not path.rsplit('/', 1)[-1].endswith(f'-{suffix}'):
                continue
            yield Request(urljoin(response.url, path), callback=self.parse_detail)

        next_page = response.xpath('//a[@class="page-link"][@rel="next"]/@href').get()
        if next_page:
            # 翻页请求不带 first_page 标志
            meta = {k: v for k, v in response.meta.items() if k != 'first_page'}
            yield Request(urljoin(response.url, next_page), callback=self.parse, meta=meta)
```

注意：`__init__` 必须放在类中（`custom_settings` 之后即可），Python 允许多处定义方法顺序自由，但同一类只保留一个 `__init__`。

- [ ] **Step 2: 回归测试**

Run: `uv run pytest tests/test_ichembio_spider.py -v`
Expected: 3 passed（本次改动不影响 parse_detail）

- [ ] **Step 3: Commit（需用户确认）**

```bash
git add product_spider/spiders/ichembio_spider.py
git commit -m "feat: ichembio spider three modes (enumerate/cas_file/keyword_search)"
```

---

### Task 5: Redis Pipeline 扩展

**Files:**
- Modify: `product_spider/pipelines/redis_pipeline.py:8,55-67,81`

- [ ] **Step 1: 改三处**

import（第 8 行附近）：

```python
from product_spider.items import ProductPackage, RawData
from product_spider.items.ichembio_items import IchembioData
```

类型判断（原 `process_item` 第 55-67 行）改为：

```python
        if not isinstance(item, (ProductPackage, RawData, IchembioData)):
            return item
```

key 选择处改为：

```python
            if isinstance(item, RawData):
                key = f"{self.KEY_PREFIX}:{task_id}:results:product"
            elif isinstance(item, ProductPackage):
                key = f"{self.KEY_PREFIX}:{task_id}:results:package"
            elif isinstance(item, IchembioData):
                key = f"{self.KEY_PREFIX}:{task_id}:results:ichembio"
```

日志行（第 81 行）改为以 cas 兜底：

```python
            spider.logger.info(f"Stored item to Redis: task_id={task_id}, item={item.get('cat_no') or item.get('cas', 'N/A')}")
```

- [ ] **Step 2: 验证导入与现有测试**

Run: `uv run python -c "from product_spider.pipelines.redis_pipeline import KeywordSearchRedisPipeline; print('ok')"` 及 `uv run pytest tests/ -m "not slow and not integration" -x -q`
Expected: ok；现有测试不因此次改动失败

- [ ] **Step 3: Commit（需用户确认）**

```bash
git add product_spider/pipelines/redis_pipeline.py
git commit -m "feat: KeywordSearchRedisPipeline supports IchembioData"
```

---

### Task 6: 集成冒烟验证（手动，需真实环境）

**前置：** `test.local.env` 已配置 Redis/数据库/代理池。

- [ ] **Step 1: 文件模式**

```bash
printf "67-56-1\n64-17-5\n# comment\n\n000-00-0\n" > data/test_cas.txt
uv run --env-file ./test.local.env scrapy crawl ichembio -a cas_file=./data/test_cas.txt
```

Expected：甲醇、乙醇入库（`ichembio_data` 表）；`000-00-0` 日志出现"页面不存在"且无 item；无 traceback。

- [ ] **Step 2: API 搜索模式**

```bash
uv run --env-file ./test.local.env scrapy crawl ichembio \
  -a cmd_keyword_search=true -a keyword=methanol -a task_id=ichembio-smoke-1
redis-cli -h 192.168.4.246 -p 6380 -n 2 zrange 'CMD_KEYWORD_SEARCH:ichembio-smoke-1:results:ichembio' 0 -1
```

Expected：Redis 中有 IchembioData JSON；`CMD_KEYWORD_SEARCH:ichembio-smoke-1:status` 最终为 `finished`。

- [ ] **Step 3: 枚举模式抽查（跑一个后缀即中断）**

```bash
uv run --env-file ./test.local.env scrapy crawl ichembio -s CLOSESPIDER_ITEMCOUNT=5
```

Expected：日志显示请求 `query=00-0`，产出 item 且 CAS 均以 `-00-0` 结尾。

- [ ] **Step 4: Commit（需用户确认）**

```bash
git add docs/superpowers/
git commit -m "docs: ichembio spider design and plan"
```
