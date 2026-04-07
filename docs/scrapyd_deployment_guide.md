# Scrapyd 测试部署指南

## 1. 启动 Scrapyd 服务

### 本地测试环境

```bash
# 在项目根目录启动 scrapyd
scrapyd

# 或使用 docker-compose 启动
docker-compose up -d scrapyd
```

### 验证服务状态

```bash
# 检查 daemon 状态
curl http://127.0.0.1:6800/daemonstatus.json

# 预期返回
{"status": "ok", "running": "0", "pending": "0", "finished": "0", "node_name": "your-node"}
```

## 2. 部署项目

### 使用 scrapyd 部署

```bash
# 部署到测试环境
uv run --env-file {...} scrapyd
```

### scrapy.cfg 配置示例

```ini
[settings]
default = product_spider.settings

[deploy:testing]
url = http://127.0.0.1:6800/
project = product_spider
```

### 查看已部署项目

```bash
# 列出所有项目
curl http://127.0.0.1:6800/listprojects.json

# 预期返回
{"status": "ok", "projects": ["product_spider"]}
```

## 3. 查看可用爬虫

```bash
# 列出项目下的所有爬虫
curl http://127.0.0.1:6800/listspiders.json?project=product_spider

# 预期返回
{"status": "ok", "spiders": ["allmpus", "aladdin", "usp", ...]}
```

## 4. 启动爬虫任务

### 基础启动

```bash
# 启动普通爬取
curl http://127.0.0.1:6800/schedule.json \
  -d project=product_spider \
  -d spider=allmpus
```

### 启动关键词搜索（验证 keyword_search）

```bash
# 启动 allmpus 关键词搜索
curl http://127.0.0.1:6800/schedule.json \
  -d project=product_spider \
  -d spider=allmpus \
  -d cmd_keyword_search=True \
  -d keyword=acetone \
  -d task_id=test-task-001

# 返回示例
{"status": "ok", "jobid": "94bd8ce041fd11e48b9e0242ac110007"}
```

### 带额外参数的搜索

```bash
# 带 search_params 的搜索
curl http://127.0.0.1:6800/schedule.json \
  -d project=product_spider \
  -d spider=allmpus \
  -d cmd_keyword_search=True \
  -d keyword=acetone \
  -d task_id=test-task-002 \
  -d setting=DOWNLOAD_DELAY=1 \
  -d setting=CONCURRENT_REQUESTS=2
```

## 5. 查看任务状态

### 列出所有任务

```bash
# 查看运行中的任务
curl http://127.0.0.1:6800/listjobs.json?project=product_spider

# 预期返回
{
  "status": "ok",
  "pending": [],
  "running": [
    {"id": "94bd8ce0...", "spider": "allmpus", "pid": 1234, "start_time": "2026-02-27 10:00:00"}
  ],
  "finished": []
}
```

### 查看具体任务日志

```bash
# 获取任务日志
curl http://127.0.0.1:6800/logs/product_spider/allmpus/94bd8ce041fd11e48b9e0242ac110007.log
```

## 6. 取消任务

```bash
# 取消运行中的任务
curl http://127.0.0.1:6800/cancel.json \
  -d project=product_spider \
  -d job=94bd8ce041fd11e48b9e0242ac110007
```

## 7. 测试脚本

### Bash 测试脚本

```bash
#!/bin/bash

SCRAPYD_URL="http://127.0.0.1:6800"
PROJECT="product_spider"
SPIDER="allmpus"
KEYWORD="acetone"
TASK_ID="test-$(date +%s)"

echo "=== 1. 检查 Scrapyd 状态 ==="
curl -s "${SCRAPYD_URL}/daemonstatus.json" | python3 -m json.tool

echo ""
echo "=== 2. 列出项目 ==="
curl -s "${SCRAPYD_URL}/listprojects.json" | python3 -m json.tool

echo ""
echo "=== 3. 列出爬虫 ==="
curl -s "${SCRAPYD_URL}/listspiders.json?project=${PROJECT}" | python3 -m json.tool

echo ""
echo "=== 4. 启动关键词搜索任务 ==="
echo "Keyword: ${KEYWORD}, Task ID: ${TASK_ID}"

RESULT=$(curl -s "${SCRAPYD_URL}/schedule.json" \
  -d project="${PROJECT}" \
  -d spider="${SPIDER}" \
  -d cmd_keyword_search=True \
  -d keyword="${KEYWORD}" \
  -d task_id="${TASK_ID}")

echo "$RESULT" | python3 -m json.tool

JOB_ID=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('jobid', ''))")

echo ""
echo "=== 5. 查看任务状态 ==="
sleep 2
curl -s "${SCRAPYD_URL}/listjobs.json?project=${PROJECT}" | python3 -m json.tool

echo ""
echo "=== 6. 任务信息 ==="
echo "Task ID: ${TASK_ID}"
echo "Job ID: ${JOB_ID}"
echo ""
echo "检查 Redis 中是否有结果:"
echo "redis-cli -h 192.168.4.246 -p 6380 -n 2 smembers active_tasks"
echo "redis-cli -h 192.168.4.246 -p 6380 -n 2 zrange 'task:${TASK_ID}:results' 0 -1"
```

### Python 测试脚本

