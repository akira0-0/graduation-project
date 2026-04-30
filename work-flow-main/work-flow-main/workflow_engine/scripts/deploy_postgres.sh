#!/bin/bash
# PostgreSQL Docker 快速部署脚本
# 用于一键部署 PostgreSQL 数据库

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查 Docker 是否安装
check_docker() {
    print_info "检查 Docker 安装..."
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker 已安装: $DOCKER_VERSION"
        return 0
    else
        print_error "Docker 未安装"
        print_info "请参考 DOCKER_INSTALL_GUIDE.md 安装 Docker"
        print_info "或访问: https://www.docker.com/products/docker-desktop"
        return 1
    fi
}

# 检查 Docker Compose 是否可用
check_docker_compose() {
    print_info "检查 Docker Compose..."
    
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version --short)
        print_success "Docker Compose 可用: $COMPOSE_VERSION"
        return 0
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        print_success "Docker Compose 可用: $COMPOSE_VERSION"
        return 0
    else
        print_error "Docker Compose 不可用"
        return 1
    fi
}

# 检查 Docker 服务是否运行
check_docker_running() {
    print_info "检查 Docker 服务状态..."
    
    if docker info &> /dev/null; then
        print_success "Docker 服务正在运行"
        return 0
    else
        print_error "Docker 服务未运行"
        print_info "请启动 Docker Desktop 或 Docker 服务"
        return 1
    fi
}

# 检查环境配置
check_env_config() {
    print_info "检查环境配置..."
    
    if [ -f ".env" ]; then
        print_success ".env 文件存在"
        
        if grep -q "postgresql://" .env; then
            print_success "PostgreSQL 配置已设置"
            return 0
        else
            print_warning "未找到 PostgreSQL 配置"
            print_info "请确保 .env 文件包含 DATABASE_URL=postgresql://..."
            return 1
        fi
    else
        print_warning ".env 文件不存在"
        print_info "正在从 .env.example 创建 .env..."
        cp .env.example .env
        print_success ".env 文件已创建"
        return 0
    fi
}

# 检查端口占用
check_port() {
    print_info "检查端口 5432..."
    
    if lsof -Pi :5432 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "端口 5432 已被占用"
        print_info "可能已有 PostgreSQL 实例在运行"
        
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
    else
        print_success "端口 5432 可用"
    fi
    return 0
}

# 启动 PostgreSQL 容器
start_postgres() {
    print_info "启动 PostgreSQL 容器..."
    
    # 使用 docker compose 或 docker-compose
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    $COMPOSE_CMD -f docker-compose.postgres.yml up -d
    
    print_success "PostgreSQL 容器已启动"
}

# 等待 PostgreSQL 就绪
wait_for_postgres() {
    print_info "等待 PostgreSQL 启动..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec workflow_postgres pg_isready -U workflow_user -d workflow_db >/dev/null 2>&1; then
            print_success "PostgreSQL 已就绪"
            return 0
        fi
        
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo
    print_error "PostgreSQL 启动超时"
    return 1
}

# 安装 Python 依赖
install_python_deps() {
    print_info "检查 Python 依赖..."
    
    # 检查是否在虚拟环境中
    if [ -n "$VIRTUAL_ENV" ]; then
        print_info "当前虚拟环境: $VIRTUAL_ENV"
    fi
    
    # 检查 psycopg2-binary
    if python3 -c "import psycopg2" 2>/dev/null; then
        print_success "psycopg2-binary 已安装"
    else
        print_info "安装 psycopg2-binary..."
        pip install psycopg2-binary
    fi
    
    # 检查 asyncpg
    if python3 -c "import asyncpg" 2>/dev/null; then
        print_success "asyncpg 已安装"
    else
        print_info "安装 asyncpg..."
        pip install asyncpg
    fi
    
    print_success "Python 依赖安装完成"
}

# 初始化数据库
init_database() {
    print_info "初始化数据库..."
    
    python3 scripts/init_postgres.py
    
    if [ $? -eq 0 ]; then
        print_success "数据库初始化完成"
        return 0
    else
        print_error "数据库初始化失败"
        return 1
    fi
}

# 验证数据库连接
verify_connection() {
    print_info "验证数据库连接..."
    
    python3 test/test_db_connection.py
    
    if [ $? -eq 0 ]; then
        print_success "数据库连接验证通过"
        return 0
    else
        print_error "数据库连接验证失败"
        return 1
    fi
}

# 显示部署信息
show_info() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}PostgreSQL 部署成功!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
    echo "数据库连接信息:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: workflow_db"
    echo "  User: workflow_user"
    echo "  Password: workflow_password"
    echo
    echo "连接字符串:"
    echo "  postgresql://workflow_user:workflow_password@localhost:5432/workflow_db"
    echo
    echo "常用命令:"
    echo "  查看状态: docker compose -f docker-compose.postgres.yml ps"
    echo "  查看日志: docker compose -f docker-compose.postgres.yml logs -f"
    echo "  停止服务: docker compose -f docker-compose.postgres.yml down"
    echo "  进入数据库: docker exec -it workflow_postgres psql -U workflow_user -d workflow_db"
    echo
    if [ "$WITH_PGADMIN" = true ]; then
        echo "pgAdmin 管理界面:"
        echo "  URL: http://localhost:5050"
        echo "  Email: admin@workflow.local"
        echo "  Password: admin123"
        echo
    fi
    echo -e "${BLUE}========================================${NC}"
}

# 主函数
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}PostgreSQL Docker 快速部署${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
    
    # 检查是否带 --with-pgadmin 参数
    if [ "$1" = "--with-pgadmin" ]; then
        WITH_PGADMIN=true
        print_info "将启动 pgAdmin 管理界面"
    else
        WITH_PGADMIN=false
    fi
    
    # 执行检查和部署步骤
    check_docker || exit 1
    check_docker_compose || exit 1
    check_docker_running || exit 1
    check_env_config || exit 1
    check_port || exit 1
    
    echo
    print_info "开始部署..."
    echo
    
    start_postgres || exit 1
    wait_for_postgres || exit 1
    
    # 如果启用 pgAdmin
    if [ "$WITH_PGADMIN" = true ]; then
        print_info "启动 pgAdmin..."
        docker compose -f docker-compose.postgres.yml --profile admin up -d
    fi
    
    echo
    install_python_deps || exit 1
    echo
    init_database || exit 1
    echo
    verify_connection || exit 1
    
    show_info
}

# 运行主函数
main "$@"