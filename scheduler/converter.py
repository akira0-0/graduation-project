# -*- coding: utf-8 -*-
"""
数据格式转换器
将小红书旧格式数据转换为统一格式
"""
import os
import json
import sys
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import config as cfg
from .logger import get_logger

logger = get_logger(__name__)


def convert_xhs_data(target_date: str = None) -> tuple:
    """
    转换小红书数据为统一格式
    
    Args:
        target_date: 目标日期，格式 YYYY-MM-DD，默认为今天
    
    Returns:
        (转换的帖子数, 转换的评论数)
    """
    try:
        from tools.data_format_converter import convert_xhs_to_unified, convert_xhs_comment_to_unified
        
        # 源目录和目标目录
        source_dir = os.path.join(cfg.DATA_DIR, 'xhs', 'json')
        target_dir = os.path.join(cfg.UNIFIED_DIR, 'xhs')
        
        if not os.path.exists(source_dir):
            logger.warning(f"小红书数据目录不存在: {source_dir}")
            return 0, 0
        
        os.makedirs(target_dir, exist_ok=True)
        
        # 转换数据
        posts_count = 0
        comments_count = 0
        
        # 使用指定日期或今天
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"转换小红书数据，日期: {target_date}")
        
        # 遍历源目录中的文件，只处理指定日期的数据
        for filename in os.listdir(source_dir):
            if not filename.endswith('.json'):
                continue
            
            # 只处理指定日期的数据文件
            if target_date not in filename:
                continue
            
            filepath = os.path.join(source_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if not isinstance(data, list):
                    continue
                
                # 判断是帖子还是评论
                if 'comment' in filename.lower():
                    # 转换评论
                    converted = [convert_xhs_comment_to_unified(item) for item in data]
                    comments_count += len(converted)
                    
                    # 保存到统一格式目录
                    output_file = os.path.join(target_dir, f'search_comments_{target_date}.json')
                    _merge_and_save(output_file, converted)
                    logger.info(f"转换小红书评论: {len(converted)} 条")
                elif 'contents' in filename.lower():
                    # 转换帖子 (小红书原始文件名是 search_contents_*)
                    converted = [convert_xhs_to_unified(item) for item in data]
                    posts_count += len(converted)
                    
                    # 保存到统一格式目录 (统一命名为 search_posts_*)
                    output_file = os.path.join(target_dir, f'search_posts_{target_date}.json')
                    _merge_and_save(output_file, converted)
                    logger.info(f"转换小红书帖子: {len(converted)} 条")
                    
            except Exception as e:
                logger.warning(f"转换文件失败 {filename}: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                continue
        
        logger.info(f"小红书数据转换完成: 帖子 {posts_count}, 评论 {comments_count}")
        return posts_count, comments_count
        
    except ImportError as e:
        logger.error(f"导入转换器失败: {e}")
        return 0, 0
    except Exception as e:
        logger.error(f"转换小红书数据失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0, 0


def _merge_and_save(filepath: str, new_data: List[Dict]):
    """
    合并并保存数据（去重）
    """
    existing_data = []
    
    # 加载已有数据
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except:
            existing_data = []
    
    # 去重合并
    existing_ids = {item.get('id') for item in existing_data}
    new_items = [item for item in new_data if item.get('id') not in existing_ids]
    
    all_data = existing_data + new_items
    
    # 保存
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    if new_items:
        logger.debug(f"保存数据到 {filepath}: 新增 {len(new_items)} 条")


def run_conversion(target_date: str = None, all_dates: bool = False):
    """
    运行所有数据转换
    
    Args:
        target_date: 目标日期，格式 YYYY-MM-DD，默认为今天
        all_dates: 是否转换所有日期的数据
    """
    logger.info("=" * 60)
    logger.info("开始数据格式转换")
    
    total_posts = 0
    total_comments = 0
    
    if all_dates:
        # 扫描所有日期的数据
        logger.info("模式: 转换所有日期的数据")
        dates = _scan_all_dates()
        logger.info(f"发现 {len(dates)} 个日期的数据: {', '.join(sorted(dates))}")
        
        for date in sorted(dates):
            logger.info(f"正在转换 {date} 的数据...")
            posts, comments = convert_xhs_data(date)
            total_posts += posts
            total_comments += comments
    else:
        if target_date:
            logger.info(f"目标日期: {target_date}")
        
        # 转换小红书数据
        posts, comments = convert_xhs_data(target_date)
        total_posts += posts
        total_comments += comments
    
    # 微博和网易已经是统一格式，无需转换
    logger.info("微博数据已是统一格式，无需转换")
    logger.info("网易新闻数据已是统一格式，无需转换")
    
    logger.info("=" * 60)
    logger.info(f"转换完成: 总计帖子 {total_posts}, 评论 {total_comments}")
    logger.info("=" * 60)
    
    return total_posts, total_comments


def _scan_all_dates() -> List[str]:
    """
    扫描数据目录中所有存在的日期
    
    Returns:
        日期列表，格式 YYYY-MM-DD
    """
    import re
    dates = set()
    
    # 扫描小红书数据目录
    source_dir = os.path.join(cfg.DATA_DIR, 'xhs', 'json')
    if os.path.exists(source_dir):
        for filename in os.listdir(source_dir):
            if filename.endswith('.json'):
                # 从文件名中提取日期 (格式: xxx_YYYY-MM-DD.json)
                match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                if match:
                    dates.add(match.group(1))
    
    return list(dates)


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='数据格式转换器')
    parser.add_argument('date', nargs='?', help='指定日期 (YYYY-MM-DD)，不指定则转换今天')
    parser.add_argument('--all', '-a', action='store_true', help='转换所有日期的数据')
    
    args = parser.parse_args()
    
    if args.all:
        print("📅 转换所有日期的数据")
        run_conversion(all_dates=True)
    elif args.date:
        print(f"📅 转换指定日期数据: {args.date}")
        run_conversion(args.date)
    else:
        print("📅 转换今天的数据")
        run_conversion()
