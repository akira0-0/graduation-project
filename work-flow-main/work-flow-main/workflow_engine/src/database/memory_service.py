"""
对话记忆持久化服务
提供对话历史、工作流记忆的持久化功能
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from .models import Workflow, Conversation, Memory, AuditLog
from ..utils.logger import get_logger

logger = get_logger("memory_service")


class ConversationMemoryService:
    """对话记忆服务：管理对话历史和工作流状态"""
    
    def __init__(self, db: Session):
        """
        初始化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def create_workflow(
        self,
        name: str,
        description: str,
        definition: Dict[str, Any]
    ) -> Workflow:
        """
        创建新的工作流记录
        
        Args:
            name: 工作流名称
            description: 工作流描述
            definition: 工作流定义（JSON）
            
        Returns:
            Workflow 实例
        """
        workflow_id = str(uuid.uuid4())
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            definition=definition
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"创建工作流记录: {workflow_id}")
        return workflow
    
    def save_conversation(
        self,
        workflow_id: str,
        user_message: str,
        assistant_response: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        保存对话记录
        
        Args:
            workflow_id: 工作流 ID
            user_message: 用户消息
            assistant_response: 助手响应
            context: 对话上下文
            
        Returns:
            Conversation 实例
        """
        conversation = Conversation(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_message=user_message,
            assistant_response=assistant_response,
            context=context
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        logger.debug(f"保存对话记录: {conversation.id}")
        return conversation
    
    def get_conversation_history(
        self,
        workflow_id: str,
        limit: int = 10
    ) -> List[Conversation]:
        """
        获取工作流的对话历史
        
        Args:
            workflow_id: 工作流 ID
            limit: 返回的最大条数
            
        Returns:
            对话记录列表
        """
        conversations = (
            self.db.query(Conversation)
            .filter(Conversation.workflow_id == workflow_id)
            .order_by(Conversation.timestamp.desc())
            .limit(limit)
            .all()
        )
        # 按时间正序返回
        return conversations[::-1]
    
    def get_workflow_by_id(self, workflow_id: str) -> Optional[Workflow]:
        """
        根据工作流 ID 获取工作流
        
        Args:
            workflow_id: 工作流 ID
            
        Returns:
            Workflow 实例或 None
        """
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()


class AgentMemoryService:
    """智能体记忆服务：管理智能体的知识、案例、模板等记忆"""
    
    def __init__(self, db: Session):
        """
        初始化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db

    def _is_persistable_workflow_id(self, workflow_id: Optional[str]) -> bool:
        """检查 workflow_id 是否可用于持久化（UUID 且在 workflows 表存在）"""
        if not workflow_id:
            return False

        try:
            uuid.UUID(str(workflow_id))
        except (ValueError, TypeError):
            return False

        try:
            return self.db.query(Workflow).filter(Workflow.id == str(workflow_id)).first() is not None
        except Exception as e:
            logger.warning(f"校验 workflow_id 可持久化性失败，降级为不写库: {e}")
            return False
    
    def save_memory(
        self,
        workflow_id: str,
        agent_type: str,
        memory_type: str,
        key: str,
        value: Any,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Memory]:
        """
        保存智能体记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型（data_collection, sentiment_analysis, report_generation）
            memory_type: 记忆类型（domain_knowledge, case_pattern, template, rule）
            key: 记忆键
            value: 记忆值
            extra_data: 元数据
            
        Returns:
            Memory 实例
        """
        if not self._is_persistable_workflow_id(workflow_id):
            logger.warning(
                "workflow_id 缺失或无效，跳过记忆写入并降级执行",
                workflow_id=workflow_id,
                agent_type=agent_type,
                memory_type=memory_type,
                key=key
            )
            return None

        # 检查是否已存在相同键的记忆，如果存在则更新
        existing = (
            self.db.query(Memory)
            .filter(
                Memory.workflow_id == workflow_id,
                Memory.agent_type == agent_type,
                Memory.memory_type == memory_type,
                Memory.key == key
            )
            .first()
        )
        
        if existing:
            existing.value = value
            existing.extra_data = extra_data
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            logger.debug(f"更新记忆: {key}")
            return existing
        
        # 创建新记忆
        memory = Memory(
            workflow_id=workflow_id,
            agent_type=agent_type,
            memory_type=memory_type,
            key=key,
            value=value,
            extra_data=extra_data
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        logger.debug(f"保存新记忆: {key}")
        return memory
    
    def get_memory(
        self,
        workflow_id: str,
        agent_type: str,
        memory_type: Optional[str] = None,
        key: Optional[str] = None
    ) -> List[Memory]:
        """
        获取智能体记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            memory_type: 记忆类型（可选）
            key: 记忆键（可选）
            
        Returns:
            记忆列表
        """
        query = self.db.query(Memory).filter(
            Memory.workflow_id == workflow_id,
            Memory.agent_type == agent_type
        )
        
        if memory_type:
            query = query.filter(Memory.memory_type == memory_type)
        
        if key:
            query = query.filter(Memory.key == key)
        
        return query.all()
    
    def get_domain_knowledge(
        self,
        workflow_id: str,
        agent_type: str
    ) -> Dict[str, Any]:
        """
        获取领域知识记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            
        Returns:
            领域知识字典
        """
        memories = self.get_memory(
            workflow_id,
            agent_type,
            memory_type="domain_knowledge"
        )
        return {m.key: m.value for m in memories}
    
    def get_case_patterns(
        self,
        workflow_id: str,
        agent_type: str
    ) -> List[Dict[str, Any]]:
        """
        获取案例模式记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            
        Returns:
            案例模式列表
        """
        memories = self.get_memory(
            workflow_id,
            agent_type,
            memory_type="case_pattern"
        )
        return [m.value for m in memories]
    
    def get_templates(
        self,
        workflow_id: str,
        agent_type: str
    ) -> Dict[str, str]:
        """
        获取模板记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            
        Returns:
            模板字典
        """
        memories = self.get_memory(
            workflow_id,
            agent_type,
            memory_type="template"
        )
        return {m.key: m.value for m in memories}
    
    def get_rules(
        self,
        workflow_id: str,
        agent_type: str
    ) -> List[Dict[str, Any]]:
        """
        获取规则记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            
        Returns:
            规则列表
        """
        memories = self.get_memory(
            workflow_id,
            agent_type,
            memory_type="rule"
        )
        return [m.value for m in memories]


class AuditLogService:
    """审计日志服务：记录关键操作的审计日志"""
    
    def __init__(self, db: Session):
        """
        初始化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def log_operation(
        self,
        workflow_id: str,
        operation_type: str,
        operator: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        template_used: Optional[str] = None,
        rules_applied: Optional[List[Dict[str, Any]]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> AuditLog:
        """
        记录操作审计日志
        
        Args:
            workflow_id: 工作流 ID
            operation_type: 操作类型
            operator: 操作者
            input_data: 输入数据
            output_data: 输出数据
            template_used: 使用的模板
            rules_applied: 应用的规则
            status: 状态
            error_message: 错误信息
            execution_time_ms: 执行时间（毫秒）
            
        Returns:
            AuditLog 实例
        """
        audit_log = AuditLog(
            workflow_id=workflow_id,
            operation_type=operation_type,
            operator=operator,
            input_data=input_data,
            output_data=output_data,
            template_used=template_used,
            rules_applied=rules_applied,
            status=status,
            error_message=error_message,
            execution_time_ms=execution_time_ms
        )
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        logger.info(f"记录审计日志: {operation_type} by {operator}")
        return audit_log
    
    def get_audit_logs(
        self,
        workflow_id: str,
        operation_type: Optional[str] = None,
        limit: int = 50
    ) -> List[AuditLog]:
        """
        获取审计日志
        
        Args:
            workflow_id: 工作流 ID
            operation_type: 操作类型（可选）
            limit: 返回的最大条数
            
        Returns:
            审计日志列表
        """
        query = self.db.query(AuditLog).filter(
            AuditLog.workflow_id == workflow_id
        )
        
        if operation_type:
            query = query.filter(AuditLog.operation_type == operation_type)
        
        return (
            query.order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )