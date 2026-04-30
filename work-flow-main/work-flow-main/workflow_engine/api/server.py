"""
工作流引擎 API 服务器
提供工作流生成和执行的 HTTP 接口

重构说明：
- 采用三层架构：接口层(API) -> 业务服务层(Service) -> 数据层(Repository)
- 使用依赖注入模式，支持测试和灵活配置
- 保持现有 API 接口不变，向后兼容
"""
import os
import sys
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# 添加项目根目录到 sys.path 以解决 workflow_engine 导入问题
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, project_root)

env_path = os.path.join(project_root, "workflow_engine", ".env")
load_dotenv(env_path, override=True)

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# API 模型
from workflow_engine.api.models import (
    GenerateRequest, GenerateResponse,
    ExecuteRequest, ExecuteResponse,
    ErrorResponse, PublicOpinionRequest, PublicOpinionResponse,
    AgentTemplateResponse,
    StartConversationRequest, ConversationMessageRequest,
    ConversationResponse, ConversationHistoryResponse,
    WorkflowImprovementResponse,
    ExecutionRunResponse, ExecutionListResponse, ExecutionReportResponse,
    WorkflowCreateRequest, WorkflowCreateResponse
)

# 依赖注入
from workflow_engine.api.dependencies import (
    get_db,
    get_planner_service,
    get_workflow_service_dep,
    get_execution_service_dep,
    get_agent_service_dep,
    get_workflow_service_no_db,
    get_execution_service_no_db,
    get_agent_service_no_db
)

# Service 层
from workflow_engine.src.services import (
    PlannerService,
    WorkflowService,
    ExecutionService,
    AgentService
)
from workflow_engine.src.services.ai_conversation_service import AIConversationService
from workflow_engine.src.services.workflow_service import (
    WorkflowSaveError,
    ERROR_CODE_WORKFLOW_SAVE_FAILED
)
from workflow_engine.src.utils.logger import get_logger

# 核心组件（仅用于向后兼容的无数据库模式）
from workflow_engine.src.planner.llm_planner import (
    LLMPlanner,
    WorkflowJSONProcessingError
)
from workflow_engine.src.planner.enhanced_planner import EnhancedLLMPlanner
from workflow_engine.src.core.builder import GraphBuilder
from workflow_engine.src.monitoring import ExecutionMonitor

import uvicorn
from dotenv import load_dotenv

# 加载环境变量
env_path = os.path.join(project_root, "workflow_engine", ".env")
load_dotenv(env_path, override=True)

# 创建 FastAPI 应用
app = FastAPI(
    title="工作流引擎 API",
    description="使用 LLM 生成和管理工作流的 API",
    version="2.1.0"
)

logger = get_logger("api_server")

ERROR_CODE_INVALID_LLM_WORKFLOW_JSON = "INVALID_LLM_WORKFLOW_JSON"
ERROR_CODE_WORKFLOW_GENERATION_FAILED = "WORKFLOW_GENERATION_FAILED"
ERROR_CODE_CONVERSATION_NOT_FOUND = "CONVERSATION_NOT_FOUND"
ERROR_CODE_CONVERSATION_FAILED = "CONVERSATION_FAILED"
ERROR_CODE_WORKFLOW_EXECUTION_FAILED = "WORKFLOW_EXECUTION_FAILED"
ERROR_CODE_EXECUTION_NOT_FOUND = "EXECUTION_NOT_FOUND"
ERROR_CODE_EXECUTION_QUERY_FAILED = "EXECUTION_QUERY_FAILED"
ERROR_CODE_EXECUTION_REPORT_NOT_FOUND = "EXECUTION_REPORT_NOT_FOUND"


def _get_request_context(request: Optional[Request]) -> dict:
    if request is None:
        return {"request_id": None, "conversation_id": None}
    request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
    conversation_id = request.headers.get("X-Conversation-ID")
    return {"request_id": request_id, "conversation_id": conversation_id}


def _build_error_payload(
    code: str,
    message: str,
    details: Optional[dict] = None
) -> dict:
    return {
        "code": code,
        "message": message,
        "details": details or {}
    }


