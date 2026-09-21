# Energy Spider 修复设计（官网改版适配）

日期：2026-09-20
分支：ichembio
目标文件：`product_spider/spiders/energy_spider.py`（单文件改动）

## 背景

energy-chemical.com 改版，旧爬虫 `EnergySpiderSpider` 失效，原因有二：

1. **雷池（SafeLine）WAF**：全站页面对桌面浏览器 UA 一律返回 403 JS 指纹挑战页（`waf-ce.chaitin.cn/release/js/fp.js`），普通 Scrapy 默认 UA 无法通过。
2. **站点结构改版**：前端改为 Vue + axios，产品数据全部通过 JSON API 异步加载；分类树层级加深，顶层分类不再是叶子节点。

## 实测结论（2026-09-20 对生产站验证）

- **移动端 Safari UA + requests(urllib3) TLS 指纹可绕过 WAF**：桌面 UA 全部 403；iPhone Safari UA 下，Python `requests` 200，但 Scrapy 默认下载器（Twisted）和 curl 仍 403——WAF 同时校验 UA 白名单和 TLS 指纹（JA3）。因此 Scrapy 需通过自定义 download handler（`product_spider/utils/requests_handler.py` 的 `RequestsDownloadHandler`，spider 级 `DOWNLOAD_HANDLERS` 覆盖）把下载转发给 requests 库。这是方案成立的关键前提。
- **不使用项目代理池**：代理池约 75% SSL 失败，且有代理返回伪造页面（D-link 路由管理页），会造成静默空数据；单 IP 低速（并发 2 + 延迟 1s）实测可跑通。
- 官网前端自身通过以下 JSON 接口获取产品信息，爬虫与前端行为同构：

| 用途 | 接口 | 说明 |
|------|------|------|
| 分类树 | `POST /front/have_children.htm` | 参数 `id`，返回 JSON 子分类列表；无 `children` 字段即叶子 |
| 列表页第 1 页 | `GET /front/search_goodsbyclass.htm?labelId=<leaf>` | HTML 内嵌 `tempList` JSON + `listToken`；同时种下 `csrfToken` cookie |
| 翻页 | `POST /front/searchByQueryCriteria.htm` | form 参数 `post_obj`=base64(JSON) + `csrfToken`（值取自同名 cookie，form 和 cookie 都带，与官网前端行为一致）；响应含 resultList + 新 listToken |
| 详情/价格库存 | `POST /front/searchProductList.htm` | 按 CAS 查询，结构未变 |

- 价格字体混淆映射 `num_map` 未变（已用真实数据验证：`ρ?😅ββ` → `59.00`）。
- `searchByQueryCriteria.htm` 的 `totalPage` 参数传任意值均可，翻页终止条件以返回空列表为准。
- `csrfToken` cookie 由 `search_goodsbyclass.htm` 页面 GET 下发（首页不下发），scrapy cookie jar 自动携带。

## 设计

### 整体流程

```
start_requests: GET 首页 (mobile UA)
  → parse: 提取顶层分类 (onclick="getChildrenOrDetail('<id>')")
  → 递归 POST have_children.htm 至叶子，层级路径拼 parent（如 "有机化学>有机金属试剂>格氏试剂"）
  → GET search_goodsbyclass.htm?labelId=<leaf>
      · 旧 tempList 正则解析第 1 页 + listToken（复用现有代码）
      · csrfToken cookie 自动入 jar
  → POST searchByQueryCriteria.htm 翻页 (currentPage=2,3,... 直到 resultList 为空)
  → 每个 item: POST searchProductList.htm (按 CAS, 携带当页 listToken)
  → parse_detail: mstList/pkgList 解析（现有逻辑不变）
```

### 改动点（均在 energy_spider.py）

1. **custom_settings**
   - `USER_AGENT` 设为 iPhone Safari UA（过 WAF 关键）：
     `Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1`
   - `DOWNLOAD_HANDLERS` 覆盖 http/https 为 `product_spider.utils.requests_handler.RequestsDownloadHandler`（过 TLS 指纹检测关键；cookie 由 Scrapy CookiesMiddleware 在头部层面维护，handler 只透传）。
   - 低速配置：`CONCURRENT_REQUESTS_PER_DOMAIN=2`、`DOWNLOAD_DELAY=1`；`RETRY_HTTP_CODES=[403, 468]`、少重试 + 长 backoff（单 IP 高频会被软封为 468 维护页）。

