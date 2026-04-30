#!/usr/bin/env python3
"""
PostgreSQL 数据库初始化脚本
直接创建所有表结构，不使用 Alembic 迁移
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from src.database.connection import init_db, get_session, close_db
from src.database.models import Base, Workflow, Conversation, Memory, AuditLog
from src.utils.logger import get_logger

logger = get_logger("init_postgres")


def check_database_connection():
    """检查数据库连接"""
    try:
        session = get_session()
        session.execute(text("SELECT 1"))
        session.close()
        logger.info("✅ 数据库连接成功")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {str(e)}")
        return False


def create_tables():
    """创建所有表"""
    try:
        logger.info("开始创建数据库表...")
        init_db()
        logger.info("✅ 数据库表创建成功")
        return True
    except Exception as e:
        logger.error(f"❌ 创建数据库表失败: {str(e)}")
        return False


def verify_tables():
    """验证表结构"""
    try:
        session = get_session()
        
        # 检查表是否存在
        tables = ['workflows', 'conversations', 'memories', 'audit_logs']
        logger.info("验证数据库表...")
        
        for table in tables:
            query = text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            result = session.execute(query)
            exists = result.scalar()
            if exists:
                logger.info(f"  ✅ 表 {table} 存在")
            else:
                logger.error(f"  ❌ 表 {table} 不存在")
                return False
        
        session.close()
        logger.info("✅ 所有表验证通过")
        return True
    except Exception as e:
        logger.error(f"❌ 表验证失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("PostgreSQL 数据库初始化脚本")
    print("=" * 60)
    
    # 加载环境变量
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"已加载环境配置文件: {env_path}")
    else:
        logger.warning(f"未找到环境配置文件: {env_path}")
    
    # 显示数据库配置
    db_url = os.getenv("DATABASE_URL", "未配置")
    if db_url and db_url != "未配置":
        # 隐藏密码
        if "@" in db_url:
            parts = db_url.split("@")
            masked_url = parts[0].rsplit(":", 1)[0] + ":***@" + parts[1]
            logger.info(f"数据库 URL: {masked_url}")
        else:
            logger.info(f"数据库 URL: {db_url}")
    else:
        logger.error("❌ 未配置 DATABASE_URL 环境变量")
        sys.exit(1)
    
    print()
    
    # 步骤 1: 检查连接
    if not check_database_connection():
        logger.error("\n请检查:")
        logger.error("  1. PostgreSQL 服务是否正在运行")
        logger.error("  2. 数据库连接配置是否正确")
        logger.error("  3. 数据库用户是否有足够权限")
        sys.exit(1)
    
    print()
    
    # 步骤 2: 创建表
    if not create_tables():
        sys.exit(1)
    
    print()
    
    # 步骤 3: 验证表
    if not verify_tables():
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ 数据库初始化完成!")
    print("=" * 60)
    print()
    print("下一步:")
    print("  1. 验证数据库连接: python test/test_db_connection.py")
    print("  2. 运行应用测试: pytest test/test_agent_nodes.py")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ 初始化过程中发生错误: {str(e)}")
        sys.exit(1)
    finally:
        close_db()