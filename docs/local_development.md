# 本地开发环境配置

## 配置文件

项目使用环境变量管理敏感配置，本地调试时使用 `test.local.env` 文件。

## 快速开始

### 1. 加载环境变量

**Windows (Git Bash/WSL):**
```bash
set -a && source test.local.env && set +a
```

**Windows (PowerShell):**
```powershell
foreach ($line in Get-Content test.local.env) {
    if ($line -match "^\s*#" -or $line -match "^\s*$") { continue }
    $key, $value = $line -split "=", 2
    [Environment]::SetEnvironmentVariable($key, $value, "Process")
}
```

**Linux/Mac:**
```bash
export $(cat test.local.env | xargs)
```

### 2. 运行测试

加载环境变量后运行测试：

```bash
# 测试 Redis 连接
python tests/test_redis_connection.py

# 测试 Scrapyd 关键词搜索
python tests/test_scrapyd_keyword_search.py --spider allmpus --keyword acetone
```

### 3. 运行爬虫

```bash
# 先加载环境变量
set -a && source test.local.env && set +a

# 运行爬虫
scrapy crawl allmpus \
    -a cmd_keyword_search=True \
    -a keyword=acetone \
    -a task_id=test-001
```

### 4. 启动 API 服务

```bash
# 加载环境变量后启动
set -a && source test.local.env && set +a

python api_service/main.py
```

## test.local.env 配置说明

```ini
# 本地调试 Redis 配置
REDIS_URL=redis://192.168.4.246:6380/2
REDIS_HOST=192.168.4.246
REDIS_PORT=6380
REDIS_DB=2

# 本地调试数据库配置
DATABASE_HOST=192.168.5.247
DATABASE_PORT=5432
DATABASE_NAME=dev
DATABASE_USER=postgres
DATABASE_PWD=xxx

# Scrapyd 配置
SCRAPYD_URL=http://localhost:6800
```

## 注意事项

1. **不要提交敏感信息**
   - `test.local.env` 已被添加到 `.gitignore`
   - 生产环境使用 Docker Secrets 或环境变量注入

2. **配置优先级**
   - 环境变量 > 配置文件 > 代码默认值
   - 生产环境必须设置 `REDIS_URL` 环境变量

3. **Redis Pipeline 行为**
   - 如果 `REDIS_URL` 未配置，Pipeline 会直接报错
   - 确保 Redis 可访问后再启动爬虫

## 验证配置

```bash
# 检查环境变量是否加载成功
echo $REDIS_URL
echo $DATABASE_HOST

# 验证 Scrapy 配置
python -c "from scrapy.utils.project import get_project_settings; s = get_project_settings(); print(f'REDIS_URL: {s.get(\"REDIS_URL\")}')"
```
