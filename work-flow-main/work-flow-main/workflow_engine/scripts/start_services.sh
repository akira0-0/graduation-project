#!/bin/bash
#
# 工作流引擎服务启动脚本
# 功能：统一管理后端和前端服务的启动/停止/重启
# 使用：./start_services.sh [命令] [选项]
#
# 命令：
#   start   - 启动所有服务
#   stop    - 停止所有服务
#   restart - 重启所有服务
#   status  - 查看服务状态
#   logs    - 查看服务日志
#
# 选项：
#   --backend-only  - 仅操作后端服务
#   --frontend-only - 仅操作前端服务
#

set -e

# ==================== 配置区域 ====================
# 端口配置
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}

# 目录配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKFLOW_ENGINE_DIR="${PROJECT_ROOT}/workflow_engine"
FRONTEND_DIR="${WORKFLOW_ENGINE_DIR}/frontend"
LOGS_DIR="${PROJECT_ROOT}/logs"
VENV_DIR="${PROJECT_ROOT}/.venv"

# 日志文件
BACKEND_LOG="${LOGS_DIR}/backend.log"
FRONTEND_LOG="${LOGS_DIR}/frontend.log"

# PID文件
BACKEND_PID_FILE="${LOGS_DIR}/backend.pid"
FRONTEND_PID_FILE="${LOGS_DIR}/frontend.pid"

# ==================== 工具函数 ====================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -i :$port -t >/dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口空闲
    fi
}

# 获取占用端口的PID
get_port_pid() {
    local port=$1
    lsof -i :$port -t 2>/dev/null | head -1
}

# 停止占用端口的进程
kill_port_process() {
    local port=$1
    local service_name=$2
    
    if check_port $port; then
        local pid=$(get_port_pid $port)
        if [ -n "$pid" ]; then
            log_warning "发现 $service_name 服务 (PID: $pid) 占用端口 $port，正在停止..."
            kill -9 $pid 2>/dev/null || true
            sleep 1
            
            # 确认是否已停止
            if check_port $port; then
                log_error "无法停止 $service_name 服务 (PID: $pid)"
                return 1
            else
                log_success "$service_name 服务已停止"
            fi
        fi
    else
        log_info "$service_name 服务未运行"
    fi
}

# 停止后端服务
stop_backend() {
    log_info "停止后端服务..."
    
    # 通过PID文件停止
    if [ -f "$BACKEND_PID_FILE" ]; then
        local pid=$(cat "$BACKEND_PID_FILE")
        if kill -0 $pid 2>/dev/null; then
            kill $pid 2>/dev/null || true
            sleep 1
            kill -9 $pid 2>/dev/null || true
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    
    # 通过端口停止
    kill_port_process $BACKEND_PORT "后端"
}

# 停止前端服务
stop_frontend() {
    log_info "停止前端服务..."
    
    # 通过PID文件停止
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local pid=$(cat "$FRONTEND_PID_FILE")
        if kill -0 $pid 2>/dev/null; then
            kill $pid 2>/dev/null || true
            sleep 1
            kill -9 $pid 2>/dev/null || true
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    # 通过端口停止
    kill_port_process $FRONTEND_PORT "前端"
}

# 启动后端服务
start_backend() {
    log_info "启动后端服务..."
    
    # 检查端口
    if check_port $BACKEND_PORT; then
        log_warning "后端端口 $BACKEND_PORT 已被占用"
        kill_port_process $BACKEND_PORT "后端"
    fi
    
    # 确保日志目录存在
    mkdir -p "$LOGS_DIR"
    
    # 激活虚拟环境并启动后端
    cd "$WORKFLOW_ENGINE_DIR"
    source "$VENV_DIR/bin/activate"
    
    nohup python -m uvicorn api.server:app --host 0.0.0.0 --port $BACKEND_PORT >> "$BACKEND_LOG" 2>&1 &
    local pid=$!
    echo $pid > "$BACKEND_PID_FILE"
    
    # 等待服务启动
    log_info "等待后端服务启动..."
    local max_wait=15
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -s "http://localhost:$BACKEND_PORT/docs" > /dev/null 2>&1; then
            log_success "后端服务启动成功 (PID: $pid, 端口: $BACKEND_PORT)"
            log_info "API文档: http://localhost:$BACKEND_PORT/docs"
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    
    log_error "后端服务启动超时，请检查日志: $BACKEND_LOG"
    return 1
}

# 启动前端服务
start_frontend() {
    log_info "启动前端服务..."
    
    # 检查端口
    if check_port $FRONTEND_PORT; then
        log_warning "前端端口 $FRONTEND_PORT 已被占用"
        kill_port_process $FRONTEND_PORT "前端"
    fi
    
    # 确保日志目录存在
    mkdir -p "$LOGS_DIR"
    
    # 启动前端
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --port $FRONTEND_PORT >> "$FRONTEND_LOG" 2>&1 &
    local pid=$!
    echo $pid > "$FRONTEND_PID_FILE"
    
    # 等待服务启动
    log_info "等待前端服务启动..."
    local max_wait=15
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
            log_success "前端服务启动成功 (PID: $pid, 端口: $FRONTEND_PORT)"
            log_info "前端地址: http://localhost:$FRONTEND_PORT"
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    
    log_error "前端服务启动超时，请检查日志: $FRONTEND_LOG"
    return 1
}

