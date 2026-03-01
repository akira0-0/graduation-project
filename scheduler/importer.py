# -*- coding: utf-8 -*-
"""
数据库导入模块
将统一格式数据导入到 Supabase
"""
import os
import sys
import json
from datetime import datetime
from typing import Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import config as cfg
from .logger import get_logger

logger = get_logger(__name__)


def import_to_database() -> Tuple[int, int]:
    """
    将统一格式数据导入到数据库
    
    Returns:
        (导入的帖子数, 导入的评论数)
    """
    try:
        # 导入 Supabase 相关模块
        from supabase import create_client, Client
        
        # 尝试从 import_with_sdk.py 获取配置
        try:
            from import_with_sdk import (
                SUPABASE_URL, SUPABASE_KEY,
                import_posts_with_sdk, import_comments_with_sdk,
                create_supabase_client
            )
        except ImportError:
            logger.error("无法导入 import_with_sdk 模块")
            return 0, 0
        
        # 创建客户端
        supabase = create_supabase_client()
        if not supabase:
            logger.error("创建 Supabase 客户端失败")
            return 0, 0
        
        total_posts = 0
        total_comments = 0
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 导入各平台数据
        platforms = ['weibo', 'xhs', 'wangyi']
        
        for platform in platforms:
            platform_dir = os.path.join(cfg.UNIFIED_DIR, platform)
            
            if not os.path.exists(platform_dir):
                logger.debug(f"{platform} 数据目录不存在，跳过")
                continue
            
            # 导入帖子
            posts_file = os.path.join(platform_dir, f'search_posts_{today}.json')
            if os.path.exists(posts_file):
                logger.info(f"导入 {platform} 帖子数据: {posts_file}")
                count = import_posts_with_sdk(supabase, posts_file)
                total_posts += count
                logger.info(f"✅ {platform} 帖子导入完成: {count} 条")
            
            # 导入评论
            comments_file = os.path.join(platform_dir, f'search_comments_{today}.json')
            if os.path.exists(comments_file):
                logger.info(f"导入 {platform} 评论数据: {comments_file}")
                count = import_comments_with_sdk(supabase, comments_file)
                total_comments += count
                logger.info(f"✅ {platform} 评论导入完成: {count} 条")
        
        logger.info("=" * 60)
        logger.info(f"数据库导入完成: 帖子 {total_posts}, 评论 {total_comments}")
        logger.info("=" * 60)
        
        return total_posts, total_comments
        
    except ImportError as e:
        logger.error(f"导入模块失败 (可能需要安装 supabase): {e}")
        return 0, 0
    except Exception as e:
        logger.error(f"数据库导入失败: {e}")
        return 0, 0


def run_import():
    """
    运行数据库导入
    """
    logger.info("=" * 60)
    logger.info("开始数据库导入")
    logger.info("=" * 60)
    
    posts, comments = import_to_database()
    
    return posts, comments


if __name__ == "__main__":
    run_import()
