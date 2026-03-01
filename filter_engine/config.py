# -*- coding: utf-8 -*-
"""
过滤引擎配置
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """过滤引擎配置"""
    
    # 数据库配置
    DATABASE_PATH: str = Field(
        default=str(Path(__file__).parent / "data" / "rules.db"),
        description="SQLite数据库路径"
    )
    
    # LLM配置
    LLM_PROVIDER: str = Field(
        default="openai",
        description="LLM提供商: openai, qwen, glm, ollama"
    )
    LLM_API_KEY: Optional[str] = Field(
        default=None,
        description="LLM API密钥"
    )
    LLM_API_BASE: Optional[str] = Field(
        default=None,
        description="LLM API基础URL"
    )
    LLM_MODEL: str = Field(
        default="gpt-3.5-turbo",
        description="LLM模型名称"
    )
    LLM_TIMEOUT: int = Field(
        default=30,
        description="LLM请求超时时间(秒)"
    )
    LLM_MAX_TOKENS: int = Field(
        default=500,
        description="LLM最大输出token数"
    )
    
    # 缓存配置
    CACHE_ENABLED: bool = Field(
        default=True,
        description="是否启用缓存"
    )
    CACHE_MAX_SIZE: int = Field(
        default=1000,
        description="缓存最大条目数"
    )
    CACHE_TTL: int = Field(
        default=3600,
        description="缓存过期时间(秒)"
    )
    
    # 决策配置
    SPAM_THRESHOLD: float = Field(
        default=0.7,
        description="垃圾信息判定阈值"
    )
    SUSPICIOUS_THRESHOLD: float = Field(
        default=0.4,
        description="疑似垃圾阈值（需LLM复核）"
    )
    LLM_WEIGHT: float = Field(
        default=0.6,
        description="LLM判断权重"
    )
    RULE_WEIGHT: float = Field(
        default=0.4,
        description="规则判断权重"
    )
    
    # API配置
    API_HOST: str = Field(
        default="0.0.0.0",
        description="API监听地址"
    )
    API_PORT: int = Field(
        default=8081,
        description="API监听端口"
    )
    
    # 输出配置
    OUTPUT_DIR: str = Field(
        default=str(Path(__file__).parent / "data" / "output"),
        description="输出目录"
    )
    
    class Config:
        env_prefix = "FILTER_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def update_settings(**kwargs) -> Settings:
    """更新配置"""
    global settings
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings
