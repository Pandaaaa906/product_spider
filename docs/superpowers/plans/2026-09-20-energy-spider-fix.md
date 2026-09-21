# Energy Spider 修复实施计划（官网改版适配）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `EnergySpiderSpider`，适配 energy-chemical.com 改版（雷池 WAF + Vue/JSON API 化 + 分类树加深），恢复全量采集。

**Architecture:** 单文件改动（`energy_spider.py`）。移动端 Safari UA 绕过 WAF；`have_children.htm` 递归分类树到叶子；旧 tempList 正则取第 1 页；新接口 `searchByQueryCriteria.htm`（base64 post_obj + csrfToken）翻页；`searchProductList.htm` 按 CAS 取详情（不变）。

**Tech Stack:** Scrapy（纯 HTTP，无 Playwright）。

**Spec:** `docs/superpowers/specs/2026-09-20-energy-spider-fix-design.md`

**项目规则：所有 git commit 由用户执行，任何步骤不得运行 `git commit`（CLAUDE.md：NEVER Auto-Commit）。改动留在工作区即可。**

---

## 已验证的站点事实（实现依据，勿再猜测）

- 桌面 UA 一律 403（雷池 WAF JS 挑战）；iPhone Safari UA 下 `requests`(urllib3) 200，但 Scrapy(Twisted)/curl 仍 403——WAF 同时校验 UA 白名单与 TLS 指纹。故 spider 级 `DOWNLOAD_HANDLERS` 覆盖为 `product_spider.utils.requests_handler.RequestsDownloadHandler`（基于 requests 的下载器，2026-09-20 实测冒烟通过）。
- 不使用项目代理池（约 75% SSL 失败、有代理返回伪造页面）；单 IP 并发 2 + 延迟 1s 实测可跑通，高频会被软封（468 维护页）。
- 列表页内嵌 `tempList` 是 JS 对象字面量（双引号 key、字符串内含 `\'` 转义），解析前需 `.replace("\\'", "'")`，不能用旧的 `.replace("'", '"')` hack。
- `POST /front/have_children.htm`（formdata `id`）响应形如 `{"list":[{"id":"79","text":"有机化学","children":[{"id":98,...}]}]}`；`list[0]` 是被查询节点本身，无 `children` 字段即叶子。
- `GET /front/search_goodsbyclass.htm?labelId=<leaf>`：HTML 内嵌 `let tempList = JSON.parse(JSON.stringify([...]))`（第 1 页）和 `let listToken = '...'`，并通过 Set-Cookie 种下 `csrfToken`（首页不下发）。
- `POST /front/searchByQueryCriteria.htm`：form 参数 `post_obj` + `csrfToken`（值取自同名 cookie）。`post_obj` = base64(utf8(json))，json 为 `{"searchString": "<json字符串>", "totalPage": "", "currentPage": "2", "groupValue": "试剂产品"}`，其中 searchString 序列化自 searchMap（`cas`/`keywords`/`brandBm`/`spec`/`classMap`/`bpbSourcenm`/`deliveryDate`/`labelId`/`pattern`/`elementId`/`smiles`/`searchStruType`/`similarValue`/`plcas`/`ComboFlag`，翻页时 `cas=''`）。`totalPage` 传任意值均可。响应 `{"listToken": "...", "resultList": [{"groupValue":"试剂产品","list2":[...]}]}`，list2 为空即翻页结束。
- `POST /front/searchProductList.htm`：form 参数 `searchString`（searchMap 带具体 cas）/`currentPage`/`groupValue=试剂产品`/`listToken`，响应 `tokenFlag:true` + `resultList[0].list2[0].mstList[*].pkgList`。token 按页使用：第 1 页用页面内嵌 token，第 N 页用该页翻页响应的 token。
- 价格 HTML 实体 + `num_map` 映射未变（`ρ?😅ββ` → `59.00` 已实测）。
- 实测链路样例：labelId=103 第 2 页首条 CAS 931-51-1 → 货号 W420204、100ml、59.00。

---

### Task 1: custom_settings 加移动端 UA

**Files:**
- Modify: `product_spider/spiders/energy_spider.py:16-26`

- [ ] **Step 1: 修改 custom_settings，加 USER_AGENT**

```python
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'RETRY_ENABLED': True,
        'RETRY_HTTP_CODES': [403],
        'RETRY_TIMES': 10,
        'RETRY_BACKOFF_BASE': 2,
        'RETRY_BACKOFF_MAX': 60,
    }
```