# 显示服务状态
show_status() {
    echo ""
    echo "=========================================="
    echo "           工作流引擎服务状态"
    echo "=========================================="
    echo ""
    
    # 后端状态
    echo -e "${BLUE}[后端服务]${NC}"
    if check_port $BACKEND_PORT; then
        local pid=$(get_port_pid $BACKEND_PORT)
        echo -e "  状态: ${GREEN}运行中${NC}"
        echo -e "  PID: $pid"
        echo -e "  端口: $BACKEND_PORT"
        echo -e "  地址: http://localhost:$BACKEND_PORT"
        echo -e "  文档: http://localhost:$BACKEND_PORT/docs"
    else
        echo -e "  状态: ${RED}未运行${NC}"
    fi
    echo ""
    
    # 前端状态
    echo -e "${BLUE}[前端服务]${NC}"
    if check_port $FRONTEND_PORT; then
        local pid=$(get_port_pid $FRONTEND_PORT)
        echo -e "  状态: ${GREEN}运行中${NC}"
        echo -e "  PID: $pid"
        echo -e "  端口: $FRONTEND_PORT"
        echo -e "  地址: http://localhost:$FRONTEND_PORT"
    else
        echo -e "  状态: ${RED}未运行${NC}"
    fi
    echo ""
    
    # 日志文件
    echo -e "${BLUE}[日志文件]${NC}"
    echo -e "  后端日志: $BACKEND_LOG"
    echo -e "  前端日志: $FRONTEND_LOG"
    echo ""
    echo "=========================================="
}

# 查看日志
show_logs() {
    local service=$1
    
    case $service in
        backend|b)
            log_info "后端服务日志 (Ctrl+C 退出):"
            tail -f "$BACKEND_LOG"
            ;;
        frontend|f)
            log_info "前端服务日志 (Ctrl+C 退出):"
            tail -f "$FRONTEND_LOG"
            ;;
        all|*)
            log_info "所有服务日志 (Ctrl+C 退出):"
            tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
            ;;
    esac
}

# 清理所有残留进程
cleanup_all() {
    log_warning "清理所有残留进程..."
    
    # 清理后端相关进程
    pkill -f "uvicorn.*:$BACKEND_PORT" 2>/dev/null || true
    pkill -f "api.server:app" 2>/dev/null || true
    
    # 清理前端相关进程
    pkill -f "vite.*:$FRONTEND_PORT" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    
    # 等待进程结束
    sleep 2
    
    # 通过端口再次确认
    kill_port_process $BACKEND_PORT "后端" 2>/dev/null || true
    kill_port_process $FRONTEND_PORT "前端" 2>/dev/null || true
    
    # 删除PID文件
    rm -f "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"
    
    log_success "清理完成"
}

# ==================== 主逻辑 ====================

# 解析命令
COMMAND=${1:-"status"}
OPTION=${2:-""}

# 确定操作范围
BACKEND_ONLY=false
FRONTEND_ONLY=false

case $OPTION in
    --backend-only|-b)
        BACKEND_ONLY=true
        ;;
    --frontend-only|-f)
        FRONTEND_ONLY=true
        ;;
esac

# 执行命令
case $COMMAND in
    start)
        if [ "$FRONTEND_ONLY" = "false" ]; then
            start_backend || exit 1
        fi
        if [ "$BACKEND_ONLY" = "false" ]; then
            start_frontend || exit 1
        fi
        show_status
        ;;
    
    stop)
        if [ "$FRONTEND_ONLY" = "false" ]; then
            stop_backend
        fi
        if [ "$BACKEND_ONLY" = "false" ]; then
            stop_frontend
        fi
        show_status
        ;;
    
    restart)
        log_info "重启所有服务..."
        if [ "$FRONTEND_ONLY" = "false" ]; then
            stop_backend
        fi
        if [ "$BACKEND_ONLY" = "false" ]; then
            stop_frontend
        fi
        sleep 1
        if [ "$FRONTEND_ONLY" = "false" ]; then
            start_backend || exit 1
        fi
        if [ "$BACKEND_ONLY" = "false" ]; then
            start_frontend || exit 1
        fi
        show_status
        ;;
    
    status)
        show_status
        ;;
    
    logs)
        show_logs "$OPTION"
        ;;
    
    cleanup)
        cleanup_all
        show_status
        ;;
    
    *)
        echo "用法: $0 {start|stop|restart|status|logs|cleanup} [--backend-only|--frontend-only]"
        echo ""
        echo "命令:"
        echo "  start   - 启动所有服务"
        echo "  stop    - 停止所有服务"
        echo "  restart - 重启所有服务"
        echo "  status  - 查看服务状态"
        echo "  logs    - 查看服务日志 (可选: backend/frontend)"
        echo "  cleanup - 清理所有残留进程"
        echo ""
        echo "选项:"
        echo "  --backend-only, -b  - 仅操作后端服务"
        echo "  --frontend-only, -f - 仅操作前端服务"
        echo ""
        echo "环境变量:"
        echo "  BACKEND_PORT  - 后端端口 (默认: 8000)"
        echo "  FRONTEND_PORT - 前端端口 (默认: 5173)"
        exit 1
        ;;
esac