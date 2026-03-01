# -*- coding: utf-8 -*-
"""
自动化调度器主入口
每日定时运行爬虫任务
"""
import os
import sys
import asyncio
import argparse
from datetime import datetime, time
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import config as cfg
from .logger import get_logger, TaskLogger
from .hot_search import get_weibo_hot_search
from .runner import CrawlerRunner
from .converter import run_conversion
from .importer import run_import

logger = get_logger(__name__)


async def run_daily_task(keywords: Optional[list] = None, parallel_all: bool = False):
    """
    运行每日爬虫任务
    
    Args:
        keywords: 可选的关键词列表，如果不提供则自动获取热搜
        parallel_all: 是否让三个爬虫全部并行运行
    """
    task_logger = TaskLogger('daily_crawler')
    task_logger.start()
    
    try:
        # Step 1: 获取关键词
        logger.info("=" * 60)
        logger.info("Step 1: 获取微博热搜关键词")
        logger.info("=" * 60)
        
        if keywords:
            hot_keywords = keywords
            logger.info(f"使用指定关键词: {hot_keywords}")
        else:
            hot_keywords = get_weibo_hot_search(cfg.HOT_SEARCH_COUNT)
        
        if not hot_keywords:
            logger.error("获取关键词失败，任务终止")
            task_logger.end()
            return
        
        logger.info(f"本次任务将使用 {len(hot_keywords)} 个关键词")
        
        # Step 2: 运行爬虫
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 2: 运行爬虫")
        if parallel_all:
            logger.info("模式: 三个爬虫全部并行")
        else:
            logger.info("模式: 微博+小红书并行，网易新闻串行")
        logger.info("=" * 60)
        
        runner = CrawlerRunner(hot_keywords)
        results = await runner.run_all(parallel_all=parallel_all)
        
        # 统计结果
        for platform, platform_results in results.items():
            success_count = sum(1 for r in platform_results if r.success)
            total_count = len(platform_results)
            posts_count = sum(r.posts_count for r in platform_results)
            comments_count = sum(r.comments_count for r in platform_results)
            
            task_logger.stats['success'] += success_count
            task_logger.stats['failed'] += (total_count - success_count)
            task_logger.stats['posts'] += posts_count
            task_logger.stats['comments'] += comments_count
            
            logger.info(f"  {platform}: 成功 {success_count}/{total_count}, "
                       f"帖子 {posts_count}, 评论 {comments_count}")
        
        # Step 3: 数据格式转换
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 3: 数据格式转换")
        logger.info("=" * 60)
        
        run_conversion()
        
        # Step 4: 数据入库
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 4: 数据入库")
        logger.info("=" * 60)
        
        run_import()
        
    except Exception as e:
        logger.error(f"任务执行异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        task_logger.end()


def run_scheduler():
    """
    运行调度器（定时任务）
    使用 Windows 任务计划程序调用此函数
    """
    logger.info("=" * 60)
    logger.info("自动化爬虫调度器启动")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # 运行任务
    asyncio.run(run_daily_task())
    
    logger.info("=" * 60)
    logger.info("调度器任务完成")
    logger.info("=" * 60)


def main():
    """
    命令行入口
    """
    parser = argparse.ArgumentParser(
        description='自动化爬虫调度器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 立即运行（自动获取热搜）
  python -m scheduler.main run
  
  # 使用指定关键词运行
  python -m scheduler.main run --keywords "人工智能,科技新闻"
  
  # 仅运行数据转换
  python -m scheduler.main convert
  
  # 仅运行数据入库
  python -m scheduler.main import
  
  # 测试获取热搜
  python -m scheduler.main test-hot
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # run 命令
    run_parser = subparsers.add_parser('run', help='运行爬虫任务')
    run_parser.add_argument(
        '--keywords', '-k',
        type=str,
        help='指定关键词（逗号分隔），不指定则自动获取热搜'
    )
    run_parser.add_argument(
        '--no-weibo', 
        action='store_true',
        help='禁用微博爬虫'
    )
    run_parser.add_argument(
        '--no-xhs',
        action='store_true', 
        help='禁用小红书爬虫'
    )
    run_parser.add_argument(
        '--no-web',
        action='store_true',
        help='禁用网易新闻爬虫'
    )
    run_parser.add_argument(
        '--parallel',
        action='store_true',
        help='三个爬虫全部并行运行（默认网易新闻单独运行）'
    )
    
    # convert 命令
    subparsers.add_parser('convert', help='运行数据格式转换')
    
    # import 命令
    subparsers.add_parser('import', help='运行数据库导入')
    
    # test-hot 命令
    test_parser = subparsers.add_parser('test-hot', help='测试获取热搜')
    test_parser.add_argument(
        '--count', '-c',
        type=int,
        default=15,
        help='获取热搜数量 (默认: 15)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'run':
        # 处理爬虫开关
        if args.no_weibo:
            cfg.ENABLE_WEIBO = False
        if args.no_xhs:
            cfg.ENABLE_XHS = False
        if args.no_web:
            cfg.ENABLE_WEB = False
        
        # 处理关键词
        keywords = None
        if args.keywords:
            keywords = [k.strip() for k in args.keywords.split(',')]
        
        # 处理并行模式
        parallel_all = getattr(args, 'parallel', False)
        
        asyncio.run(run_daily_task(keywords, parallel_all=parallel_all))
        
    elif args.command == 'convert':
        run_conversion()
        
    elif args.command == 'import':
        run_import()
        
    elif args.command == 'test-hot':
        keywords = get_weibo_hot_search(args.count)
        print(f"\n获取到 {len(keywords)} 个热搜词:")
        for i, kw in enumerate(keywords, 1):
            print(f"  {i}. {kw}")
            
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
