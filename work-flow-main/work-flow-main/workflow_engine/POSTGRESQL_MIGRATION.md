# PostgreSQL 数据库配置与迁移指南

本文档提供详细的 PostgreSQL 数据库配置步骤和从 SQLite 迁移的完整指南。

## 📋 目录

- [前置要求](#前置要求)
- [安装配置](#安装配置)
- [数据库迁移](#数据库迁移)
- [验证测试](#验证测试)
- [常见问题](#常见问题)

## 🔧 前置要求

### 必需软件

- **PostgreSQL 12+** (推荐 14 或 15 版本)
- **Python 3.8+**
- 已安装的 Python 依赖包（见 requirements.txt）

### Python 依赖

项目已包含必要的 PostgreSQL 依赖：

```txt
asyncpg          # PostgreSQL 异步驱动
sqlalchemy       # ORM 框架
alembic          # 数据库迁移工具
psycopg2-binary  # PostgreSQL 同步驱动（可选，用于 Alembic）
```

## 📦 安装配置

### 步骤 1: 安装 PostgreSQL

#### macOS (使用 Homebrew)

```bash
# 安装 PostgreSQL
brew install postgresql@15

# 启动 PostgreSQL 服务
brew services start postgresql@15

# 创建数据库用户
createuser -s postgres

# 验证安装
psql --version
```

#### Ubuntu/Debian

```bash
# 安装 PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 切换到 postgres 用户并创建数据库
sudo -u postgres psql
```

#### Windows

1. 下载 [PostgreSQL 安装程序](https://www.postgresql.org/download/windows/)
2. 运行安装程序并按提示完成安装
3. 记住设置的超级用户密码

### 步骤 2: 创建数据库和用户

连接到 PostgreSQL 并创建专用数据库：

```sql
-- 以 postgres 用户身份登录
psql -U postgres

-- 创建数据库用户
CREATE USER workflow_user WITH PASSWORD 'your_secure_password';

-- 创建数据库
CREATE DATABASE workflow_db OWNER workflow_user;

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE workflow_db TO workflow_user;

-- 连接到新数据库
\c workflow_db

-- 授予 schema 权限
GRANT ALL ON SCHEMA public TO workflow_user;

-- 退出
\q
```

### 步骤 3: 配置环境变量

编辑 [`workflow_engine/.env`](workflow_engine/.env) 文件：

```bash
# PostgreSQL 配置（生产环境）
DATABASE_URL=postgresql://workflow_user:your_secure_password@localhost:5432/workflow_db

# 连接池配置（可选）
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# 其他配置保持不变
OPENAI_API_KEY=sk-d3e44466f96a43d4a4369b5f0310bb40
OPENAI_API_BASE=https://api.deepseek.com
OPENAI_MODEL_NAME=deepseek-chat
```

**重要提示：**
- 将 `your_secure_password` 替换为您设置的实际密码
- 如果 PostgreSQL 运行在不同的主机或端口，请相应修改连接字符串
- 生产环境务必使用强密码

### 步骤 4: 安装额外的 Python 依赖

虽然 `asyncpg` 已在 requirements.txt 中，但 Alembic 迁移需要同步驱动：

```bash
# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或 .venv\Scripts\activate  # Windows

# 安装 psycopg2（如果未安装）
pip install psycopg2-binary
```

## 🔄 数据库迁移

### 方法一：使用 Alembic 迁移（推荐）

#### 1. 初始化 Alembic（如果尚未初始化）

```bash
cd workflow_engine
alembic init alembic
```

#### 2. 配置 Alembic

编辑 `alembic/env.py`：

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入模型
from src.database.models import Base

config = context.config

# 从环境变量获取数据库 URL
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
```

编辑 `alembic.ini`：

```ini
# 找到 sqlalchemy.url 行并注释掉或删除
# sqlalchemy.url = driver://user:pass@localhost/dbname

# 添加版本存储配置
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
```

#### 3. 创建初始迁移

```bash
# 创建迁移脚本
alembic revision --autogenerate -m "Initial migration with all tables"

# 执行迁移
alembic upgrade head
```

### 方法二：直接创建表（快速开发环境）

如果不需要迁移历史，可以直接初始化：

```bash
cd workflow_engine
python -c "from src.database.connection import init_db; init_db()"
```

或使用提供的初始化脚本：

```bash
python scripts/init_postgres.py
```

### 方法三：从 SQLite 迁移数据

如果需要从现有 SQLite 迁移数据到 PostgreSQL：

#### 1. 导出 SQLite 数据

```bash
cd workflow_engine
python scripts/export_sqlite_data.py
```

这将在 `data/migration/` 目录生成 JSON 格式的导出数据。

#### 2. 导入到 PostgreSQL

```bash
# 确保 PostgreSQL 配置正确
python scripts/import_to_postgres.py
```

## ✅ 验证测试

### 验证数据库连接

运行数据库连接测试脚本：

```bash
cd workflow_engine
python test/test_db_connection.py
```

### 验证表结构

连接到 PostgreSQL 并检查表：

```bash
psql -U workflow_user -d workflow_db -c "\dt"
```

应该看到以下表：
- `workflows`
- `conversations`
- `memories`
- `audit_logs`

### 验证应用功能

运行测试套件：

```bash
cd workflow_engine
pytest test/test_agent_nodes.py -v
```

## 🔍 常见问题

### 问题 1: 连接被拒绝

**错误信息:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

**解决方案:**
1. 确认 PostgreSQL 服务正在运行：
   ```bash
   # macOS
   brew services list | grep postgresql
   
   # Linux
   sudo systemctl status postgresql
   ```

2. 检查 `pg_hba.conf` 配置允许本地连接
3. 验证用户名、密码和数据库名称正确

### 问题 2: 权限不足

**错误信息:**
```
permission denied for schema public
```

**解决方案:**
```sql
-- 以管理员身份连接
psql -U postgres -d workflow_db

-- 授予所有权限
GRANT ALL ON SCHEMA public TO workflow_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO workflow_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO workflow_user;

-- 设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO workflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO workflow_user;
```

### 问题 3: 连接池耗尽

**错误信息:**
```
QueuePool limit of size 10 overflow 20 reached
```

**解决方案:**
调整 `.env` 中的连接池参数：

```bash
DB_POOL_SIZE=20        # 增加连接池大小
DB_MAX_OVERFLOW=30     # 增加溢出连接数
```

或在 `connection.py` 中添加超时配置：

```python
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,  # 等待连接的超时时间
    pool_recycle=3600,  # 连接回收时间
    pool_pre_ping=True,
    echo=False
)
```

### 问题 4: Alembic 迁移冲突

**解决方案:**
```bash
# 查看当前版本
alembic current

# 标记当前数据库为最新版本
alembic stamp head

# 清理并重新生成迁移
alembic downgrade base
alembic upgrade head
```

## 📊 性能优化建议

### 1. 索引优化

数据库模型已包含必要索引，但可根据查询模式添加：

```sql
-- 为常用查询添加索引
CREATE INDEX idx_conversations_timestamp ON conversations(timestamp DESC);
CREATE INDEX idx_workflows_created_at ON workflows(created_at DESC);
```

### 2. 连接池配置

根据应用负载调整：

```bash
# 小型应用
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# 中型应用
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# 大型应用
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

### 3. PostgreSQL 配置优化

编辑 `postgresql.conf`：

```conf
# 内存配置
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB

# 连接配置
max_connections = 100

# 日志配置
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d.log'
```

## 🔐 安全建议

### 生产环境必做事项

1. **使用强密码**
   ```sql
   ALTER USER workflow_user WITH PASSWORD 'complex_secure_password_here';
   ```

2. **限制网络访问**
   - 配置 `pg_hba.conf` 只允许必要的连接
   - 使用 SSL/TLS 加密连接

3. **定期备份**
   ```bash
   # 自动备份脚本
   pg_dump -U workflow_user workflow_db > backup_$(date +%Y%m%d).sql
   ```

4. **监控和日志**
   - 启用 PostgreSQL 慢查询日志
   - 监控连接池使用情况

## 📚 相关文件

- 数据库模型定义: [`src/database/models.py`](src/database/models.py)
- 数据库连接管理: [`src/database/connection.py`](src/database/connection.py)
- 环境配置模板: [`.env.template`](.env.template)
- 初始化脚本: `scripts/init_postgres.py`
- 迁移脚本: `scripts/export_sqlite_data.py`, `scripts/import_to_postgres.py`

## 🆘 获取帮助

如果遇到问题：

1. 查看 PostgreSQL 日志: `/var/log/postgresql/` 或 `pg_log/`
2. 检查应用日志: `workflow_engine/logs/`
3. 运行诊断脚本: `python scripts/diagnose_db.py`
4. 查看连接状态: `python scripts/check_db_connection.py`

---

**注意:** 在生产环境部署前，请务必在测试环境完整测试迁移过程，并做好数据备份。