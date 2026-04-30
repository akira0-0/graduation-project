#!/bin/bash
set -e

# PostgreSQL 初始化脚本
# 此脚本在 PostgreSQL 容器首次启动时自动执行

echo "========================================="
echo "PostgreSQL 初始化脚本开始执行"
echo "========================================="

# 设置变量
DB_USER="${POSTGRES_USER:-workflow_user}"
DB_NAME="${POSTGRES_DB:-workflow_db}"

echo "数据库用户: $DB_USER"
echo "数据库名称: $DB_NAME"

# 创建扩展（如果需要）
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$DB_NAME" <<-EOSQL
    -- 启用必要的 PostgreSQL 扩展
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    
    -- 授予用户权限
    GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
    GRANT ALL ON SCHEMA public TO $DB_USER;
    
    -- 设置默认权限
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
    
    echo "扩展和权限设置完成"
EOSQL

echo "========================================="
echo "PostgreSQL 初始化脚本执行完成"
echo "========================================="