def _build_exception_details(
    exception: Exception,
    stage: str,
    include_traceback: bool = True,
    extra_details: Optional[dict] = None
) -> dict:
    details = {
        "error_type": type(exception).__name__,
        "error_summary": str(exception),
        "stage": stage,
        "timestamp": datetime.now().isoformat()
    }

    if include_traceback:
        import traceback
        details["traceback"] = traceback.format_exc()

    if extra_details:
        details.update(extra_details)

    return details


# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5181",
        "http://127.0.0.1:5181",
        "http://localhost:5182",
        "http://127.0.0.1:5182",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 根路径和健康检查 ====================

@app.get("/")
async def root():
    """根路径，返回欢迎信息"""
    return {
        "message": "欢迎使用工作流引擎 API",
        "documentation": "/docs",
        "version": "2.1.0",
        "architecture": "三层架构 (API -> Service -> Repository)"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }


# ==================== 工作流生成 API ====================

@app.post("/api/v1/workflows/generate", response_model=GenerateResponse, responses={500: {"model": ErrorResponse}})
async def generate_workflow(
    request: GenerateRequest,
    planner_service: PlannerService = Depends(get_planner_service)
):
    """
    根据自然语言意图生成工作流定义
    
    Args:
        request: 生成请求，包含用户意图和模型配置
        planner_service: 规划服务（依赖注入）
        
    Returns:
        生成的工作流定义
    """
    try:
        # 使用规划服务生成工作流
        workflow_def = planner_service.generate_workflow(
            intent=request.intent,
            model=request.model
        )
        
        return GenerateResponse(
            workflow=workflow_def,
            status="success",
            metadata={
                "model": request.model,
                "intent_length": len(request.intent),
                "node_count": len(workflow_def.nodes),
                "edge_count": len(workflow_def.edges)
            }
        )
    except WorkflowJSONProcessingError as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_INVALID_LLM_WORKFLOW_JSON,
                message="LLM 返回的工作流 JSON 无效",
                details=_build_exception_details(
                    exception=e,
                    stage="generate_workflow",
                    extra_details={"llm_stage": e.stage}
                )
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_WORKFLOW_GENERATION_FAILED,
                message="生成工作流失败",
                details=_build_exception_details(
                    exception=e,
                    stage="generate_workflow"
                )
            )
        )


@app.post("/api/v1/workflows/generate-public-opinion",
          response_model=PublicOpinionResponse,
          responses={500: {"model": ErrorResponse}})
async def generate_public_opinion_workflow(
    request: PublicOpinionRequest,
    planner_service: PlannerService = Depends(get_planner_service)
):
    """
    根据主题生成舆论分析工作流
    
    自动创建包含数据收集、过滤、情感分析、报告生成的完整工作流
    
    Args:
        request: 舆论分析请求，包含主题和可选的需求配置
        planner_service: 规划服务（依赖注入）
        
    Returns:
        生成的舆论分析工作流定义
    """
    try:
        # 使用规划服务生成舆论分析工作流
        workflow_def = planner_service.generate_public_opinion_workflow(
            topic=request.topic,
            requirements=request.requirements,
            model=request.model
        )
        
        return PublicOpinionResponse(
            workflow=workflow_def,
            status="success",
            metadata={
                "model": request.model,
                "topic": request.topic,
                "workflow_type": "public_opinion_analysis",
                "node_count": len(workflow_def.nodes),
                "edge_count": len(workflow_def.edges)
            }
        )
    except WorkflowJSONProcessingError as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_INVALID_LLM_WORKFLOW_JSON,
                message="LLM 返回的工作流 JSON 无效",
                details=_build_exception_details(
                    exception=e,
                    stage="generate_public_opinion_workflow",
                    extra_details={"llm_stage": e.stage}
                )
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_WORKFLOW_GENERATION_FAILED,
                message="生成舆情工作流失败",
                details=_build_exception_details(
                    exception=e,
                    stage="generate_public_opinion_workflow"
                )
            )
        )


# ==================== 工作流执行 API ====================