```python
#!/usr/bin/env python3
"""测试 keyword_search 功能"""

import requests
import time
import json

SCRAPYD_URL = "http://127.0.0.1:6800"
PROJECT = "product_spider"

def test_daemon_status():
    """测试 Scrapyd 服务状态"""
    resp = requests.get(f"{SCRAPYD_URL}/daemonstatus.json")
    print(f"Daemon Status: {resp.json()}")
    return resp.json().get("status") == "ok"

def test_list_spiders():
    """测试列出爬虫"""
    resp = requests.get(f"{SCRAPYD_URL}/listspiders.json", params={"project": PROJECT})
    print(f"Spiders: {resp.json()}")
    return resp.json().get("spiders", [])

def test_keyword_search(spider_name="allmpus", keyword="acetone"):
    """测试关键词搜索"""
    task_id = f"test-{int(time.time())}"

    data = {
        "project": PROJECT,
        "spider": spider_name,
        "cmd_keyword_search": "True",
        "keyword": keyword,
        "task_id": task_id,
    }

    resp = requests.post(f"{SCRAPYD_URL}/schedule.json", data=data)
    result = resp.json()

    print(f"Start Keyword Search: {result}")
    print(f"Task ID: {task_id}")
    print(f"Job ID: {result.get('jobid')}")

    return task_id, result.get("jobid")

def test_list_jobs():
    """测试列出任务"""
    resp = requests.get(f"{SCRAPYD_URL}/listjobs.json", params={"project": PROJECT})
    print(f"Jobs: {json.dumps(resp.json(), indent=2)}")
    return resp.json()

def main():
    print("=== Scrapyd Keyword Search Test ===\n")

    # 1. 检查服务状态
    print("1. 检查服务状态...")
    if not test_daemon_status():
        print("Scrapyd 服务未启动！")
        return
    print("✓ 服务正常\n")

    # 2. 列出爬虫
    print("2. 列出可用爬虫...")
    spiders = test_list_spiders()
    if "allmpus" not in spiders:
        print("allmpus 爬虫不存在！")
        return
    print("✓ 爬虫存在\n")

    # 3. 启动关键词搜索
    print("3. 启动关键词搜索...")
    task_id, job_id = test_keyword_search()
    print(f"✓ 任务已启动\n")

    # 4. 等待并检查状态
    print("4. 等待任务执行...")
    for i in range(5):
        time.sleep(3)
        jobs = test_list_jobs()
        running = jobs.get("running", [])
        finished = jobs.get("finished", [])

        # 检查任务是否完成
        job_finished = any(j["id"] == job_id for j in finished)
        if job_finished:
            print(f"✓ 任务已完成\n")
            break
        else:
            print(f"  等待中... ({i+1}/5)")

    # 5. 检查 Redis 结果
    print("5. 检查 Redis 结果...")
    print(f"执行: redis-cli -h 192.168.4.246 -p 6380 -n 2 zrange 'task:{task_id}:results' 0 -1")
    print("(需要在 shell 中手动检查)")

if __name__ == "__main__":
    main()
```

## 8. 验证 keyword_search 成功的标志

### 1. 任务成功启动
- `schedule.json` 返回 `{"status": "ok", "jobid": "..."}`

### 2. 任务正常运行
- `listjobs.json` 中能看到任务在 `running` 或 `finished` 列表中

### 3. Redis 中有结果数据
```bash
# 检查任务是否在活跃列表中
# 检查任务是否在活跃列表中
redis-cli -h 192.168.4.246 -p 6380 -n 2 sismember active_tasks test-task-001

# 查看任务结果
redis-cli -h 192.168.4.246 -p 6380 -n 2 zrange task:test-task-001:results 0 -1

# 查看任务结果数量
redis-cli -h 192.168.4.246 -p 6380 -n 2 get task:test-task-001:results:count
```

### 4. 日志正常
```bash
# 查看日志中是否有 keyword_search 相关输出
curl http://127.0.0.1:6800/logs/product_spider/allmpus/JOB_ID.log | grep -i keyword
```

## 9. 常见问题排查

### 问题 1: Project not found
```bash
# 解决：先部署项目
scrapyd-deploy testing -p product_spider
```

### 问题 2: Spider not found
```bash
# 检查爬虫名称拼写
curl http://127.0.0.1:6800/listspiders.json?project=product_spider
```

### 问题 3: task_id 未传递
```bash
# 检查参数是否正确
curl http://127.0.0.1:6800/schedule.json \
  -d project=product_spider \
  -d spider=allmpus \
  -d cmd_keyword_search=True \
  -d keyword=acetone \
  -d task_id=your-task-id
```

### 问题 4: Redis 无结果
```bash
# 检查 Redis 连接
redis-cli -h 192.168.4.246 -p 6380 -n 2 ping

# 检查 Pipeline 是否启用
grep RedisPipeline product_spider/settings.py
```

## 10. Docker Compose 测试环境

```yaml
version: '3'
services:
  scrapyd:
    build: .
    ports:
      - "6800:6800"
    volumes:
      - .:/app
      - scrapyd_data:/app/dbs

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  scrapyd_data:
```

启动测试环境：
```bash
docker-compose up -d scrapyd redis

# 部署项目
docker-compose exec scrapyd scrapyd-deploy testing -p product_spider

# 运行测试
curl http://127.0.0.1:6800/schedule.json \
  -d project=product_spider \
  -d spider=allmpus \
  -d cmd_keyword_search=True \
  -d keyword=acetone \
  -d task_id=docker-test-001
```