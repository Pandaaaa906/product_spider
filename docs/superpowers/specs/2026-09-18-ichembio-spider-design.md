# IchembioSpider 设计文档

日期：2026-09-18
状态：已确认

## 背景与目标

新增爬虫 `IchembioSpider`，采集 ichembio.com 的化学品数据，重点是详情页"安全信息"章节（GHS 图标、危险声明、预防措施、UN 编码、包装等级等）。

网站为 SSR（服务端渲染），列表页与详情页数据均在初始 HTML 中，**无需 Playwright**。

## 三种运行模式

单 spider 三模式，共用同一个 `parse_detail`：

| 模式 | 触发方式 | 入口逻辑 |
|---|---|---|
| 枚举模式（默认） | 无参数 | 枚举 CAS 后三位 `00-0` ~ `99-9` 共 1000 个后缀，逐个请求 `/search?query={suffix}&size=100`，翻页提取详情链接 |
| 文件模式 | `-a cas_file=path/to/cas.txt` | 读 txt（每行一个 CAS，跳过空行与 `#` 注释），直接请求 `/cas/{CAS}` 详情页（不经过搜索，请求量最小） |
| API 搜索模式 | `cmd_keyword_search=True&keyword=...&task_id=...` | 实现 `keyword_search`，请求 `/search?query={keyword}&size=100`，复用列表翻页解析 |

### 页面结构（已验证）

- 列表页：`https://www.ichembio.com/search?query=23-5&page_size=100&page=2`，每页条数参数为 `page_size`（10/20/50/100），单查询上限约 500 条；结果链接为 `/cas/{CAS}?log_rc=...`（须取 `?` 前路径以保证跨后缀去重）
- **搜索有模糊兜底**：无精确匹配时返回无关结果，枚举模式必须过滤掉 CAS 不以 `-{suffix}` 结尾的条目
- 详情页：`https://www.ichembio.com/cas/67-56-1`，安全信息、属性信息均为 SSR 直出
- 无效 CAS 详情页返回 200 + "页面不存在"提示页（title 含"页面不存在"），需识别跳过
- 列表页总数元素：`//span[contains(@class,"total-num")]/text()`；下一页：`//a[@class="page-link"][@rel="next"]/@href`

## Item：IchembioData

文件：`product_spider/items/ichembio_items.py`，继承 `scrapyautodb.OrderedItem`，`Meta.indexes = (('cas',), True)`。

详情页采用统一的 `content-item-label` / `content-item-value` 结构，共 38 个字段，全部采集：

| label（页面原文） | 字段名 | 章节 |
|---|---|---|
| 中文名称 | `zh_name` | 基本信息 |
| 英文名称 | `en_name` | 基本信息 |
| 中文同义词 | `synonyms_zh` | 基本信息 |
| 英文同义词 | `synonyms_en` | 基本信息 |
| IUPAC Name | `iupac_name` | 基本信息 |
| 分子式 | `mf` | 基本信息 |
| CAS No. | `cas` | 基本信息 |
| 分子量 | `mw` | 基本信息 |
| Smiles | `smiles` | 基本信息 |
| InChI key | `inchi_key` | 基本信息 |
| Reaxy-Rn | `reaxy_rn` | 基本信息 |
| MDL编号 | `mdl_number` | 基本信息 |
| PubChem编号 | `pubchem_id` | 基本信息 |
| 自燃温度 | `autoignition_temp` | 属性信息 |
| 形态 | `appearance` | 属性信息 |
| 折射率 | `refractive_index` | 属性信息 |
| 熔点 | `melting_point` | 属性信息 |
| 沸点 | `boiling_point` | 属性信息 |
| 溶解性 | `solubility` | 属性信息 |
| 密度 | `density` | 属性信息 |
| 闪点(°F) | `flash_point_f` | 属性信息 |
| 闪点(°C) | `flash_point_c` | 属性信息 |
| 旋光 | `optical_rotation` | 属性信息 |
| 敏感性 | `sensitivity` | 属性信息 |
| 储存温度 | `storage_temp` | 属性信息 |
| 运输条件 | `transport_condition` | 属性信息 |
| 描述及应用 | `description` | 属性信息 |
| 象形图 | `ghs_icons`（从 img src 提取 GHS 代码，JSON 列表，如 `["GHS02","GHS06"]`） | 安全信息 |
| 警示用语 | `signal_word` | 安全信息 |
| 危险声明 | `hazard_statements` | 安全信息 |
| 预防措施说明 | `precautionary_statements` | 安全信息 |
| 危险级别 | `danger_level` | 安全信息 |
| UN编码 | `un_number` | 安全信息 |
| 包装等级 | `package_grade` | 安全信息 |
| 危险分类 | `hazard_class` | 安全信息 |
| 储存分类代码 | `storage_class` | 安全信息 |
| WGK | `wgk` | 安全信息 |
| 个人防护装备 | `ppe` | 安全信息 |
| - | `url`（详情页 URL） | - |

