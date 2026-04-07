# Keyword Search 功能使用说明

## 概述

本功能为 `BaseSpider` 提供了关键词搜索支持，通过 `keyword_search` 方法实现统一的关键词搜索接口。

## 功能特点

1. **统一接口**：所有继承自 `BaseSpider` 的爬虫都可以实现 `keyword_search` 方法
2. **API支持**：支持API请求模式，可以传入 `task_id` 进行任务追踪
3. **结果存储**：通过Redis Pipeline存储搜索结果，支持按任务ID查询
4. **兼容性**：不影响原有爬虫的普通爬取功能

## 使用方法

### 1. 启动关键词搜索爬虫

```python
# 创建爬虫实例（任务模式）
spider = AllmpusSpider(
    cmd_keyword_search=True,    # 启用关键词搜索
    keyword="acetone",          # 搜索关键词
    task_id="custom-task-id"    # 任务ID（可选）
)

# 启动爬取
process.crawl(spider)
```

### 2. 普通字母导航爬取

```python
# 创建爬虫实例（普通模式）
spider = AllmpusSpider(
    cmd_keyword_search=False    # 不启用关键词搜索
)
```

### 3. API服务调用示例

```python
import requests

# 启动搜索任务
response = requests.post('http://localhost:8000/api/spiders/run', json={
    "spider_name": "allmpus",
    "keyword": "acetone",
    "task_id": "my-task-123"
})

# 获取任务状态
status = requests.get('http://localhost:8000/api/spiders/status/my-task-123')

# 获取搜索结果
results = requests.get('http://localhost:8000/api/spiders/result/my-task-123')
```

## 实现细节

### BaseSpider 增强功能

- 支持通过构造函数传入 `task_id` 参数进行任务追踪
- 在 `start_requests` 方法中验证 `task_id`，启用关键词搜索时必须有 `task_id`
- 子类在 `keyword_search` 中需要将 `self.task_id` 添加到请求 meta

### 爬虫端修改

- 实现 `keyword_search` 方法，**构建搜索请求并将 `task_id` 添加到 meta**
- 在解析方法中通过 `response.meta.get('task_id')` 获取任务ID

#### keyword_search 实现示例

```python
def keyword_search(self, keyword: str, search_params: dict = None):
    """关键词搜索方法 - 构建搜索请求，添加 task_id 到 meta"""
    # 构建搜索URL
    search_url = f"{self.base_url}/search.php"
    params = {'search_query': keyword}

    if search_params:
        params.update(search_params)

    # 返回请求，将 task_id 添加到 meta
    yield Request(
        url=f"{search_url}?{urlencode(params)}",
        callback=self.parse_search_results,  # 或者使用原有的某个方法
        meta={
            'keyword': keyword,
            'search_params': search_params,
            'task_id': self.task_id,  # 必须添加
        }
    )
```

### Redis Pipeline

- 使用Sorted Set存储结果，按时间排序
- 支持分页查询
- 自动设置过期时间
- 提供任务状态查询接口

## 环境配置

### Redis 配置

在 `settings.py` 中配置Redis连接：

```python
REDIS_HOST = "localhost"
REDIS_PORT = "6379"
REDIS_URL = "redis://localhost:6379/0"  # 优先使用此配置
```

### Pipeline 配置

确保在 `ITEM_PIPELINES` 中添加：

```python
'product_spider.pipelines.redis_pipeline.RedisPipeline': 290,
```

## 数据结构

### Redis 中存储的数据

```
task:{task_id}:results          # Sorted Set，存储结果
task:{task_id}:results:count   # String，结果总数
task:{task_id}:first_result     # String，第一个结果时间
task:{task_id}:last_result      # String，最后一个结果时间
active_tasks                   # Set，活跃任务列表
completed_tasks                 # Sorted Set，完成任务列表
```

### 爬虫结果数据格式

```json
{
  "brand": "allmpus",
  "cat_no": "12345",
  "en_name": "Acetone",
  "cas": "67-64-1",
  "mf": "C3H6O",
  "mw": "58.08",
  "stock_info": "In Stock",
  "purity": ">99%",
  "img_url": "https://...",
  "info1": "Propanone",
  "info2": "Room Temperature",
  "prd_url": "https://...",
  "_search_info": {
    "keyword": "acetone",
    "spider": "allmpus",
    "timestamp": 1645584000.0,
    "task_id": "custom-task-id"
  }
}
```

## 注意事项

1. **任务ID**：建议提供唯一的 `task_id`，便于后续查询和管理
2. **Redis连接**：确保Redis服务正常运行，并有足够的存储空间
3. **Redis连接**：确保Redis服务正常运行，并有足够的存储空间
4. **爬虫兼容性**：修改后的爬虫仍然支持普通模式爬取
5. **网络延迟**：网络请求可能有一定延迟，建议设置适当的超时时间

## 故障排查

### 常见问题

1. **任务无结果**
   - 检查Redis连接是否正常
   - 确认爬虫是否成功执行搜索请求
   - 查看爬虫日志确认是否有错误

2. **Redis连接失败**
   - 检查Redis服务状态
   - 验证连接URL配置
   - 确认网络连接

3. **任务状态未更新**
   - 检查任务ID是否正确传递
   - 查看爬虫是否正确接收参数

## 扩展功能

### 自定义搜索参数

可以通过 `search_params` 传递额外的搜索参数：

```python
spider = AllmpusSpider(
    cmd_keyword_search=True,
    keyword="acetone",
    search_params={"category": "solvent", "min_price": "100"},
    task_id="custom-task-id"
)
```

### 结果聚合

可以使用提供的静态方法进行结果聚合：

```python
from product_spider.pipelines.redis_pipeline import RedisPipeline

# 获取任务结果
results = RedisPipeline.get_task_results(redis_client, "task-id", limit=100)

# 获取任务状态
status = RedisPipeline.get_task_status(redis_client, "task-id")
```