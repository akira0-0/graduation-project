"""
工作流引擎日志模块
提供统一的日志记录和配置功能
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class WorkflowLogger:
    """工作流日志记录器类"""
    
    def __init__(self, name: str = "workflow_engine", level: str = "INFO"):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """配置日志处理器"""
        # 创建格式化器
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器（可选）
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"workflow_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        formatted_msg = self._format_message(message, **kwargs)
        self.logger.debug(formatted_msg)
    
    def info(self, message: str, **kwargs):
        """记录一般信息"""
        formatted_msg = self._format_message(message, **kwargs)
        self.logger.info(formatted_msg)
    
    def warning(self, message: str, **kwargs):
        """记录警告信息"""
        formatted_msg = self._format_message(message, **kwargs)
        self.logger.warning(formatted_msg)
    
    def error(self, message: str, **kwargs):
        """记录错误信息"""
        formatted_msg = self._format_message(message, **kwargs)
        self.logger.error(formatted_msg)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误信息"""
        formatted_msg = self._format_message(message, **kwargs)
        self.logger.critical(formatted_msg)
    
    def _format_message(self, message: str, **kwargs) -> str:
        """
        格式化日志消息，将额外参数附加到消息中
        
        Args:
            message: 原始消息
            **kwargs: 额外的键值对参数
            
        Returns:
            格式化后的消息
        """
        if not kwargs:
            return message
        
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        return f"{message} | {extra_info}"


# 创建全局日志实例
logger = WorkflowLogger()


def get_logger(name: Optional[str] = None) -> WorkflowLogger:
    """
    获取日志记录器实例
    
    Args:
        name: 可选的自定义名称
        
    Returns:
        WorkflowLogger 实例
    """
    if name:
        return WorkflowLogger(name)
    return logger