# -*- coding: utf-8 -*-
"""
日志模块
"""
import os
import sys
import logging
from datetime import datetime
from .config import LOG_DIR


def get_logger(name: str = None) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志名称
        
    Returns:
        Logger 实例
    """
    logger = logging.getLogger(name or 'scheduler')
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # 日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台输出 (INFO 及以上)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出 (DEBUG 及以上)
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(LOG_DIR, f'scheduler_{today}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


class TaskLogger:
    """
    任务日志记录器，用于记录任务执行详情
    """
    
    def __init__(self, task_name: str):
        self.task_name = task_name
        self.logger = get_logger(f'task.{task_name}')
        self.start_time = None
        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'posts': 0,
            'comments': 0,
        }
    
    def start(self):
        """开始任务"""
        self.start_time = datetime.now()
        self.logger.info(f"{'='*60}")
        self.logger.info(f"任务开始: {self.task_name}")
        self.logger.info(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'='*60}")
    
    def end(self):
        """结束任务"""
        end_time = datetime.now()
        duration = end_time - self.start_time if self.start_time else None
        
        self.logger.info(f"{'='*60}")
        self.logger.info(f"任务结束: {self.task_name}")
        self.logger.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if duration:
            self.logger.info(f"总耗时: {duration}")
        self.logger.info(f"统计: 成功={self.stats['success']}, 失败={self.stats['failed']}, 跳过={self.stats['skipped']}")
        self.logger.info(f"数据: 帖子={self.stats['posts']}, 评论={self.stats['comments']}")
        self.logger.info(f"{'='*60}")
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def debug(self, msg: str):
        self.logger.debug(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def success(self, keyword: str, posts: int = 0, comments: int = 0):
        """记录成功"""
        self.stats['success'] += 1
        self.stats['posts'] += posts
        self.stats['comments'] += comments
        self.logger.info(f"✅ [{keyword}] 成功 - 帖子: {posts}, 评论: {comments}")
    
    def fail(self, keyword: str, error: str):
        """记录失败"""
        self.stats['failed'] += 1
        self.logger.error(f"❌ [{keyword}] 失败 - {error}")
    
    def skip(self, keyword: str, reason: str):
        """记录跳过"""
        self.stats['skipped'] += 1
        self.logger.warning(f"⏭️ [{keyword}] 跳过 - {reason}")
    
    def retry(self, keyword: str, attempt: int, max_attempts: int):
        """记录重试"""
        self.logger.warning(f"🔄 [{keyword}] 重试 {attempt}/{max_attempts}")