解析约定：
- 全部走 XPath "label → 值" 模板（同 ChemSrcSpider 的 `tmpl` 手法）
- 页面空值标记 `-` 统一转为 None
- 字段缺失不丢弃 item，该字段置 None

## Spider：IchembioSpider

文件：`product_spider/spiders/ichembio_spider.py`，继承 `BaseSpider`。

```python
class IchembioSpider(BaseSpider):
    name = "ichembio"
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'PROXY_POOL_REFRESH_STATUS_CODES': [403, 503, 302],
        'RETRY_TIMES': 5,
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 1,
    }

    def __init__(self, cas_file: str = None, **kwargs): ...
```

- `_start_requests`：枚举模式 / 文件模式分支（`BaseSpider.start_requests` 已处理 keyword 模式分发）
- 参数优先级：若同时传入 `cas_file` 与 `cmd_keyword_search`，keyword 模式优先（`BaseSpider.start_requests` 行为），`cas_file` 被忽略
- 枚举模式容量保护：单查询上限约 500 条；某后缀翻页达到上限时在日志中 warning 提示可能漏采
- `parse`：列表页——提取详情链接 + 翻页
- `parse_detail`：详情页——yield `IchembioData`
- `keyword_search`：请求搜索页后复用 `parse`
- `is_proxy_invalid`：403/5xx/302 或响应过短判定代理失效（复用 ChemSrcSpider 手法）

## Pipeline 改动

`KeywordSearchRedisPipeline`（`product_spider/pipelines/redis_pipeline.py`）增加 `IchembioData` 分支：
- 存储 key：`CMD_KEYWORD_SEARCH:{task_id}:results:ichembio`
- 序列化、TTL（`REDIS_CACHE_TTL`，默认 24h）与现有 RawData/ProductPackage 一致
- 该分支日志以 `cas` 标识 item（现有日志用 `cat_no`，IchembioData 无此字段）

数据库入库走现有 `AutoDBPipeline`，无需改动。

## 错误处理

- 403 / 5xx / 302 / 响应过短 → 代理刷新重试（`PROXY_POOL_REFRESH_STATUS_CODES` + `is_proxy_invalid`）
- 搜索无结果 → 正常结束该 query，不算错误
- 详情页字段缺失 → 字段置 None，不丢弃 item

## 测试

- `tests/test_ichembio_spider.py`：用保存的详情页 HTML fixture 验证 `parse_detail` 字段提取（H/P 码、GHS 图标列表、`-` 空值处理）
- 手动验证：
  - 文件模式：小文件（3~5 个 CAS）跑通并入库
  - API 模式：`cmd_keyword_search` 跑通，Redis 中可查到 `CMD_KEYWORD_SEARCH:{task_id}:results:ichembio`

## 部署

无需改 docker/compose；scrapyd 中以 `ichembio` 名调度。

## 运行示例

```bash
# 枚举模式（全量）
uv run --env-file ./test.local.env scrapy crawl ichembio

# 文件模式
uv run --env-file ./test.local.env scrapy crawl ichembio -a cas_file=./data/cas_list.txt

# API 搜索模式
curl -X POST http://127.0.0.1:6800/schedule.json \
  -d project=product_spider -d spider=ichembio \
  -d cmd_keyword_search=True -d keyword=methanol -d task_id=xxx
```

## 明确不做（YAGNI）

- 不采集"逆合成路线"模块（页面中唯一 JS 异步加载区域）
- 不实现 CSV 格式 CAS 文件（仅 txt）
- 不改 API Service 返回结构（IchembioData 结果直接从 Redis 读取，如需 API 端点后续另议）