- [ ] **Step 2: 语法检查**

Run: `uv run python -c "import ast; ast.parse(open('product_spider/spiders/energy_spider.py', encoding='utf-8').read())"`
Expected: 无输出（通过）

---

### Task 2: 分类递归（parse + walk_categories）

**Files:**
- Modify: `product_spider/spiders/energy_spider.py:42-52`（替换旧 parse，新增 walk_categories）

- [ ] **Step 1: 替换 parse，新增 walk_categories**

```python
    def parse(self, response, **kwargs):
        seen = set()
        for el in response.xpath("//*[contains(@onclick,'getChildrenOrDetail')]"):
            match = re.search(r"'(\d+)'", el.xpath('./@onclick').get() or '')
            if not match or match.group(1) in seen:
                continue
            seen.add(match.group(1))
            parent = el.xpath('./@title').get() or el.xpath('normalize-space(.)').get()
            yield FormRequest('https://www.energy-chemical.com/front/have_children.htm',
                              formdata={'id': match.group(1)}, method='POST',
                              callback=self.walk_categories,
                              meta={'parent': parent})

    def walk_categories(self, response):
        parent = response.meta.get('parent')
        try:
            j = json.loads(response.text)
            if isinstance(j, str):  # 响应可能是双重编码的 JSON 字符串
                j = json.loads(j)
            nodes = j.get('list', [])
        except Exception as e:
            self.logger.warning(f"Parse category tree error, url:{response.url} err:{e}")
            return
        if not nodes:
            return
        node = nodes[0]  # 实测 list[0] 即被查询节点本身
        children = node.get('children')
        if not children:
            # 叶子节点 → 产品列表页
            node_id = str(node.get('id'))
            yield Request(f'https://www.energy-chemical.com/front/search_goodsbyclass.htm?labelId={node_id}',
                          callback=self.parse_list,
                          meta={'parent': parent, 'label_id': node_id})
            return
        for child in children:
            crumb = f'{parent}>{child.get("text")}' if parent else child.get('text')
            yield FormRequest('https://www.energy-chemical.com/front/have_children.htm',
                              formdata={'id': str(child.get('id'))}, method='POST',
                              callback=self.walk_categories,
                              meta={'parent': crumb})
```

注意：`Request` 已在文件头部 import（`from scrapy import Request, FormRequest`），无需新增 import。

- [ ] **Step 2: 语法检查**

Run: `uv run python -c "import ast; ast.parse(open('product_spider/spiders/energy_spider.py', encoding='utf-8').read())"`
Expected: 无输出（通过）

---

### Task 3: parse_list 提取 csrfToken + 新增 parse_page 翻页

**Files:**
- Modify: `product_spider/spiders/energy_spider.py`（parse_list 尾部追加翻页请求；新增 `_page_request` 和 `parse_page`；文件头加 `import base64`）

- [ ] **Step 1: 文件头加 import**

```python
import base64
import html
import json
import re
```

- [ ] **Step 2: parse_list 末尾（page-1 item 循环之后）追加翻页起点**

在现有 parse_list 的 `for item in product_list:` 循环之后追加：

```python
        csrf = None
        for h in response.headers.getlist('Set-Cookie'):
            m = re.search(rb'csrfToken=([^;]+)', h)
            if m:
                csrf = m.group(1).decode()
                break
        if not csrf:
            self.logger.warning(f"No csrfToken cookie found, url:{response.url}")
            return
        yield self._page_request(parent, label_id, csrf, 2)
```

- [ ] **Step 3: 新增 _page_request 和 parse_page 方法**

