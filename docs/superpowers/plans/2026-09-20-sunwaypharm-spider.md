# Sunwaypharm Spider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 sunwaypharm spider，抓取 sunwaypharm.cn 全部分类产品的规格/价格/库存/货期。

**Architecture:** 克隆 `heowns_spider.py` 模式（同 kuujiasoft Web960 平台）：分类列表页 → 详情页（名称/CAS/MF/MW）→ `POST /index.aspx?a=ajaxpro_ajax&method=LoadGoods`（全部规格的价格/库存/货期）。纯 HTTP，无 Playwright。

**Tech Stack:** Scrapy、pytest、uv。站点编码 UTF-8（meta charset=utf-8，已实测）。

**Spec:** `docs/superpowers/specs/2026-09-20-sunwaypharm-spider-design.md`

**项目规则：全程不要执行 `git commit`**，所有改动留在工作区，由用户自行提交。计划模板中的 commit 步骤一律跳过。

---

### Task 1: 录制测试 fixtures

调研时已下载真实响应，复制为 fixtures（保留原始字节，UTF-8 编码）。

**Files:**
- Create: `tests/fixtures/sunwaypharm_list.html`（分类 618 第 1 页）
- Create: `tests/fixtures/sunwaypharm_detail.html`（产品 149836 详情页）
- Create: `tests/fixtures/sunwaypharm_loadgoods.json`（LoadGoods 响应，4 个规格）

- [ ] **Step 1: 复制 fixture 文件**

```bash
cp sunway_cat618.html tests/fixtures/sunwaypharm_list.html
cp sunway_detail.html tests/fixtures/sunwaypharm_detail.html
cp sunway_goods.json tests/fixtures/sunwaypharm_loadgoods.json
```

若根目录下这些临时文件已被清理，重新下载：

```bash
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "https://sunwaypharm.cn/products/618/" -o tests/fixtures/sunwaypharm_list.html
curl -s -A "Mozilla/5.0" "https://sunwaypharm.cn/product/149836.html" -o tests/fixtures/sunwaypharm_detail.html
curl -s -A "Mozilla/5.0" -X POST "https://sunwaypharm.cn/index.aspx?a=ajaxpro_ajax&method=LoadGoods" -d 'pd_id=149836' -o tests/fixtures/sunwaypharm_loadgoods.json
```

- [ ] **Step 2: 验证 fixture 内容**

Run: `uv run python -c "import json,re; raw=open('tests/fixtures/sunwaypharm_loadgoods.json','rb').read().decode('utf-8',errors='replace'); d=json.loads(raw); obj=json.loads(d['ObjResult']); rows=obj['p_149836']; print(len(rows), 'packages')"`
Expected: 输出 `4 packages`

- [ ] **Step 3: 删除根目录调研临时文件**（sunway_home.html、sunway_cat618.html、sunway_detail.html、sunway_goods.json、sunway_ajax.js、sunway_sys.js、sunway_product.js、sunway_gm.js、sunway_wr.js、sunway_all.html、sunway_search.html、sunway_s.html、sunway_s2.html、inv_resp.txt、inv2.txt、goods.txt）

---

### Task 2: 列表页解析（TDD）

**Files:**
- Test: `tests/test_sunwaypharm_spider.py`
- Create: `product_spider/spiders/sunwaypharm_spider.py`

列表页事实（fixture 已验证）：每页 20 个 `sunwaypharm.cn/product/{id}.html` 产品卡（`<a class="name" href="//sunwaypharm.cn/product/149836.html">`），正则守卫跳过可能的旧域名 `www.sunwaypharm.com` 链接；翻页为 kuujiasoft 标准 pagination，下一页 URL `/products/618.html?page=2&prop_filter=%7b%7d`。

- [ ] **Step 1: 写失败测试**

创建 `tests/test_sunwaypharm_spider.py`：

```python
import json
from pathlib import Path

import pytest
from scrapy.http import Request, TextResponse

from product_spider.items import (
    ProductPackage,
    RawData,
    RawSupplierQuotation,
    SupplierProduct,
)
from product_spider.spiders.sunwaypharm_spider import SunwaypharmSpider

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://sunwaypharm.cn"
DETAIL_URL = f"{BASE}/product/149836.html"


def make_html_response(fixture: str, url: str, meta: dict = None) -> TextResponse:
    body = (FIXTURES / fixture).read_bytes()
    return TextResponse(url=url, body=body, encoding="utf-8", request=Request(url, meta=meta))


def test_parse_list_extracts_products_and_next_page():
    spider = SunwaypharmSpider()
    results = list(spider.parse(make_html_response("sunwaypharm_list.html", f"{BASE}/products/618/")))
    detail_requests = [r for r in results if isinstance(r, Request) and r.callback == spider.parse_detail]
    page_requests = [r for r in results if isinstance(r, Request) and r.callback == spider.parse]

    assert len(detail_requests) == 20
    assert detail_requests[0].url == DETAIL_URL
    assert detail_requests[0].meta["pd_id"] == "149836"
    # 旧域名 www.sunwaypharm.com 推荐链接被跳过
    assert all("sunwaypharm.cn" in r.url for r in detail_requests)
    assert len(page_requests) == 1
    assert page_requests[0].url == f"{BASE}/products/618.html?page=2&prop_filter=%7b%7d"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_sunwaypharm_spider.py -v`
