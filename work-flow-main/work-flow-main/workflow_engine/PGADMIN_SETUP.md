# pgAdmin 配置指南

pgAdmin 是 PostgreSQL 的图形化管理工具。本文档提供两种配置方式。

## 方式一: Docker 部署 (推荐)

### 前提条件
- Docker Desktop 已安装并运行
- PostgreSQL 容器已启动

### 启动 pgAdmin

#### 选项 1: 使用 Docker Compose (推荐)

```bash
# 启动 PostgreSQL 和 pgAdmin 服务
docker-compose -f docker-compose.postgres.yml --profile admin up -d

# 或者仅启动 pgAdmin (PostgreSQL 已运行)
docker-compose -f docker-compose.postgres.yml --profile admin up -d pgadmin
```

#### 选项 2: 手动启动 pgAdmin 容器

如果 Docker Hub 连接超时,可以尝试使用国内镜像:

```bash
# 使用阿里云镜像
docker pull registry.cn-hangzhou.aliyuncs.com/dpage/pgadmin4:latest
docker tag registry.cn-hangzhou.aliyuncs.com/dpage/pgadmin4:latest dpage/pgadmin4:latest

# 启动容器
docker run -d \
  --name workflow_pgadmin \
  --network workflow_engine_workflow_network \
  -e PGADMIN_DEFAULT_EMAIL=admin@workflow.local \
  -e PGADMIN_DEFAULT_PASSWORD=admin123 \
  -e PGADMIN_LISTEN_PORT=5050 \
  -p 5050:5050 \
  -v workflow_engine_pgadmin_data:/var/lib/pgadmin \
  dpage/pgadmin4:latest
```

### 访问 pgAdmin

1. 打开浏览器访问: http://localhost:5050
2. 登录凭据:
   - 邮箱: `admin@workflow.local`
   - 密码: `admin123`

### 配置数据库连接

1. 登录后,右键点击 "Servers" → "Register" → "Server"
2. 在 "General" 标签页:
   - Name: `Workflow Database`
3. 在 "Connection" 标签页:
   - Host name/address: `postgres` (使用 Docker 网络)
   - Port: `5432`
   - Maintenance database: `workflow_db`
   - Username: `workflow_user`
   - Password: `workflow_password`
4. 点击 "Save" 保存连接

## 方式二: 本地安装 pgAdmin

### macOS

```bash
# 使用 Homebrew 安装
brew install --cask pgadmin4

# 或下载安装包
# https://www.pgadmin.org/download/pgadmin-4-macos/
```

### Windows

下载并安装: https://www.pgadmin.org/download/pgadmin-4-windows/

### Linux

```bash
# Ubuntu/Debian
sudo apt-get install pgadmin4

# CentOS/RHEL
sudo yum install pgadmin4
```

### 配置本地 pgAdmin 连接

安装后打开 pgAdmin,配置连接:
- Host: `localhost`
- Port: `5432`
- Database: `workflow_db`
- Username: `workflow_user`
- Password: `workflow_password`

## 方式三: 使用命令行工具

如果 pgAdmin 暂时无法使用,可以使用命令行工具管理数据库:

```bash
# 连接到 PostgreSQL
docker exec -it workflow_postgres psql -U workflow_user -d workflow_db

# 或使用本地 psql
psql -h localhost -U workflow_user -d workflow_db

# 常用命令
\l          # 列出所有数据库
\dt         # 列出所有表
\d table_name   # 查看表结构
\q          # 退出
```

## 方式四: 使用其他数据库管理工具

### DBeaver (免费,跨平台)
- 下载: https://dbeaver.io/download/
- 支持 PostgreSQL 和其他数据库
- 功能强大,界面友好

### DataGrip (JetBrains,付费)
- 包含在 JetBrains IDE 中
- 专业数据库管理工具

### TablePlus (macOS/Windows)
- 现代化的数据库管理工具
- 免费版功能已足够

## 故障排查

### Docker Hub 连接超时

如果遇到 `EOF` 或连接超时错误:

1. **配置 Docker 镜像加速器**
   - 打开 Docker Desktop
   - Settings → Docker Engine
   - 添加镜像加速器配置:

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ]
}
```

2. **重试拉取镜像**
```bash
docker pull dpage/pgadmin4:latest
```

3. **使用本地安装** (推荐)
   - 安装本地 pgAdmin 客户端
   - 连接到 localhost:5432

### pgAdmin 无法连接到 PostgreSQL

如果 pgAdmin 容器无法连接到 PostgreSQL:

1. 检查网络配置:
```bash
docker network ls
docker network inspect workflow_engine_workflow_network
```

2. 确保两个容器在同一网络:
```bash
docker ps
# 应该看到 workflow_postgres 和 workflow_pgadmin 都在运行
```

3. 使用正确的连接信息:
   - Host: `postgres` (不是 localhost!)
   - 这是因为 pgAdmin 和 PostgreSQL 在同一个 Docker 网络中

### 端口冲突

如果 5050 端口被占用:

```bash
# 查看端口占用
lsof -i :5050

# 修改 docker-compose.postgres.yml 中的端口映射
# 将 "5050:5050" 改为 "8080:5050" 或其他端口
```

## 推荐方案

由于 Docker Hub 连接问题,推荐使用以下方式之一:

1. **最快方案**: 安装本地 pgAdmin 客户端
   - macOS: `brew install --cask pgadmin4`
   - Windows: 下载安装包
   - 连接到 localhost:5432

2. **备选方案**: 使用 DBeaver
   - 免费且功能强大
   - 支持多种数据库
   - 安装简单

3. **命令行方案**: 使用 psql
   - 已包含在 PostgreSQL 容器中
   - `docker exec -it workflow_postgres psql -U workflow_user -d workflow_db`

## 数据库管理最佳实践

无论使用哪种工具,都建议:

1. **定期备份**
```bash
# 备份数据库
docker exec workflow_postgres pg_dump -U workflow_user workflow_db > backup.sql

# 恢复数据库
docker exec -i workflow_postgres psql -U workflow_user workflow_db < backup.sql
```

2. **监控性能**
   - 使用 pgAdmin 的仪表板功能
   - 检查慢查询
   - 监控连接数

3. **安全管理**
   - 修改默认密码
   - 限制网络访问
   - 定期更新