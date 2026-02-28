#!/usr/bin/env python3
"""
测试allmpus_spider的keyword_search功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from product_spider.spiders.allmpus_spider import AllmpusSpider

def test_keyword_search():
    """测试关键词搜索功能"""

    # 配置settings
    settings = get_project_settings()
    settings.set('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36')
    settings.set('LOG_LEVEL', 'INFO')
    settings.set('ITEM_PIPELINES', {
        'product_spider.pipelines.RawDataPipeline': 300,
    })

    # 创建爬虫实例（API请求模式）
    spider = AllmpusSpider(
        cmd_keyword_search=True,
        keyword="acetone",
        task_id="test-task-123"
    )

    # 创建爬虫进程
    process = CrawlerProcess(settings)

    # 添加爬虫
    process.crawl(spider)

    # 开始爬取
    process.start()

    print("测试完成！")

def test_normal_crawl():
    """测试正常字母导航爬取"""

    settings = get_project_settings()
    settings.set('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36')
    settings.set('LOG_LEVEL', 'INFO')

    # 创建爬虫实例（普通模式）
    spider = AllmpusSpider(
        cmd_keyword_search=False
    )

    process = CrawlerProcess(settings)
    process.crawl(spider)
    process.start()

    print("正常爬取测试完成！")

if __name__ == "__main__":
    print("开始测试 allmpus_spider...")

    # 测试关键词搜索
    print("\n=== 测试关键词搜索 ===")
    test_keyword_search()

    # 测试普通爬取
    # print("\n=== 测试普通爬取 ===")
    # test_normal_crawl()