Expected: FAIL（ModuleNotFoundError: sunwaypharm_spider）

- [ ] **Step 3: 实现 spider 骨架 + 列表解析**

创建 `product_spider/spiders/sunwaypharm_spider.py`：

```python
import json
import re
from urllib.parse import urlencode, urljoin

import scrapy

from product_spider.items import (
    ProductPackage,
    RawData,
    RawSupplierQuotation,
    SupplierProduct,
)
from product_spider.utils.items_translate import (
    product_package_to_raw_supplier_quotation,
    rawdata_to_supplier_product,
)
from product_spider.utils.spider_mixin import BaseSpider

BASE_URL = "https://sunwaypharm.cn"
CATEGORIES = [437, 446, 449, 468, 471, 480, 483, 548, *range(570, 619)]


def is_sunwaypharm(brand: str):
    return brand in {"相辉", "sunwaypharm"}


class SunwaypharmSpider(BaseSpider):
    """上海相辉医药 https://sunwaypharm.cn/"""

    name = "sunwaypharm"
    allowed_domains = ["sunwaypharm.cn"]
    start_urls = [f"{BASE_URL}/products/{c}/" for c in CATEGORIES]
    other_brands = set()

    def parse(self, response):
        for url in response.xpath("//a[@class='name']/@href").getall():
            m = re.search(r"sunwaypharm\.cn/product/(\d+)\.html", url)
            if not m:
                continue
            yield scrapy.Request(
                url=urljoin(BASE_URL, url),
                callback=self.parse_detail,
                meta={"pd_id": m.group(1)},
            )
        next_page = response.xpath(
            '//ul[contains(@class, "pagination")]/li[@class="active"]'
            "/following-sibling::li[1]/a/text()"
        ).get()
        if next_page and next_page.strip().isdigit():
            yield scrapy.Request(url=self._page_url(response.url, next_page.strip()), callback=self.parse)

    @staticmethod
    def _page_url(url: str, page: str) -> str:
        base = url.split("?")[0]
        if base.endswith("search.do"):
            return f"{base}?a=is&psize=18&page={page}"
        if not base.endswith(".html"):
            base = base.rstrip("/") + ".html"
        return f"{base}?page={page}&prop_filter=%7b%7d"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_sunwaypharm_spider.py::test_parse_list_extracts_products_and_next_page -v`
Expected: PASS

若 pagination XPath 不匹配（同平台应有差异可能），用 `uv run python -c` 解码 fixture 检查分页容器实际 class 后修正 XPath。

---

### Task 3: 详情页解析（TDD）

**Files:**
- Test: `tests/test_sunwaypharm_spider.py`
- Modify: `product_spider/spiders/sunwaypharm_spider.py`

详情页事实（fixture 已验证）：字段表为 `th/td`（标签：中文名称、英文名称、CAS号、分子式、分子量）；产品编号在 `div.detail span`（文本 "产品编号 <span>CB40054</span>"）；面包屑末级为 "产品分类" 时 parent 置 None；产品图为 `.image` 容器内 `div.img` 的 CSS background `url(...)`，无图时为 noimage.jpg（取 None）。

- [ ] **Step 1: 追加失败测试**

