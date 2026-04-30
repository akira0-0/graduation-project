"""
工作流服务
封装工作流管理的核心业务逻辑
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..core.schema import WorkflowDefinition
from ..database.repositories import WorkflowRepository, ConversationRepository
from ..database.models import Workflow
from .planner_service import PlannerService
from ..utils.logger import get_logger

logger = get_logger("workflow_service")

ERROR_CODE_WORKFLOW_SAVE_FAILED = "WORKFLOW_SAVE_FAILED"


class WorkflowServiceError(Exception):
    """工作流服务异常基类（支持结构化错误响应）"""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_error_response(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


class WorkflowSaveError(WorkflowServiceError):
    """工作流保存失败异常"""

    def __init__(self, message: str = "保存工作流失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ERROR_CODE_WORKFLOW_SAVE_FAILED,
            message=message,
            details=details
        )


class WorkflowService:
    """
    工作流服务
    负责工作流的生成、保存、查询、删除等业务逻辑
    """
    
    def __init__(
        self,
        workflow_repo: WorkflowRepository,
        conversation_repo: Optional[ConversationRepository] = None,
        planner_service: Optional[PlannerService] = None
    ):
        """
        初始化工作流服务
        
        Args:
            workflow_repo: 工作流仓储
            conversation_repo: 对话仓储（可选）
            planner_service: 规划服务（可选）
        """
        self.workflow_repo = workflow_repo
        self.conversation_repo = conversation_repo
        self._planner_service = planner_service
    
    @property
    def planner_service(self) -> PlannerService:
        """获取规划服务（懒加载）"""
        if self._planner_service is None:
            self._planner_service = PlannerService()
        return self._planner_service
    
    def generate_workflow(
        self,
        intent: str,
        model: str = "deepseek-chat",
        save: bool = True
    ) -> Dict[str, Any]:
        """
        根据自然语言意图生成工作流
        
        Args:
            intent: 用户的自然语言描述
            model: 使用的 LLM 模型
            save: 是否保存到数据库
            
        Returns:
            包含工作流定义和元数据的字典
        """
        logger.info("生成工作流", intent=intent[:50], model=model)
        
        # 生成工作流定义
        workflow_def = self.planner_service.generate_workflow(intent, model)
        
        result = {
            "workflow": workflow_def,
            "status": "success",
            "metadata": {
                "model": model,
                "intent_length": len(intent),
                "node_count": len(workflow_def.nodes),
                "edge_count": len(workflow_def.edges)
            }
        }
        
        # 保存到数据库
        if save:
            workflow = self.save_workflow(workflow_def)
            result["workflow_id"] = workflow.id
            result["metadata"]["created_at"] = workflow.created_at.isoformat()
        
        return result
    
    def generate_public_opinion_workflow(
        self,
        topic: str,
        requirements: Optional[Dict[str, Any]] = None,
        model: str = "deepseek-chat",
        save: bool = True
    ) -> Dict[str, Any]:
        """
        生成舆论分析工作流
        
        Args:
            topic: 分析主题
            requirements: 额外需求配置
            model: 使用的 LLM 模型
            save: 是否保存到数据库
            
        Returns:
            包含工作流定义和元数据的字典
        """
        logger.info("生成舆论分析工作流", topic=topic, model=model)
        
        # 生成工作流定义
        workflow_def = self.planner_service.generate_public_opinion_workflow(
            topic=topic,
            requirements=requirements,
            model=model
        )
        
        result = {
            "workflow": workflow_def,
            "status": "success",
            "metadata": {
                "model": model,
                "topic": topic,
                "workflow_type": "public_opinion_analysis",
                "node_count": len(workflow_def.nodes),
                "edge_count": len(workflow_def.edges)
            }
        }
        
        # 保存到数据库
        if save:
            workflow = self.save_workflow(workflow_def)
            result["workflow_id"] = workflow.id
            result["metadata"]["created_at"] = workflow.created_at.isoformat()
        
        return result
    
    def save_workflow(
        self,
        workflow_def: WorkflowDefinition,
        description: Optional[str] = None,
        request_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Workflow:
        """
        保存工作流到数据库
        
        Args:
            workflow_def: 工作流定义
            description: 工作流描述
            request_id: 请求关联 ID（可选）
            conversation_id: 对话关联 ID（可选）
            
        Returns:
            保存的工作流实体
            
        Raises:
            ValueError: 工作流验证失败
            WorkflowSaveError: 数据库保存失败
        """
        # 验证工作流
        if not self.planner_service.validate_workflow(workflow_def):
            raise ValueError("工作流定义验证失败")
        
        # 转换为字典
        workflow_dict = workflow_def.model_dump()
        
        try:
            # 保存到数据库
            workflow = self.workflow_repo.create_from_dict(
                name=workflow_def.name,
                definition=workflow_dict,
                description=description or workflow_def.description
            )
            
            logger.info("工作流已保存", workflow_id=workflow.id, workflow_name=workflow.name)
            return workflow
            
        except Exception as e:
            error_summary = f"{type(e).__name__}: {str(e)}"
            details = {
                "workflow_name": workflow_def.name,
                "error_type": "database_save_error",
                "error_summary": error_summary,
                "stage": "save_workflow",
                "request_id": request_id,
                "conversation_id": conversation_id
            }
            logger.error(
                "工作流保存失败",
                workflow_name=workflow_def.name,
                error_type="database_save_error",
                error_summary=error_summary,
                request_id=request_id,
                conversation_id=conversation_id
            )
            raise WorkflowSaveError(
                message="保存工作流失败",
                details=details
            ) from e
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        获取工作流
        
        Args:
            workflow_id: 工作流 ID
            
        Returns:
            工作流实体，如果不存在则返回 None
        """
        return self.workflow_repo.get_by_id(workflow_id)
    
    def get_workflow_by_name(self, name: str) -> Optional[Workflow]:
        """
        根据名称获取工作流
        
        Args:
            name: 工作流名称
            
        Returns:
            工作流实体，如果不存在则返回 None
        """
        return self.workflow_repo.get_by_name(name)
    
    def get_workflows(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Workflow]:
        """
        获取工作流列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            工作流列表
        """
        return self.workflow_repo.get_all(skip=skip, limit=limit)
    
    def update_workflow(
        self,
        workflow_id: str,
        workflow_def: WorkflowDefinition,
        description: Optional[str] = None
    ) -> Workflow:
        """
        更新工作流
        
        Args:
            workflow_id: 工作流 ID
            workflow_def: 新的工作流定义
            description: 新的描述
            
        Returns:
            更新后的工作流实体
        """
        # 验证工作流
        if not self.planner_service.validate_workflow(workflow_def):
            raise ValueError("工作流定义验证失败")
        
        # 获取现有工作流
        workflow = self.workflow_repo.get_by_id(workflow_id)
        if not workflow:
            raise ValueError(f"工作流不存在: {workflow_id}")
        
        # 更新字段
        workflow_dict = workflow_def.model_dump()
        workflow.definition = workflow_dict
        workflow.name = workflow_def.name
        if description:
            workflow.description = description
        
        return self.workflow_repo.update(workflow_id, workflow)
    
    def update_workflow_definition(
        self,
        workflow_id: str,
        definition: Dict[str, Any],
        request_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Workflow:
        """
        更新工作流定义
        
        Args:
            workflow_id: 工作流 ID
            definition: 新的工作流定义字典
            request_id: 请求关联 ID（可选）
            conversation_id: 对话关联 ID（可选）
            
        Returns:
            更新后的工作流实体
        """
        workflow_name = definition.get("name") if isinstance(definition, dict) else None
        try:
            return self.workflow_repo.update_definition(workflow_id, definition)
        except Exception as e:
            error_summary = f"{type(e).__name__}: {str(e)}"
            details = {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "error_type": "database_update_error",
                "error_summary": error_summary,
                "stage": "update_workflow_definition",
                "request_id": request_id,
                "conversation_id": conversation_id
            }
            logger.error(
                "工作流更新失败",
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                error_type="database_update_error",
                error_summary=error_summary,
                request_id=request_id,
                conversation_id=conversation_id
            )
            raise WorkflowSaveError(
                message="保存工作流失败",
                details=details
            ) from e
    
    def delete_workflow(self, workflow_id: str, soft_delete: bool = True) -> bool:
        """
        删除工作流
        
        Args:
            workflow_id: 工作流 ID
            soft_delete: 是否软删除
            
        Returns:
            删除成功返回 True，否则返回 False
        """
        if soft_delete:
            return self.workflow_repo.delete(workflow_id)
        else:
            return self.workflow_repo.hard_delete(workflow_id)
    
    def search_workflows(
        self,
        keyword: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Workflow]:
        """
        搜索工作流
        
        Args:
            keyword: 搜索关键词
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            匹配的工作流列表
        """
        return self.workflow_repo.search_by_name(keyword, skip=skip, limit=limit)
    
    def get_workflow_count(self) -> int:
        """
        获取工作流总数
        
        Returns:
            工作流数量
        """
        return self.workflow_repo.count()
    
    def workflow_exists(self, workflow_id: str) -> bool:
        """
        检查工作流是否存在
        
        Args:
            workflow_id: 工作流 ID
            
        Returns:
            存在返回 True，否则返回 False
        """
        return self.workflow_repo.exists(workflow_id)
    
    def save_conversation(
        self,
        workflow_id: str,
        user_message: str,
        assistant_response: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        保存对话记录
        
        Args:
            workflow_id: 工作流 ID
            user_message: 用户消息
            assistant_response: 助手响应
            context: 对话上下文
            
        Returns:
            对话记录实体，如果没有 conversation_repo 则返回 None
        """
        if not self.conversation_repo:
            logger.warning("conversation_repo 未初始化，无法保存对话")
            return None
        
        return self.conversation_repo.create_conversation(
            workflow_id=workflow_id,
            user_message=user_message,
            assistant_response=assistant_response,
            context=context
        )
    
    def get_conversation_history(
        self,
        workflow_id: str,
        limit: int = 10
    ) -> List[Any]:
        """
        获取对话历史
        
        Args:
            workflow_id: 工作流 ID
            limit: 返回的最大条数
            
        Returns:
            对话记录列表
        """
        if not self.conversation_repo:
            logger.warning("conversation_repo 未初始化")
            return []
        
        return self.conversation_repo.get_recent_by_workflow(workflow_id, limit)