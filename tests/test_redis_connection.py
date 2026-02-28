#!/usr/bin/env python3
"""测试 Redis 连接"""

import sys
from pathlib import Path
import os

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import redis

# 从环境变量读取，默认为本地测试地址
REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.4.246:6380/2")

def test_redis_connection():
    """测试 Redis 连接"""
    try:
        print(f"Connecting to Redis: {REDIS_URL}")
        r = redis.from_url(REDIS_URL, decode_responses=True)

        # 测试连接
        pong = r.ping()
        print(f"Ping: {pong}")

        # 测试写入
        r.set("test:connection", "ok", ex=60)
        value = r.get("test:connection")
        print(f"Test write/read: {value}")

        # 清理
        r.delete("test:connection")

        print("[OK] Redis 连接成功！")
        return True

    except Exception as e:
        print(f"[ERROR] Redis 连接失败: {e}")
        return False

if __name__ == "__main__":
    exit(0 if test_redis_connection() else 1)
