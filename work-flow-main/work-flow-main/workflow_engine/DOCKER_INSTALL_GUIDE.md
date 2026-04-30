# Docker 安装指南与 PostgreSQL 部署

本文档提供详细的 Docker 安装步骤和 PostgreSQL 数据库部署指南。

## 📦 Docker 安装

### macOS 安装 Docker Desktop

#### 方法 1: 官方安装包（推荐）

1. **下载 Docker Desktop**
   - 访问官网: https://www.docker.com/products/docker-desktop
   - 下载 macOS 版本（支持 Intel 和 Apple Silicon）

2. **安装步骤**
   ```bash
   # 双击下载的 Docker.dmg 文件
   # 将 Docker 拖拽到 Applications 文件夹
   # 打开 Applications 中的 Docker
   ```

3. **验证安装**
   ```bash
   docker --version
   docker compose version
   ```

#### 方法 2: 使用 Homebrew 安装

```bash
# 安装 Docker Desktop
brew install --cask docker

# 或安装 Docker Engine（命令行版本）
brew install docker docker-compose

# 启动 Docker 服务（如果安装的是 Engine）
brew services start docker
```

### 验证 Docker 安装

安装完成后，运行以下命令验证:

```bash
# 检查 Docker 版本
docker --version

# 检查 Docker Compose 版本
docker compose version

# 运行测试容器
docker run hello-world
```

如果看到 "Hello from Docker!" 消息，说明安装成功。

## 🚀 使用 Docker 部署 PostgreSQL

### 步骤 1: 配置环境变量

创建或编辑 `.env` 文件:

```bash
cd workflow_engine
cp .env.example .env
```

编辑 `.env` 文件，配置 PostgreSQL 连接:

```bash
# PostgreSQL 连接配置
DATABASE_URL=postgresql://workflow_user:workflow_password@localhost:5432/workflow_db

# Docker PostgreSQL 环境变量
POSTGRES_USER=workflow_user
POSTGRES_PASSWORD=workflow_password
POSTGRES_DB=workflow_db
POSTGRES_PORT=5432
```

### 步骤 2: 启动 PostgreSQL 容器

#### 基础启动（仅 PostgreSQL）

```bash
# 在 workflow_engine 目录下执行
docker compose -f docker-compose.postgres.yml up -d
```

#### 启动 PostgreSQL + pgAdmin 管理界面

```bash
# 启动包含 pgAdmin 的完整服务
docker compose -f docker-compose.postgres.yml --profile admin up -d
```

#### 查看容器状态

```bash
# 查看运行中的容器
docker compose -f docker-compose.postgres.yml ps

# 查看容器日志
docker compose -f docker-compose.postgres.yml logs -f postgres

# 查看 pgAdmin 日志
docker compose -f docker-compose.postgres.yml logs -f pgadmin
```

### 步骤 3: 验证 PostgreSQL 运行状态

```bash
# 检查容器健康状态
docker compose -f docker-compose.postgres.yml ps

# 应该看到类似输出:
# NAME                  STATUS
# workflow_postgres     Up (healthy)
```

#### 使用 psql 连接测试

```bash
# 进入 PostgreSQL 容器
docker exec -it workflow_postgres psql -U workflow_user -d workflow_db

# 在 psql 中执行
\dt        # 列出所有表
\q         # 退出
```

### 步骤 4: 安装 Python 依赖

确保安装了 PostgreSQL Python 驱动:

```bash
# 激活虚拟环境（如果有）
source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install psycopg2-binary asyncpg
```

### 步骤 5: 初始化数据库

#### 方法 1: 使用初始化脚本（推荐）

```bash
cd workflow_engine
python scripts/init_postgres.py
```

#### 方法 2: 使用 Alembic 迁移

```bash
cd workflow_engine

# 创建初始迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

### 步骤 6: 验证数据库连接

```bash
cd workflow_engine
python test/test_db_connection.py
```

## 🔧 常用 Docker 命令

### 容器管理

```bash
# 启动服务
docker compose -f docker-compose.postgres.yml up -d

# 停止服务
docker compose -f docker-compose.postgres.yml down

# 重启服务
docker compose -f docker-compose.postgres.yml restart

# 停止并删除数据卷（清理所有数据）
docker compose -f docker-compose.postgres.yml down -v

# 查看日志
docker compose -f docker-compose.postgres.yml logs -f

# 进入容器 shell
docker exec -it workflow_postgres bash
```

### 数据库操作

```bash
# 备份数据库
docker exec workflow_postgres pg_dump -U workflow_user workflow_db > backup.sql

# 恢复数据库
docker exec -i workflow_postgres psql -U workflow_user workflow_db < backup.sql