@app.post(
    "/api/v1/workflows/execute",
    response_model=ExecuteResponse,
    response_model_exclude_none=False,
    responses={500: {"model": ErrorResponse}}
)
async def execute_workflow(
    request: ExecuteRequest,
    execution_service: ExecutionService = Depends(get_execution_service_dep)
):
    """
    执行工作流
    
    Args:
        request: 执行请求，包含工作流定义和配置
        execution_service: 执行服务（依赖注入）
        
    Returns:
        执行结果
    """
    try:
        # 使用执行服务执行工作流
        result = execution_service.execute_workflow(
            workflow_def=request.workflow,
            enable_monitoring=request.enable_monitoring,
            variables=request.workflow.variables,
            workflow_id=request.workflow_id
        )

        response_payload = ExecuteResponse(
            status=result.get("status", "completed"),
            execution_id=result.get("execution_id"),
            result=result.get("result", {}),
            summary=result.get("summary"),
            report_path=result.get("report_path"),
            report_content=result.get("report_content")
        )
        return response_payload.model_dump(exclude_none=False)
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_WORKFLOW_EXECUTION_FAILED,
                message="工作流执行失败",
                details=_build_exception_details(
                    exception=e,
                    stage="execute_workflow"
                )
            )
        )


@app.get(
    "/api/v1/executions/{execution_id}",
    response_model=ExecutionRunResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_execution_detail(
    execution_id: str,
    include_node_traces: bool = True,
    execution_service: ExecutionService = Depends(get_execution_service_dep)
):
    """
    获取执行详情（默认包含节点追踪）
    """
    try:
        execution = execution_service.get_execution_by_id(
            execution_id=execution_id,
            include_node_traces=include_node_traces
        )
        if execution is None:
            raise HTTPException(
                status_code=404,
                detail=_build_error_payload(
                    code=ERROR_CODE_EXECUTION_NOT_FOUND,
                    message="执行记录不存在",
                    details={"execution_id": execution_id}
                )
            )
        return execution
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "查询执行详情失败",
            execution_id=execution_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_EXECUTION_QUERY_FAILED,
                message="查询执行详情失败",
                details=_build_exception_details(
                    exception=e,
                    stage="get_execution_detail",
                    extra_details={"execution_id": execution_id}
                )
            )
        )


@app.get(
    "/api/v1/workflows/{workflow_id}/executions",
    response_model=ExecutionListResponse,
    responses={500: {"model": ErrorResponse}}
)
async def list_workflow_executions(
    workflow_id: str,
    limit: int = 20,
    offset: int = 0,
    execution_service: ExecutionService = Depends(get_execution_service_dep)
):
    """
    分页获取工作流执行历史
    """
    try:
        if limit <= 0:
            limit = 20
        if offset < 0:
            offset = 0
        return execution_service.list_workflow_executions(
            workflow_id=workflow_id,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(
            "查询工作流执行历史失败",
            workflow_id=workflow_id,
            limit=limit,
            offset=offset,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_EXECUTION_QUERY_FAILED,
                message="查询工作流执行历史失败",
                details=_build_exception_details(
                    exception=e,
                    stage="list_workflow_executions",
                    extra_details={
                        "workflow_id": workflow_id,
                        "limit": limit,
                        "offset": offset
                    }
                )
            )
        )


@app.get(
    "/api/v1/executions/{execution_id}/report",
    response_model=ExecutionReportResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_execution_report(
    execution_id: str,
    execution_service: ExecutionService = Depends(get_execution_service_dep)
):
    """
    获取执行报告内容（优先 execution_run 记录路径，其次默认日志路径）
    """
    try:
        report = execution_service.get_execution_report(execution_id)
        if report is None:
            raise HTTPException(
                status_code=404,
                detail=_build_error_payload(
                    code=ERROR_CODE_EXECUTION_REPORT_NOT_FOUND,
                    message="执行报告不存在",
                    details={"execution_id": execution_id}
                )
            )
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "读取执行报告失败",
            execution_id=execution_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_EXECUTION_QUERY_FAILED,
                message="读取执行报告失败",
                details=_build_exception_details(
                    exception=e,
                    stage="get_execution_report",
                    extra_details={"execution_id": execution_id}
                )
            )
        )


# ==================== 智能体模板 API ====================

