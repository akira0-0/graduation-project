"""
依赖注入配置
提供 FastAPI 的依赖注入工厂函数
"""
from functools import lru_cache
from typing import Generator, Optional
from sqlalchemy.orm import Session

# 配置管理
from workflow_engine.src.config import get_settings, get_llm_settings

# 数据库连接
from workflow_engine.src.database.connection import SessionLocal, get_db as _get_db

# Repository
from workflow_engine.src.database.repositories import (
    WorkflowRepository,
    ConversationRepository,
    MemoryRepository,
    AuditLogRepository,
    ExecutionRepository
)

# Service
from workflow_engine.src.services import (
    PlannerService,
    WorkflowService,
    ExecutionService,
    AgentService
)


# ==================== 数据库依赖 ====================

def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（用于 FastAPI 依赖注入）
    
    Yields:
        Session: 数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== Repository 依赖 ====================

def get_workflow_repo(db: Session = None) -> WorkflowRepository:
    """
    获取工作流仓储
    
    Args:
        db: 数据库会话（可选，如果不提供则自动创建）
        
    Returns:
        WorkflowRepository: 工作流仓储实例
    """
    if db is None:
        db = SessionLocal()
    return WorkflowRepository(db)


def get_conversation_repo(db: Session = None) -> ConversationRepository:
    """
    获取对话仓储
    
    Args:
        db: 数据库会话（可选，如果不提供则自动创建）
        
    Returns:
        ConversationRepository: 对话仓储实例
    """
    if db is None:
        db = SessionLocal()
    return ConversationRepository(db)


def get_memory_repo(db: Session = None) -> MemoryRepository:
    """
    获取记忆仓储
    
    Args:
        db: 数据库会话（可选，如果不提供则自动创建）
        
    Returns:
        MemoryRepository: 记忆仓储实例
    """
    if db is None:
        db = SessionLocal()
    return MemoryRepository(db)


def get_audit_log_repo(db: Session = None) -> AuditLogRepository:
    """
    获取审计日志仓储
    
    Args:
        db: 数据库会话（可选，如果不提供则自动创建）
        
    Returns:
        AuditLogRepository: 审计日志仓储实例
    """
    if db is None:
        db = SessionLocal()
    return AuditLogRepository(db)


def get_execution_repo(db: Session = None) -> ExecutionRepository:
    """
    获取执行记录仓储
    
    Args:
        db: 数据库会话（可选，如果不提供则自动创建）
        
    Returns:
        ExecutionRepository: 执行记录仓储实例
    """
    if db is None:
        db = SessionLocal()
    return ExecutionRepository(db)


# ==================== Service 依赖 ====================

@lru_cache()
def get_planner_service() -> PlannerService:
    """
    获取规划服务（单例模式）
    
    Returns:
        PlannerService: 规划服务实例
    """
    # 使用统一配置管理
    settings = get_settings()
    return PlannerService(model_name=settings.llm_model)


def get_workflow_service(
    db: Session = None,
    planner_service: PlannerService = None
) -> WorkflowService:
    """
    获取工作流服务
    
    Args:
        db: 数据库会话（可选）
        planner_service: 规划服务（可选）
        
    Returns:
        WorkflowService: 工作流服务实例
    """
    workflow_repo = get_workflow_repo(db)
    conversation_repo = get_conversation_repo(db) if db else None
    
    if planner_service is None:
        planner_service = get_planner_service()
    
    return WorkflowService(
        workflow_repo=workflow_repo,
        conversation_repo=conversation_repo,
        planner_service=planner_service
    )


def get_execution_service(
    db: Session = None
) -> ExecutionService:
    """
    获取执行服务
    
    Args:
        db: 数据库会话（可选）
        
    Returns:
        ExecutionService: 执行服务实例
    """
    workflow_repo = get_workflow_repo(db) if db else None
    audit_log_repo = get_audit_log_repo(db) if db else None
    execution_repo = get_execution_repo(db) if db else None
    
    return ExecutionService(
        workflow_repo=workflow_repo,
        audit_log_repo=audit_log_repo,
        execution_repo=execution_repo
    )


def get_agent_service(
    db: Session = None,
    planner_service: PlannerService = None
) -> AgentService:
    """
    获取智能体服务
    
    Args:
        db: 数据库会话（可选）
        planner_service: 规划服务（可选）
        
    Returns:
        AgentService: 智能体服务实例
    """
    memory_repo = get_memory_repo(db) if db else None
    
    if planner_service is None:
        planner_service = get_planner_service()
    
    return AgentService(
        memory_repo=memory_repo,
        planner_service=planner_service
    )


# ==================== FastAPI Depends 函数 ====================

from fastapi import Depends

def get_workflow_service_dep(
    db: Session = Depends(get_db),
    planner_service: PlannerService = Depends(get_planner_service)
) -> WorkflowService:
    """
    FastAPI 依赖注入：获取工作流服务
    
    用法:
        @app.post("/workflows")
        async def create_workflow(
            service: WorkflowService = Depends(get_workflow_service_dep)
        ):
            ...
    """
    return get_workflow_service(db, planner_service)


def get_execution_service_dep(
    db: Session = Depends(get_db)
) -> ExecutionService:
    """
    FastAPI 依赖注入：获取执行服务
    """
    return get_execution_service(db)


def get_agent_service_dep(
    db: Session = Depends(get_db),
    planner_service: PlannerService = Depends(get_planner_service)
) -> AgentService:
    """
    FastAPI 依赖注入：获取智能体服务
    """
    return get_agent_service(db, planner_service)


# ==================== 无数据库的服务工厂 ====================

def get_workflow_service_no_db() -> WorkflowService:
    """
    获取不依赖数据库的工作流服务（仅用于生成工作流，不保存）
    
    Returns:
        WorkflowService: 工作流服务实例
    """
    return WorkflowService(
        workflow_repo=None,
        conversation_repo=None,
        planner_service=get_planner_service()
    )


def get_execution_service_no_db() -> ExecutionService:
    """
    获取不依赖数据库的执行服务（仅用于执行工作流，不记录日志）
    
    Returns:
        ExecutionService: 执行服务实例
    """
    return ExecutionService(
        workflow_repo=None,
        audit_log_repo=None
    )


def get_agent_service_no_db() -> AgentService:
    """
    获取不依赖数据库的智能体服务（仅用于获取模板）
    
    Returns:
        AgentService: 智能体服务实例
    """
    return AgentService(
        memory_repo=None,
        planner_service=get_planner_service()
    )