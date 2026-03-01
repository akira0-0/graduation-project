# -*- coding: utf-8 -*-
"""
测试三个爬虫同时异步运行
"""
import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.runner import CrawlerRunner
from scheduler.logger import get_logger
from scheduler import config as cfg

logger = get_logger(__name__)


async def test_parallel_crawlers():
    """测试三个爬虫并行运行"""
    
    # 测试用关键词（只用1-2个减少测试时间）
    test_keywords = ["测试热搜词"]
    
    logger.info("=" * 60)
    logger.info("开始测试三个爬虫并行运行")
    logger.info(f"测试关键词: {test_keywords}")
    logger.info("=" * 60)
    
    runner = CrawlerRunner(test_keywords)
    
    start_time = time.time()
    
    # 修改runner让三个爬虫都并行运行
    tasks = []
    task_names = []
    
    if cfg.ENABLE_WEIBO:
        logger.info("添加微博爬虫任务...")
        tasks.append(runner.run_weibo_crawler())
        task_names.append('weibo')
    
    if cfg.ENABLE_XHS:
        logger.info("添加小红书爬虫任务...")
        tasks.append(runner.run_xhs_crawler())
        task_names.append('xhs')
    
    if cfg.ENABLE_WEB:
        logger.info("添加网易新闻爬虫任务...")
        tasks.append(runner.run_web_crawler())
        task_names.append('web')
    
    logger.info("=" * 60)
    logger.info(f"开始并行运行 {len(tasks)} 个爬虫: {', '.join(task_names)}")
    logger.info("=" * 60)
    
    # 并行运行所有爬虫
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_time = time.time() - start_time
    
    # 输出结果
    logger.info("")
    logger.info("=" * 60)
    logger.info("测试结果")
    logger.info("=" * 60)
    
    for name, result in zip(task_names, results):
        if isinstance(result, Exception):
            logger.error(f"❌ {name}: 异常 - {result}")
        elif isinstance(result, list):
            success_count = sum(1 for r in result if r.success)
            total_posts = sum(r.posts_count for r in result)
            total_comments = sum(r.comments_count for r in result)
            logger.info(f"✅ {name}: 成功 {success_count}/{len(result)}, "
                       f"帖子 {total_posts}, 评论 {total_comments}")
        else:
            logger.info(f"❓ {name}: 未知结果 - {result}")
    
    logger.info("")
    logger.info(f"总耗时: {total_time:.2f} 秒")
    logger.info("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("测试三个爬虫同时异步运行")
    print("=" * 60)
    print()
    
    asyncio.run(test_parallel_crawlers())