@app.get("/api/v1/agents/templates", response_model=AgentTemplateResponse)
async def get_agent_templates(
    agent_service: AgentService = Depends(get_agent_service_dep)
):
    """
    获取所有预设的智能体模板
    
    Args:
        agent_service: 智能体服务（依赖注入）
    
    Returns:
        智能体模板字典，包含DataCollectionAgent、SentimentAgent、FilterAgent、ReportAgent
    """
    try:
        templates = agent_service.get_agent_templates()
        
        return AgentTemplateResponse(
            templates=templates,
            status="success"
        )
    except WorkflowJSONProcessingError as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_INVALID_LLM_WORKFLOW_JSON,
                message="LLM 返回的工作流 JSON 无效",
                details=_build_exception_details(
                    exception=e,
                    stage="generate_workflow",
                    extra_details={"llm_stage": e.stage}
                )
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_WORKFLOW_GENERATION_FAILED,
                message="生成工作流失败",
                details=_build_exception_details(
                    exception=e,
                    stage="generate_workflow"
                )
            )
        )


# ==================== 工作流管理 API ====================

@app.post(
    "/api/v1/workflows",
    response_model=WorkflowCreateResponse,
    responses={500: {"model": ErrorResponse}}
)
async def create_workflow(
    request: WorkflowCreateRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service_dep)
):
    """
    创建新工作流
    
    Args:
        request: 创建请求，包含工作流定义
        workflow_service: 工作流服务（依赖注入）
        
    Returns:
        创建的工作流信息，包含 workflow_id
    """
    try:
        # 使用工作流服务保存工作流
        workflow = workflow_service.save_workflow(
            workflow_def=request.workflow,
            description=request.description
        )
        
        return WorkflowCreateResponse(
            workflow_id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            created_at=workflow.created_at.isoformat() if workflow.created_at else None,
            status="created"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=_build_error_payload(
                code="WORKFLOW_VALIDATION_FAILED",
                message=str(e),
                details={"stage": "create_workflow"}
            )
        )
    except WorkflowSaveError as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=e.code,
                message=e.message,
                details=e.details
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_WORKFLOW_SAVE_FAILED,
                message="创建工作流失败",
                details=_build_exception_details(
                    exception=e,
                    stage="create_workflow"
                )
            )
        )


@app.get("/api/v1/workflows")
async def get_workflows(
    skip: int = 0,
    limit: int = 100,
    workflow_service: WorkflowService = Depends(get_workflow_service_dep)
):
    """
    获取所有工作流列表
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        workflow_service: 工作流服务（依赖注入）
        
    Returns:
        工作流列表
    """
    try:
        workflows = workflow_service.get_workflows(skip=skip, limit=limit)
        return {
            "workflows": [
                {
                    "id": w.id,
                    "name": w.name,
                    "description": w.description,
                    "created_at": w.created_at.isoformat() if w.created_at else None,
                    "updated_at": w.updated_at.isoformat() if w.updated_at else None
                }
                for w in workflows
            ]
        }
    except Exception as e:
        # 如果数据库未初始化，返回空列表
        return {"workflows": []}


