"""
统一配置管理模块
使用 Pydantic Settings 集中管理所有配置项
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
from dotenv import load_dotenv


# 加载 .env 文件
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)


class Settings(BaseSettings):
    """
    应用配置类
    
    所有配置项通过环境变量或 .env 文件设置
    优先级：环境变量 > .env 文件 > 默认值
    """
    
    # ==================== LLM 配置 ====================
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI/DeepSeek API Key"
    )
    openai_api_base: str = Field(
        default="https://api.deepseek.com/v1",
        description="API Base URL"
    )
    llm_model: str = Field(
        default="deepseek-chat",
        description="默认使用的 LLM 模型"
    )
    llm_temperature: float = Field(
        default=0.1,
        description="LLM 温度参数"
    )
    llm_max_tokens: int = Field(
        default=4096,
        description="LLM 最大 token 数"
    )
    
    # ==================== 数据库配置 ====================
    database_url: str = Field(
        default="sqlite:///workflow_test.db",
        description="数据库连接 URL"
    )
    db_pool_size: int = Field(
        default=10,
        description="数据库连接池大小"
    )
    db_max_overflow: int = Field(
        default=20,
        description="数据库连接池最大溢出"
    )
    db_pool_pre_ping: bool = Field(
        default=True,
        description="连接前检查连接是否有效"
    )
    db_echo: bool = Field(
        default=False,
        description="是否打印 SQL 日志"
    )
    
    # ==================== 应用配置 ====================
    app_name: str = Field(
        default="PyCoze Workflow Engine",
        description="应用名称"
    )
    app_version: str = Field(
        default="2.1.0",
        description="应用版本"
    )
    debug: bool = Field(
        default=False,
        description="调试模式"
    )
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    
    # ==================== API 配置 ====================
    api_host: str = Field(
        default="0.0.0.0",
        description="API 服务主机"
    )
    api_port: int = Field(
        default=8000,
        description="API 服务端口"
    )
    api_workers: int = Field(
        default=1,
        description="API 工作进程数"
    )
    
    # ==================== 限流配置 ====================
    rate_limit_enabled: bool = Field(
        default=False,
        description="是否启用限流"
    )
    rate_limit_times: int = Field(
        default=100,
        description="限流次数"
    )
    rate_limit_seconds: int = Field(
        default=60,
        description="限流时间窗口（秒）"
    )
    
    # ==================== 循环节点配置 ====================
    loop_max_iterations: int = Field(
        default=100,
        description="循环节点最大迭代次数（防止死循环）"
    )
    loop_default_iterations: int = Field(
        default=10,
        description="循环节点默认最大迭代次数"
    )
    
    # ==================== 缓存配置 ====================
    cache_enabled: bool = Field(
        default=False,
        description="是否启用缓存"
    )
    cache_ttl: int = Field(
        default=300,
        description="缓存过期时间（秒）"
    )
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis 连接 URL"
    )
    
    @field_validator("openai_api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        """验证 API Key，支持从环境变量 OPENAI_API_KEY 读取"""
        if v is None:
            return os.getenv("OPENAI_API_KEY")
        return v

    @field_validator("llm_model", mode="before")
    @classmethod
    def validate_llm_model(cls, v: Optional[str]) -> str:
        if v and str(v).strip() and str(v).strip() != "deepseek-chat":
            return str(v).strip()
        return os.getenv("OPENAI_MODEL_NAME") or os.getenv("LLM_MODEL") or "deepseek-chat"
    
    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """验证数据库 URL，支持从环境变量 DATABASE_URL 读取"""
        if v == "sqlite:///workflow_test.db":
            env_url = os.getenv("DATABASE_URL")
            if env_url:
                return env_url
        return v
    
    class Config:
        env_file = str(env_path)
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略未定义的环境变量


class LLMSettings(BaseSettings):
    """
    LLM 专用配置类
    用于创建 LangChain LLM 实例
    """
    openai_api_key: Optional[str] = Field(default=None)
    openai_api_base: str = Field(default="https://api.deepseek.com/v1")
    model_name: str = Field(default="deepseek-chat")
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=4096)
    
    @field_validator("openai_api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return os.getenv("OPENAI_API_KEY")
        return v

    @field_validator("model_name", mode="before")
    @classmethod
    def validate_model_name(cls, v: Optional[str]) -> str:
        if v and str(v).strip() and str(v).strip() != "deepseek-chat":
            return str(v).strip()
        return os.getenv("OPENAI_MODEL_NAME") or os.getenv("LLM_MODEL") or "deepseek-chat"
    
    class Config:
        env_file = str(env_path)
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    def to_langchain_kwargs(self) -> dict:
        """转换为 LangChain LLM 初始化参数"""
        kwargs = {
            "model": self.model_name,
            "temperature": self.temperature,
            "openai_api_base": self.openai_api_base,
        }
        if self.openai_api_key:
            kwargs["openai_api_key"] = self.openai_api_key
        return kwargs


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例（缓存）
    
    Returns:
        Settings: 配置实例
    """
    return Settings()


@lru_cache()
def get_llm_settings(
    model_name: Optional[str] = None,
    temperature: Optional[float] = None
) -> LLMSettings:
    """
    获取 LLM 配置
    
    Args:
        model_name: 模型名称（可选，覆盖默认值）
        temperature: 温度参数（可选，覆盖默认值）
    
    Returns:
        LLMSettings: LLM 配置实例
    """
    settings = get_settings()
    return LLMSettings(
        openai_api_key=settings.openai_api_key,
        openai_api_base=settings.openai_api_base,
        model_name=model_name or settings.llm_model,
        temperature=temperature or settings.llm_temperature,
        max_tokens=settings.llm_max_tokens
    )


# 便捷访问
settings = get_settings()
