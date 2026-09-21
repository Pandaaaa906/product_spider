# Sunwaypharm Spider 设计文档

日期：2026-09-20
状态：已批准

## 目标

为上海相辉医药（sunwaypharm.cn）新增一个 Scrapy spider，抓取全部产品分类的产品数据，包括**产品规格、价格、库存量、货期**。

## 网站调研结论

- 平台：kuujiasoft Web960 建站系统，与现有 `heowns_spider.py`（heowns.com）同平台，接口模式一致
- 编码：UTF-8（meta charset=utf-8，fixture 实测）
- 无需 Playwright，纯 HTTP 服务端渲染
- 分类 618（其他中间体）约 14417 页 × 20/页 ≈ 28.8 万产品，其余分类很小
- 关键接口（已实测）：
  - 列表页：`https://sunwaypharm.cn/products/{cat_id}.html?page={N}&prop_filter=%7b%7d`
  - 详情页：`https://sunwaypharm.cn/product/{pd_id}.html`
  - 规格/价格/库存/货期接口：`POST https://sunwaypharm.cn/index.aspx?a=ajaxpro_ajax&method=LoadGoods`，表单参数 `pd_id={id}`
    - 注意：heowns 用的 `a=loadgoodbyajax` 在本站实测返回空响应，故改用本站 JS（content/plugins/goodsmanage/utils.js）实际调用的 `ajaxpro_ajax&method=LoadGoods`，已实测可用
    - 响应结构（按实测响应，与 heowns 的键层级不同）：顶层无 `value` 包装，`ObjResult` 为 JSON 字符串，解析后为 `{"p_{pd_id}": [{"Inventores": [{"Goods_Info": "<JSON 字符串，含 goodsinfo.packaging/purity/brand/goodshuoqi>", "Price": float, "Goods_no": str, "Amount": float, "MoneyUnit": "CNY", ...}]}]}`，即 `Goods_Info`（大写 I）在 **Inventores 数组元素**上，不在 result 层
  - 搜索接口：`GET /search.do?a=is&psize=18&kw={keyword}&searchtmp=`，结果页与列表页同为产品卡结构

## 架构与数据流

克隆 `heowns_spider.py` 模式，每产品 2 个请求：

```
start_urls（全分类）
  → parse() 分类列表页：提取产品卡 detail URL（sunwaypharm.cn/product/{id}.html）
      翻页：pagination 当前页下一个 li 页码，拼 .html?page=N&prop_filter=%7b%7d
  → parse_detail() 详情页：货号(cat_no)/中英文名/CAS/MF/MW/面包屑分类/图片
  → POST LoadGoods(pd_id)
  → parse_package()：逐规格 yield
      RawData（产品主数据）
      ProductPackage（规格/价格/库存/货期）
      SupplierProduct（rawdata_to_supplier_product）
      RawSupplierQuotation（product_package_to_raw_supplier_quotation，无价格时跳过）
```

跨分类重复产品由 Scrapy dupefilter 对 detail URL 自动去重。

## 字段映射

| 目标字段 | 来源 |
|---|---|
| cat_no | LoadGoods `Goods_no`（如 `CB40054-100mg`，`rsplit("-", 1)` 取首段） |
| chs_name / en_name / cas / mf / mw | 详情页 `th/td` 表格（同 heowns XPath） |
| parent（分类） | 详情页面包屑末级；为"产品分类"时置 None |
| prd_url | 详情页 `response.url`（`rawdata_to_supplier_product` 需要） |
| img_url | 详情页主图 |
| brand | LoadGoods `goodsinfo.brand`（相辉）；"促销无折扣"→ `sunwaypharm`；**品牌过滤沿用 heowns 策略**：仅相辉品牌 yield `RawData`/`ProductPackage`，其他品牌记入 `other_brands` 集合跳过（但所有品牌都 yield `SupplierProduct`） |
| package | `goodsinfo.packaging` |
| purity | `goodsinfo.purity` |
| cost / currency | `Price` / CNY |
| stock_num | `Amount`（float→int） |
| delivery_time | `goodshuoqi` 非空时用之；否则 `Amount>0` → "现货"；否则 None |

## 爬取范围

- `start_urls`：首页导航全部分类链接（569 分类树下的 570-618，及 446/449/468/471/480/483/548 等），含用户指定的 618
- 翻页 URL 基数：基于 `response.url` 去掉 query string、补 `.html` 后缀，再拼 `?page={N}&prop_filter=%7b%7d`（不能硬编码分类 URL，50+ 分类共用 parse）
- 列表页混入 `www.sunwaypharm.com/product/NNN.html` 旧域名推荐链接，跳过只处理 `sunwaypharm.cn`
- 总量约 28.8 万详情页，耗时长属预期；并发用项目默认 settings

## keyword_search

`GET /search.do?a=is&psize=18&kw={keyword}&searchtmp=`，结果页复用列表页产品卡解析，走相同 detail → LoadGoods 流程。搜索结果翻页沿用同一 pagination XPath 取下一页（URL 为 `/search.do` 加 `page` 参数）；无分页元素则为单页结果。

## 错误处理

- LoadGoods 返回空 `ObjResult` 或解析失败：记录 warning，跳过该产品（不中断）
- 旧域名（sunwaypharm.com）链接跳过
- 无价格规格：跳过 RawSupplierQuotation（同 heowns）

## 测试

仿 `tests/test_jk_spider.py`：

- fixture：一个分类列表页 HTML、一个详情页 HTML、一个 LoadGoods JSON 响应（按真实响应录制，键层级以实测为准）
- 站点 GBK 编码：fixture 保存原始字节，`make_html_response` 需显式指定 `encoding='gbk'`（默认 utf-8 会乱码）
- 断言：货号/CAS/名称解析、规格数量、价格、库存、货期字段映射
- 运行方式：`uv run pytest tests/test_sunwaypharm_spider.py -v`

## 产物

- `product_spider/spiders/sunwaypharm_spider.py`（单文件，~120 行）
- `tests/test_sunwaypharm_spider.py`
- `tests/fixtures/sunwaypharm_list.html`、`sunwaypharm_detail.html`、`sunwaypharm_loadgoods.json`