```python
    def _page_request(self, parent, label_id, csrf, page):
        search_map = {
            'cas': '', 'keywords': '', 'brandBm': {}, 'spec': {}, 'classMap': {},
            'bpbSourcenm': '', 'deliveryDate': '', 'labelId': label_id,
            'pattern': '大图模式', 'elementId': '', 'smiles': '', 'searchStruType': '',
            'similarValue': '', 'plcas': '', 'ComboFlag': '',
        }
        post_obj = base64.b64encode(json.dumps({
            'searchString': json.dumps(search_map, ensure_ascii=False),
            'totalPage': '',
            'currentPage': str(page),
            'groupValue': '试剂产品',  # 与旧爬虫行为一致，只取第一个 group（见 spec YAGNI）
        }, ensure_ascii=False).encode('utf-8')).decode()
        return FormRequest('https://www.energy-chemical.com/front/searchByQueryCriteria.htm',
                           formdata={'post_obj': post_obj, 'csrfToken': csrf},
                           method='POST', callback=self.parse_page,
                           meta={'parent': parent, 'label_id': label_id, 'csrf': csrf, 'page': page})

    def parse_page(self, response):
        parent = response.meta.get('parent')
        label_id = response.meta.get('label_id')
        csrf = response.meta.get('csrf')
        page = response.meta.get('page')
        try:
            j_obj = json.loads(response.text)
        except Exception as e:
            self.logger.warning(f"Parse page json error, url:{response.url} err:{e}")
            return
        result_list = j_obj.get('resultList') or []
        product_list = result_list[0].get('list2', []) if result_list else []
        if not product_list:
            return
        list_token = j_obj.get('listToken')
        for item in product_list:
            item['parent'] = parent
            item['prd_url'] = f'https://www.energy-chemical.com/front/search_goodsbyclass.htm?labelId={label_id}'
            searchString = {
                'cas': item['cas'],
                'keywords': "",
                'brandBm': {},
                'spec': {},
                'classMap': {},
                'bpbSourcenm': "",
                'deliveryDate': "",
                'labelId': label_id,
                'pattern': '大图模式',
            }
            form = {
                'searchString': json.dumps(searchString, ensure_ascii=False),
                'currentPage': str(page),
                'groupValue': '试剂产品',
                'listToken': list_token,
            }
            yield FormRequest('https://www.energy-chemical.com/front/searchProductList.htm', callback=self.parse_detail,
                              method='POST', meta={'parent': parent, 'item': item}, formdata=form)
        yield self._page_request(parent, label_id, csrf, page + 1)
```

- [ ] **Step 4: 语法检查**

Run: `uv run python -c "import ast; ast.parse(open('product_spider/spiders/energy_spider.py', encoding='utf-8').read())"`
Expected: 无输出（通过）

---

### Task 4: parse_detail 加 tokenFlag 守卫

**Files:**
- Modify: `product_spider/spiders/energy_spider.py`（parse_detail 开头）

- [ ] **Step 1: json 解析后加 tokenFlag 检查**

在 `parse_detail` 中 `product_obj: dict = json.loads(f'[{response.text}]')` 之后、`products = product_obj[0].get('resultList')` 之前插入：

```python
        if not product_obj[0].get('tokenFlag', True):
            self.logger.warning(f"Invalid listToken (tokenFlag false), url:{response.url}")
            return
```

- [ ] **Step 2: 语法检查**

Run: `uv run python -c "import ast; ast.parse(open('product_spider/spiders/energy_spider.py', encoding='utf-8').read())"`
Expected: 无输出（通过）

---

### Task 5: 实跑冒烟验证

**Files:**
- Modify: `product_spider/spiders/energy_spider.py`（临时限制，验证后还原）

- [ ] **Step 1: 临时限制分类数量**

在 `parse` 的循环处临时切片（便于快速验证）：

```python
        for el in response.xpath("//*[contains(@onclick,'getChildrenOrDetail')]")[:1]:
```

- [ ] **Step 2: 小规模实跑**

Run: `uv run scrapy crawl energychemical -s LOG_LEVEL=INFO -s CLOSESPIDER_ITEMCOUNT=50`
Expected:
- 日志出现 `have_children.htm` 递归请求并到达叶子分类；
- 出现 `searchByQueryCriteria.htm` 翻页请求（currentPage=2,3,...）；
- `searchProductList.htm` 返回 `tokenFlag:true`，无大量 "Invalid listToken" warning；
- walk_categories 回调无 `AttributeError`（若有，说明 have_children 响应编码形态与预期不符）；
- 产出 item（RawData/SupplierProduct/ProductPackage）。

- [ ] **Step 3: 抽查数据正确性**

从输出/日志抽查至少 1 个产品：货号（W 开头）、规格（如 100ml）、价格为数值（经 num_map 解码，非 HTML 实体残留）、库存为数值或 None。

- [ ] **Step 4: 去掉临时切片，还原 parse 为全量**

把 `[:1]` 移除，恢复 `response.xpath("//*[contains(@onclick,'getChildrenOrDetail')]")`。

- [ ] **Step 5: 汇总改动，请用户确认后由用户提交 git**

列出修改文件与要点，等待用户明确说 "commit" 类指令。**不得自行 git commit。**
