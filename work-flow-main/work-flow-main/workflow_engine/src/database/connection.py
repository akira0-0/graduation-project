"""
数据库连接管理
提供 PostgreSQL 数据库连接和会话管理
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from .models import Base
from ..utils.logger import get_logger
from ..config import get_settings

logger = get_logger("database")

# 获取配置
settings = get_settings()

# 创建引擎（使用统一配置）
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=settings.db_pool_pre_ping,
    echo=settings.db_echo,
    future=True
)

logger.info(f"数据库引擎已创建: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_db():
    """
    初始化数据库，创建所有表
    """
    try:
        logger.info("开始初始化数据库...")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（依赖注入使用）
    
    Yields:
        Session: 数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """
    直接获取数据库会话
    
    Returns:
        Session: 数据库会话
    """
    return SessionLocal()


def close_db():
    """
    关闭数据库连接
    """
    try:
        engine.dispose()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {str(e)}")