2. **parse（首页解析）**
   - XPath 放宽为 `//*[contains(@onclick,'getChildrenOrDetail')]`（旧的 `text-wrapper_15` class 可能已变）。
   - 不再直接请求 `search_goodsbyclass.htm`，改为先调 `have_children.htm` 递归。

3. **新增 `walk_categories`（分类递归）**
   - `POST have_children.htm`，formdata `{'id': <id>}`。
   - 响应实测形态：JSON 字符串里包 JSON（`{"list":[{"id":"79","text":"有机化学","children":[{"id":98,"text":"有机金属试剂"},...]}]}`），需两次 `json.loads`（外层 dict、内层 list 字符串）；叶子节点无 `children` 字段。
   - 节点含 `children` → 递归，parent 用 `>` 拼接层级路径；无 `children` → 叶子，发 `search_goodsbyclass.htm` 请求。

4. **parse_list（列表页，基本沿用旧代码）**
   - 沿用 tempList 正则 + listToken 提取解析第 1 页。
   - 对每个 item 发 `searchProductList.htm`（同旧逻辑，`currentPage='1'`）。
   - **新增**：从 `currentPage=2` 起循环发 `searchByQueryCriteria.htm`：
     - `searchMap` 定义为与旧 `searchString` 相同的字典（`cas`/`keywords`/`brandBm`/`spec`/`classMap`/`bpbSourcenm`/`deliveryDate`/`labelId`/`pattern` 等字段），翻页时 `cas=''`、其余默认、`labelId=<leaf>`（实测通过的形态）。
     - `post_obj` = base64(utf8(JSON({searchString: json.dumps(searchMap), totalPage: '', currentPage: str(n), groupValue: '试剂产品'})))
     - `csrfToken` 作为 form 参数提交：在 parse_list 中从 `search_goodsbyclass.htm` 响应的 Set-Cookie 头提取 `csrfToken` 值，存入 meta 传给翻页请求（cookie 本身由 jar 自动携带，两者都带——实测通过且与官网前端一致）。
     - 响应 `resultList[0].list2` 为空 → 停止翻页。
     - **token 按页使用**：第 1 页 item 用页面内嵌 listToken，第 N 页 item 用该页 `searchByQueryCriteria` 响应返回的新 listToken（经 meta 传递）。

5. **parse_detail（不变）**
   - `searchProductList.htm` 响应结构未变，现有解析逻辑、`num_map`、`parse_price`、`parse_stock_num` 全部保留。
   - `tokenFlag: false` 时记 warning 并跳过。

### 数据处理（不变）

- item 字段映射沿用：`bpsEnm→en_name`、`bpmNm→chs_name`、`bpsMf→mf`、`bpsMw→mw`、`bpsMDL→mdl`、`casImg→img_url`、`storageDesc→info2`、`bpacPurity→purity`、`bpmOrgcd→cat_no`、`specMap.规格→package`、`specMap.货期→delivery_time`、`qtyMap→stock_num`。
- 输出 RawData / SupplierProduct / ProductPackage / RawSupplierQuotation，经现有 translate 函数转换。

### 错误处理

- tempList/listToken 正则未命中 → warning 并 return（沿用旧逻辑）。
- `have_children.htm` / `searchByQueryCriteria.htm` 响应 JSON 解析失败 → warning 并跳过该分支/分页。
- `tokenFlag: false`（listToken 失效）→ warning 并跳过该 item。
- WAF 403 → 现有 RETRY 配置兜底。

## 范围外（YAGNI）

- 不使用 Playwright（移动端 UA 已验证可用；WAF 收紧后再考虑）。
- 不处理非"试剂产品"的 groupValue tab（旧爬虫同样只处理第一个 group，行为一致）。
- 不做 keyword_search（本爬虫未实现该功能，不在本次范围）。
- 不解析 `gotoPageFormHTML` 获取总页数（以空列表为终止条件更简单）。

## 风险

- **WAF UA 白名单收紧**：移动端 UA 未来可能被挑战。应对：届时退到 Playwright 方案（项目已有 StealthScrapyPlaywrightDownloadHandler）。
- **listToken 轮换策略变化**：目前每页响应下发新 token，按页使用；若改为一次性 token，需调整。

## 验证方式

`uv run scrapy crawl energychemical` 小范围运行（临时在 `parse` 里对顶层分类 `[:1]` 切片限制数量，验证后去掉），确认：
- 分类递归能到达叶子并产生列表请求；
- 翻页能取到第 2 页以后数据；
- parse_detail 能解出货号、规格、价格（数值型）、库存。