# 查看数据库大小
docker exec workflow_postgres psql -U workflow_user -d workflow_db -c "SELECT pg_size_pretty(pg_database_size('workflow_db'));"

# 查看连接数
docker exec workflow_postgres psql -U workflow_user -d workflow_db -c "SELECT count(*) FROM pg_stat_activity;"
```

## 🌐 pgAdmin 使用（可选）

如果启动了 pgAdmin 服务，可以通过 Web 界面管理数据库:

### 访问 pgAdmin

1. 打开浏览器访问: http://localhost:5050
2. 登录凭据（默认）:
   - Email: `admin@workflow.local`
   - Password: `admin123`

### 添加服务器连接

1. 点击 "Add New Server"
2. General 标签:
   - Name: `Workflow DB`
3. Connection 标签:
   - Host: `postgres` (Docker 网络中的服务名)
   - Port: `5432`
   - Database: `workflow_db`
   - Username: `workflow_user`
   - Password: `workflow_password`

## 🔍 故障排查

### 问题 1: 容器无法启动

```bash
# 检查容器日志
docker compose -f docker-compose.postgres.yml logs postgres

# 检查端口占用
lsof -i :5432

# 停止所有容器并重新启动
docker compose -f docker-compose.postgres.yml down
docker compose -f docker-compose.postgres.yml up -d
```

### 问题 2: 无法连接到数据库

```bash
# 检查容器是否在运行
docker compose -f docker-compose.postgres.yml ps

# 检查网络连接
docker exec workflow_postgres ping -c 3 localhost

# 检查 PostgreSQL 是否监听
docker exec workflow_postgres netstat -tulpn | grep 5432
```

### 问题 3: 权限问题

```bash
# 重置权限
docker exec -it workflow_postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE workflow_db TO workflow_user;"
docker exec -it workflow_postgres psql -U postgres -d workflow_db -c "GRANT ALL ON SCHEMA public TO workflow_user;"
```

### 问题 4: 数据持久化

数据存储在 Docker 卷中，查看卷信息:

```bash
# 列出所有卷
docker volume ls

# 查看卷详情
docker volume inspect workflow_engine_postgres_data

# 备份卷数据
docker run --rm -v workflow_engine_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## 📝 完整部署流程

以下是从零开始的完整部署流程:

```bash
# 1. 安装 Docker Desktop（如果未安装）
# 下载: https://www.docker.com/products/docker-desktop

# 2. 验证 Docker 安装
docker --version

# 3. 进入项目目录
cd workflow_engine

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库配置

# 5. 启动 PostgreSQL 容器
docker compose -f docker-compose.postgres.yml up -d

# 6. 等待容器健康检查完成（约 10-15 秒）
docker compose -f docker-compose.postgres.yml ps

# 7. 安装 Python 依赖
pip install psycopg2-binary asyncpg

# 8. 初始化数据库
python scripts/init_postgres.py

# 9. 验证数据库连接
python test/test_db_connection.py

# 10. (可选) 启动 pgAdmin
docker compose -f docker-compose.postgres.yml --profile admin up -d
```

## 🎯 快速命令参考

```bash
# 启动
docker compose -f docker-compose.postgres.yml up -d

# 停止
docker compose -f docker-compose.postgres.yml down

# 查看状态
docker compose -f docker-compose.postgres.yml ps

# 查看日志
docker compose -f docker-compose.postgres.yml logs -f

# 重启
docker compose -f docker-compose.postgres.yml restart

# 完全清理（包括数据）
docker compose -f docker-compose.postgres.yml down -v

# 进入数据库
docker exec -it workflow_postgres psql -U workflow_user -d workflow_db

# 初始化数据库
python scripts/init_postgres.py

# 测试连接
python test/test_db_connection.py
```

## 📚 相关文档

- [Docker 官方文档](https://docs.docker.com/)
- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [pgAdmin 文档](https://www.pgadmin.org/docs/)
- [项目迁移指南](POSTGRESQL_MIGRATION.md)

## ⚠️ 注意事项

1. **生产环境安全**
   - 修改默认密码
   - 配置防火墙规则
   - 使用 SSL/TLS 加密连接
   - 定期备份数据

2. **资源限制**
   - Docker Compose 已配置资源限制（2GB 内存，2 CPU）
   - 根据实际需求调整 `docker-compose.postgres.yml`

3. **数据备份**
   - 定期备份 PostgreSQL 数据
   - 使用 `docker exec` 导出数据库
   - 考虑使用 Docker 卷备份

4. **版本兼容性**
   - Docker Desktop: 最新稳定版本
   - PostgreSQL: 15.x（推荐）
   - Python: 3.8+

---

**安装 Docker 后，请重新打开终端窗口，然后按照上述步骤部署 PostgreSQL。**