@app.get("/api/v1/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service_dep)
):
    """
    获取单个工作流详情
    
    Args:
        workflow_id: 工作流ID
        workflow_service: 工作流服务（依赖注入）
        
    Returns:
        工作流详情，包含完整定义
    """
    try:
        workflow = workflow_service.get_workflow(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "definition": workflow.definition,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取工作流详情失败", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=404, detail="Workflow not found")


@app.put("/api/v1/workflows/{workflow_id}")
async def save_workflow(
    workflow_id: str,
    workflow: dict,
    request: Request,
    workflow_service: WorkflowService = Depends(get_workflow_service_dep)
):
    """
    保存工作流
    
    Args:
        workflow_id: 工作流ID
        workflow: 工作流数据
        request: HTTP 请求（用于获取关联信息）
        workflow_service: 工作流服务（依赖注入）
        
    Returns:
        保存的工作流
    """
    request_ctx = _get_request_context(request)
    workflow_name = workflow.get("name") if isinstance(workflow, dict) else None

    try:
        # 检查工作流是否存在
        existing = workflow_service.get_workflow(workflow_id)
        
        if existing:
            # 更新现有工作流
            updated = workflow_service.update_workflow_definition(
                workflow_id=workflow_id,
                definition=workflow,
                request_id=request_ctx["request_id"],
                conversation_id=request_ctx["conversation_id"]
            )
            return {
                "status": "updated",
                "workflow": {
                    "id": updated.id,
                    "name": updated.name,
                    "description": updated.description,
                    "updated_at": updated.updated_at.isoformat() if updated.updated_at else None
                }
            }
        else:
            # 创建新工作流（保持现有成功响应结构）
            workflow["id"] = workflow_id
            workflow["updated_at"] = datetime.now().isoformat()
            return {"status": "saved", "workflow": workflow}

    except WorkflowSaveError as e:
        details = {
            **(e.details or {}),
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "request_id": request_ctx["request_id"],
            "conversation_id": request_ctx["conversation_id"]
        }
        if "error_type" not in details:
            details["error_type"] = "workflow_save_error"
        if "error_summary" not in details:
            details["error_summary"] = str(e)
        logger.error(
            "API工作流保存失败",
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            error_type=details.get("error_type"),
            error_summary=details.get("error_summary"),
            request_id=request_ctx["request_id"],
            conversation_id=request_ctx["conversation_id"]
        )
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=e.code,
                message=e.message,
                details=details
            )
        )

    except Exception as e:
        error_summary = f"{type(e).__name__}: {str(e)}"
        details = {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "error_type": "workflow_save_unexpected_error",
            "error_summary": error_summary,
            "stage": "api_save_workflow",
            "request_id": request_ctx["request_id"],
            "conversation_id": request_ctx["conversation_id"]
        }
        logger.error(
            "API工作流保存失败",
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            error_type="workflow_save_unexpected_error",
            error_summary=error_summary,
            request_id=request_ctx["request_id"],
            conversation_id=request_ctx["conversation_id"]
        )
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_WORKFLOW_SAVE_FAILED,
                message="保存工作流失败",
                details=details
            )
        )


@app.delete("/api/v1/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service_dep)
):
    """
    删除工作流
    
    Args:
        workflow_id: 工作流ID
        workflow_service: 工作流服务（依赖注入）
        
    Returns:
        删除结果
    """
    try:
        success = workflow_service.delete_workflow(workflow_id, soft_delete=True)
        
        if success:
            return {"status": "deleted", "id": workflow_id}
        else:
            raise HTTPException(status_code=404, detail="Workflow not found")
            
    except HTTPException:
        raise
    except Exception as e:
        # 如果数据库操作失败
        raise HTTPException(status_code=404, detail="Workflow not found")


# ==================== AI 对话 API ====================

def get_ai_conversation_service():
    """
    获取AI对话服务实例
    """
    from workflow_engine.src.database.connection import get_session
    from workflow_engine.src.database.repositories import WorkflowRepository, ConversationRepository
    
    session = get_session()
    workflow_repo = WorkflowRepository(session)
    conversation_repo = ConversationRepository(session)
    workflow_service = WorkflowService(
        workflow_repo=workflow_repo,
        conversation_repo=conversation_repo
    )
    return AIConversationService(workflow_service=workflow_service)


@app.post("/api/v1/conversations/start",
          response_model=ConversationResponse,
          responses={500: {"model": ErrorResponse}})
async def start_conversation(
    request: StartConversationRequest,
    conversation_service: AIConversationService = Depends(get_ai_conversation_service)
):
    """
    开始新的AI对话，生成初始工作流
    
    Args:
        request: 开始对话请求，包含用户意图
        conversation_service: AI对话服务（依赖注入）
        
    Returns:
        包含工作流和对话信息的响应
    """
    try:
        result = conversation_service.start_conversation(
            user_intent=request.user_intent,
            workflow_type=request.workflow_type
        )
        
        return ConversationResponse(
            conversation_id=result["conversation_id"],
            workflow_id=result["workflow_id"],
            workflow=result["workflow"],
            message=result["message"]
        )
        
    except WorkflowJSONProcessingError as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_INVALID_LLM_WORKFLOW_JSON,
                message="LLM 返回的工作流 JSON 无效",
                details=_build_exception_details(
                    exception=e,
                    stage="start_conversation",
                    extra_details={
                        "llm_stage": e.stage,
                        "workflow_type": request.workflow_type
                    }
                )
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_CONVERSATION_FAILED,
                message="开始会话失败",
                details=_build_exception_details(
                    exception=e,
                    stage="start_conversation",
                    extra_details={"workflow_type": request.workflow_type}
                )
            )
        )


