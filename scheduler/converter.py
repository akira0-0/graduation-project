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


def convert_xhs_data() -> tuple:
    """
    转换小红书数据为统一格式
    
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
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 遍历源目录中的文件，只处理今天的数据
        for filename in os.listdir(source_dir):
            if not filename.endswith('.json'):
                continue
            
            # 只处理今天的数据文件
            if today not in filename:
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
                    output_file = os.path.join(target_dir, f'search_comments_{today}.json')
                    _merge_and_save(output_file, converted)
                    logger.info(f"转换小红书评论: {len(converted)} 条")
                elif 'contents' in filename.lower():
                    # 转换帖子 (小红书原始文件名是 search_contents_*)
                    converted = [convert_xhs_to_unified(item) for item in data]
                    posts_count += len(converted)
                    
                    # 保存到统一格式目录 (统一命名为 search_posts_*)
                    output_file = os.path.join(target_dir, f'search_posts_{today}.json')
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


def run_conversion():
    """
    运行所有数据转换
    """
    logger.info("=" * 60)
    logger.info("开始数据格式转换")
    logger.info("=" * 60)
    
    total_posts = 0
    total_comments = 0
    
    # 转换小红书数据
    posts, comments = convert_xhs_data()
    total_posts += posts
    total_comments += comments
    
    # 微博和网易已经是统一格式，无需转换
    logger.info("微博数据已是统一格式，无需转换")
    logger.info("网易新闻数据已是统一格式，无需转换")
    
    logger.info("=" * 60)
    logger.info(f"转换完成: 总计帖子 {total_posts}, 评论 {total_comments}")
    logger.info("=" * 60)
    
    return total_posts, total_comments


if __name__ == "__main__":
    run_conversion()
