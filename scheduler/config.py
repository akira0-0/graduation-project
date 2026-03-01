# -*- coding: utf-8 -*-
"""
调度器配置
"""
import os
from datetime import time

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ==================== 调度配置 ====================
SCHEDULE_TIMES = [time(10, 0), time(22, 0)]  # 每日执行时间：早上10点、晚上10点
HOT_SEARCH_COUNT = 15       # 获取热搜词数量

# ==================== 爬虫配置 ====================
ENABLE_WEIBO = True         # 启用微博爬虫
ENABLE_XHS = True           # 启用小红书爬虫
ENABLE_WEB = True           # 启用网易新闻爬虫

# 爬取数量限制
WEIBO_MAX_PAGES = 5         # 微博每个关键词爬取页数
XHS_MAX_NOTES = 50          # 小红书每个关键词爬取笔记数
WEB_MAX_ARTICLES = 25        # 网易每个关键词爬取文章数

# 超时设置（秒）
CRAWLER_TIMEOUT = 600       # 单个关键词爬取超时
RETRY_COUNT = 2             # 失败重试次数
RETRY_DELAY = 30            # 重试间隔（秒）

# ==================== 路径配置 ====================
# 数据目录
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
UNIFIED_DIR = os.path.join(DATA_DIR, 'unified')

# 日志目录
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# ==================== 数据库配置 ====================
# Supabase 配置 (从环境变量读取)
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# ==================== 微博配置 ====================
# Cookie 从 weibo_crawler 的 config.json 读取
WEIBO_CONFIG_PATH = os.path.join(PROJECT_ROOT, 'weibo_crawler', 'weibo_crawler', 'config.json')
