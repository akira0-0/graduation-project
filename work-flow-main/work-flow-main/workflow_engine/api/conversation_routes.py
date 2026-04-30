"""
对话管理API路由
提供对话式工作流生成和管理的HTTP接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from ..services.conversation_manager import ConversationManager
from ..utils.logger import get_logger

logger = get_logger("conversation_routes")

# 创建路由器
router = APIRouter(prefix="/api/v1/conversation", tags=["conversation"])

# 初始化对话管理器
conversation_manager = ConversationManager()


# 请求模型
class StartConversationRequest(BaseModel):
    """开始对话请求"""
    user_input: str
    workflow_name: Optional[str] = None


class ContinueConversationRequest(BaseModel):
    """继续对话请求"""
    conversation_id: str
    user_input: str


# 响应模型
class ConversationResponse(BaseModel):
    """对话响应"""
    conversation_id: str
    workflow_id: Optional[str] = None
    workflow: Optional[Dict[str, Any]] = None
    task_plan: Optional[Dict[str, Any]] = None
    message: str
    suggestions: Optional[List[str]] = None
    type: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    """对话历史响应"""
    conversation_id: str
    messages: List[Dict[str, Any]]


# API端点
@router.post("/start", response_model=ConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """
    开始新对话
    
    根据用户输入的自然语言创建工作流
    """
    try:
        logger.info("开始新对话", user_input=request.user_input[:100])
        
        result = conversation_manager.start_conversation(
            user_input=request.user_input,
            workflow_name=request.workflow_name
        )
        
        return ConversationResponse(
            conversation_id=result["conversation_id"],
            workflow_id=result["workflow_id"],
            workflow=result["workflow"].model_dump() if result.get("workflow") else None,
            task_plan=result.get("task_plan"),
            message=result["message"],
            suggestions=result.get("suggestions"),
            type="workflow_created"
        )
        
    except Exception as e:
        logger.error("开始对话失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"开始对话失败: {str(e)}")


@router.post("/continue", response_model=ConversationResponse)
async def continue_conversation(request: ContinueConversationRequest):
    """
    继续对话
    
    根据用户反馈调整工作流
    """
    try:
        logger.info(
            "继续对话",
            conversation_id=request.conversation_id,
            user_input=request.user_input[:50]
        )
        
        result = conversation_manager.continue_conversation(
            conversation_id=request.conversation_id,
            user_input=request.user_input
        )
        
        return ConversationResponse(
            conversation_id=request.conversation_id,
            workflow_id=result.get("workflow_id"),
            workflow=result.get("workflow").model_dump() if result.get("workflow") else None,
            message=result["message"],
            suggestions=result.get("suggestions"),
            type=result.get("type")
        )
        
    except ValueError as e:
        logger.error("对话不存在", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("继续对话失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"继续对话失败: {str(e)}")


@router.get("/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(conversation_id: str):
    """
    获取对话历史
    
    返回指定对话的所有消息历史
    """
    try:
        messages = conversation_manager.get_conversation_history(conversation_id)
        
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=messages
        )
        
    except Exception as e:
        logger.error("获取对话历史失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")


@router.get("/{conversation_id}/workflow")
async def get_workflow_from_conversation(conversation_id: str):
    """
    从对话中获取工作流
    
    返回当前对话生成的工作流定义
    """
    try:
        workflow = conversation_manager.get_workflow_from_conversation(conversation_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail="对话不存在或未生成工作流")
        
        return {
            "conversation_id": conversation_id,
            "workflow": workflow.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取工作流失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取工作流失败: {str(e)}")


@router.post("/explain")
async def explain_workflow_plan(user_input: str):
    """
    解释工作流规划
    
    返回用户输入的任务规划说明
    """
    try:
        explanation = conversation_manager.orchestrator.get_planning_explanation(user_input)
        
        return {
            "user_input": user_input,
            "explanation": explanation
        }
        
    except Exception as e:
        logger.error("解释工作流规划失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"解释工作流规划失败: {str(e)}")