@app.post("/api/v1/conversations/continue",
          response_model=ConversationResponse,
          responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def continue_conversation(
    request: ConversationMessageRequest,
    conversation_service: AIConversationService = Depends(get_ai_conversation_service)
):
    """
    继续对话，根据用户反馈调整工作流
    
    Args:
        request: 对话消息请求，包含工作流ID和用户消息
        conversation_service: AI对话服务（依赖注入）
        
    Returns:
        包含调整后工作流的响应
    """
    try:
        result = conversation_service.continue_conversation(
            workflow_id=request.workflow_id,
            user_message=request.user_message
        )
        
        return ConversationResponse(
            conversation_id=result["conversation_id"],
            workflow_id=result["workflow_id"],
            workflow=result["workflow"],
            message=result["message"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=_build_error_payload(
                code=ERROR_CODE_CONVERSATION_NOT_FOUND,
                message="会话不存在",
                details=_build_exception_details(
                    exception=e,
                    stage="continue_conversation",
                    include_traceback=False,
                    extra_details={"workflow_id": request.workflow_id}
                )
            )
        )
    except WorkflowJSONProcessingError as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_INVALID_LLM_WORKFLOW_JSON,
                message="LLM 返回的工作流 JSON 无效",
                details=_build_exception_details(
                    exception=e,
                    stage="continue_conversation",
                    extra_details={
                        "llm_stage": e.stage,
                        "workflow_id": request.workflow_id
                    }
                )
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_build_error_payload(
                code=ERROR_CODE_CONVERSATION_FAILED,
                message="继续会话失败",
                details=_build_exception_details(
                    exception=e,
                    stage="continue_conversation",
                    extra_details={"workflow_id": request.workflow_id}
                )
            )
        )


@app.get("/api/v1/conversations/{workflow_id}/history",
         response_model=ConversationHistoryResponse,
         responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_conversation_history(
    workflow_id: str,
    limit: int = 10,
    conversation_service: AIConversationService = Depends(get_ai_conversation_service)
):
    """
    获取工作流的对话历史
    
    Args:
        workflow_id: 工作流ID
        limit: 返回的最大对话条数
        conversation_service: AI对话服务（依赖注入）
        
    Returns:
        工作流及其对话历史
    """
    try:
        result = conversation_service.get_workflow_with_history(workflow_id)
        
        return ConversationHistoryResponse(
            workflow_id=result["workflow_id"],
            workflow=result["workflow"],
            conversation_history=result["conversation_history"],
            created_at=result["created_at"],
            updated_at=result["updated_at"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except WorkflowJSONProcessingError as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "error_type": "invalid_llm_workflow_json",
                "stage": e.stage,
                "details": error_details,
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "details": error_details,
                "timestamp": datetime.now().isoformat()
            }
        )


@app.get("/api/v1/workflows/{workflow_id}/improvements",
         response_model=WorkflowImprovementResponse,
         responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_workflow_improvements(
    workflow_id: str,
    conversation_service: AIConversationService = Depends(get_ai_conversation_service)
):
    """
    获取工作流的AI改进建议
    
    Args:
        workflow_id: 工作流ID
        conversation_service: AI对话服务（依赖注入）
        
    Returns:
        包含改进建议的响应
    """
    try:
        result = conversation_service.suggest_improvements(workflow_id)
        
        return WorkflowImprovementResponse(
            workflow_id=result["workflow_id"],
            suggestions=result["suggestions"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except WorkflowJSONProcessingError as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "error_type": "invalid_llm_workflow_json",
                "stage": e.stage,
                "details": error_details,
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "details": error_details,
                "timestamp": datetime.now().isoformat()
            }
        )


# ==================== 启动函数 ====================

def start():
    """启动服务器的入口函数"""
    # 直接使用 app 对象并禁用重载以确保稳定性和路径解析
    # 使用端口 8123 以避免冲突
    uvicorn.run(app, host="0.0.0.0", port=8123)


if __name__ == "__main__":
    start()