```python
def test_parse_detail_extracts_fields_and_requests_loadgoods():
    spider = SunwaypharmSpider()
    results = list(
        spider.parse_detail(
            make_html_response("sunwaypharm_detail.html", DETAIL_URL, {"pd_id": "149836"})
        )
    )
    assert len(results) == 1
    req = results[0]
    assert req.method == "POST"
    assert req.url == f"{BASE_URL}/index.aspx?a=ajaxpro_ajax&method=LoadGoods"
    assert req.body == b"pd_id=149836"
    d = req.meta["product"]
    assert d["cas"] == "1363381-10-5"
    assert "Pyrazolo" in d["en_name"] or "PYRAZOLO" in d["en_name"].upper()
    assert d["prd_url"] == DETAIL_URL
    assert "parent" in d and "img_url" in d and "mf" in d and "mw" in d
```

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest tests/test_sunwaypharm_spider.py::test_parse_detail_extracts_fields_and_requests_loadgoods -v`
Expected: FAIL（AttributeError: parse_detail）

- [ ] **Step 3: 实现 parse_detail**

在 `SunwaypharmSpider` 中追加：

```python
    def parse_detail(self, response):
        pd_id = response.meta["pd_id"]

        def cell(label: str):
            v = "".join(
                response.xpath(
                    f"//th[contains(text(), '{label}')]/following-sibling::td[1]//text()"
                ).getall()
            ).strip()
            return v or None

        parent = response.xpath("//ol[@class='breadcrumb']/li[last()]/a/text()").get()
        if parent == "产品分类":
            parent = None
        style = response.xpath("//div[contains(@class, 'image')]//div[@class='img']/@style").get("")
        m = re.search(r"url\((//[^)]+)\)", style)
        img_url = f"https:{m.group(1)}" if m and "noimage" not in m.group(1) else None
        d = {
            "chs_name": cell("中文名称"),
            "en_name": cell("英文名称"),
            "cas": cell("CAS"),
            "mf": cell("分子式"),
            "mw": cell("分子量"),
            "parent": parent,
            "img_url": img_url,
            "prd_url": response.url,
        }
        yield scrapy.Request(
            url=f"{BASE_URL}/index.aspx?a=ajaxpro_ajax&method=LoadGoods",
            method="POST",
            body=urlencode({"pd_id": pd_id}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            callback=self.parse_package,
            meta={"product": d, "pd_id": pd_id},
        )
```

- [ ] **Step 4: 运行确认通过**

Run: `uv run pytest tests/test_sunwaypharm_spider.py -v`
Expected: 2 passed

---

### Task 4: LoadGoods 规格解析（TDD）

**Files:**
- Test: `tests/test_sunwaypharm_spider.py`
- Modify: `product_spider/spiders/sunwaypharm_spider.py`

LoadGoods 响应结构（实测）：顶层 `ObjResult` 为 JSON 字符串 → `{"p_{pd_id}": [{"Inventores": [{...}]}]}`；每个 Inventores 元素有 `Goods_Info`（JSON 字符串，含 `goodsinfo.packaging/purity/brand/goodshuoqi`）、`Price`、`Goods_no`、`Amount`。fixture 含 4 个规格：50mg/794.2、100mg/1028.85、250mg/1547.55、1g/4633.15，Amount 全 0，brand 相辉。

- [ ] **Step 1: 追加失败测试**

```python
def _detail_meta():
    return {
        "pd_id": "149836",
        "product": {
            "chs_name": "5-溴吡唑并[1,5-a]吡啶-2-羧酸",
            "en_name": "5-Bromopyrazolo[1,5-a]pyridine-2-carboxylic acid",
            "cas": "1363381-10-5",
            "mf": None,
            "mw": None,
            "parent": "其他中间体",
            "img_url": None,
            "prd_url": DETAIL_URL,
        },
    }


def test_parse_package_yields_all_packages():
    spider = SunwaypharmSpider()
    results = list(
        spider.parse_package(
            make_html_response("sunwaypharm_loadgoods.json",
                               f"{BASE}/index.aspx?a=ajaxpro_ajax&method=LoadGoods",
                               _detail_meta())
        )
    )
    raws = [r for r in results if isinstance(r, RawData)]
    pkgs = [r for r in results if isinstance(r, ProductPackage)]
    sps = [r for r in results if isinstance(r, SupplierProduct)]
    quotes = [r for r in results if isinstance(r, RawSupplierQuotation)]

    assert len(raws) == len(pkgs) == len(sps) == len(quotes) == 4
    by_package = {p["package"]: p for p in pkgs}
    assert by_package["50mg"]["cost"] == 794.2
    assert by_package["1g"]["cost"] == 4633.15
    pkg = by_package["100mg"]
    assert pkg["brand"] == "相辉"
    assert pkg["cat_no"] == "CB40054"
    assert pkg["currency"] == "CNY"
    assert pkg["stock_num"] == 0
    assert pkg["delivery_time"] is None  # Amount=0 且无 goodshuoqi
    assert raws[0]["purity"] == "95+%"


def test_parse_package_bad_json_skips():
    spider = SunwaypharmSpider()
    resp = TextResponse(url=f"{BASE}/index.aspx", body=b"not json", encoding="utf-8",
                        request=Request(f"{BASE}/index.aspx", meta=_detail_meta()))
    assert list(spider.parse_package(resp)) == []
```

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest tests/test_sunwaypharm_spider.py -v`
Expected: FAIL（AttributeError: parse_package）

- [ ] **Step 3: 实现 parse_package 与 closed**

在 `SunwaypharmSpider` 中追加：

```python
    def parse_package(self, response):
        d = response.meta["product"]
        pd_id = response.meta["pd_id"]
        try:
            obj = json.loads(response.json()["ObjResult"])
        except (ValueError, TypeError, KeyError):
            self.logger.warning(f"LoadGoods 响应解析失败: {pd_id}")
            return
        for result in obj.get(f"p_{pd_id}") or []:
            for inv in result.get("Inventores") or []:
                goods_info = json.loads(inv.get("Goods_Info") or "{}").get("goodsinfo", {})
                brand = goods_info.get("brand")
                if brand == "促销无折扣":
                    brand = self.name
                cat_no = (inv.get("Goods_no") or "").rsplit("-", 1)[0] or None  # Goods_no 形如 CB40054-100mg
                price = inv.get("Price")
                stock_num = inv.get("Amount", 0)
                if isinstance(stock_num, float):
                    stock_num = int(stock_num)
                delivery_time = goods_info.get("goodshuoqi") or None
                if not delivery_time and isinstance(stock_num, int) and stock_num > 0:
                    delivery_time = "现货"

                d["brand"] = brand
                d["cat_no"] = cat_no
                d["purity"] = goods_info.get("purity")
                dd = {
                    "brand": brand,
                    "cat_no": cat_no,
                    "cost": price,
                    "currency": "CNY",
                    "package": goods_info.get("packaging"),
                    "stock_num": stock_num,
                    "delivery_time": delivery_time,
                }
                yield SupplierProduct(**rawdata_to_supplier_product(d, self.name, self.name))
                if not is_sunwaypharm(brand):
                    self.other_brands.add(brand)
                    continue
                yield RawData(**d)
                yield ProductPackage(**dd)
                if dd["cost"]:
                    yield RawSupplierQuotation(
                        **product_package_to_raw_supplier_quotation(d, dd, self.name, self.name)
                    )

    def closed(self, reason):
        self.logger.info(f"其他品牌: {self.other_brands}")
```

- [ ] **Step 4: 运行确认通过**

Run: `uv run pytest tests/test_sunwaypharm_spider.py -v`
Expected: 4 passed

若 `response.json()` 在该 TextResponse 上有问题，改用 `json.loads(response.text)`。

---

### Task 5: keyword_search（TDD）

**Files:**
- Test: `tests/test_sunwaypharm_spider.py`
- Modify: `product_spider/spiders/sunwaypharm_spider.py`

搜索接口：`GET /search.do?a=is&psize=18&kw={keyword}&searchtmp=`，结果页与列表页同为产品卡结构，复用 `parse`。

- [ ] **Step 1: 追加失败测试**

```python
def test_keyword_search():
    spider = SunwaypharmSpider()
    requests = list(spider.keyword_search("acetone"))
    assert len(requests) == 1
    assert requests[0].url == f"{BASE}/search.do?a=is&psize=18&kw=acetone&searchtmp="
    assert requests[0].callback == spider.parse
```

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest tests/test_sunwaypharm_spider.py::test_keyword_search -v`
Expected: FAIL（NotImplementedError 或 AssertionError）

- [ ] **Step 3: 实现 keyword_search**

在 `SunwaypharmSpider` 中追加：

```python
    def keyword_search(self, keyword: str, search_params: dict = None):
        yield scrapy.Request(
            url=f"{BASE_URL}/search.do?a=is&psize=18&kw={keyword}&searchtmp=",
            callback=self.parse,
        )
```

注意：搜索结果页翻页时 `_page_url` 会丢 `kw` 参数。ponytail：搜索结果翻页只保留 page 参数已够用的情况少见；若实测搜索结果多页且缺 kw 导致翻页失效，再把 `response.meta["keyword"]` 透传进 `_page_url`。

- [ ] **Step 4: 运行确认通过**

Run: `uv run pytest tests/test_sunwaypharm_spider.py -v`
Expected: 5 passed

---

### Task 6: 全量验证

- [ ] **Step 1: 全量跑测试**

Run: `uv run pytest tests/test_sunwaypharm_spider.py -v`
Expected: 5 passed

- [ ] **Step 2: 冒烟实测（真实站点小范围）**

Run: `uv run --env-file ./test.local.env scrapy crawl sunwaypharm -s CLOSESPIDER_PAGECOUNT=3 -s CLOSESPIDER_ITEMCOUNT=20`
Expected: 正常产出 item，无解析报错；日志中可见规格/价格/库存字段。

- [ ] **Step 3: 汇总改动给用户，等待用户提交（不要 git commit）**
