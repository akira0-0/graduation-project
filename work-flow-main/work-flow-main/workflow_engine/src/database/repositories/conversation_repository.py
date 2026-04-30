"""
对话 Repository
提供对话历史的持久化操作
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..models import Conversation
from .base import BaseFilterRepository
from ...utils.logger import get_logger

logger = get_logger("conversation_repository")


class ConversationRepository(BaseFilterRepository[Conversation]):
    """
    对话仓储
    管理对话历史的增删改查操作
    """
    
    def __init__(self, db: Session):
        """
        初始化仓储
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def create(self, entity: Conversation) -> Conversation:
        """
        创建对话记录
        
        Args:
            entity: 对话实体
            
        Returns:
            创建后的对话实体
        """
        if not entity.id:
            entity.id = str(uuid.uuid4())
        
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        logger.debug(f"创建对话记录: {entity.id}")
        return entity
    
    def create_conversation(
        self,
        workflow_id: str,
        user_message: str,
        assistant_response: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        创建对话记录的便捷方法
        
        Args:
            workflow_id: 工作流 ID
            user_message: 用户消息
            assistant_response: 助手响应
            context: 对话上下文
            
        Returns:
            创建后的对话实体
        """
        conversation = Conversation(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_message=user_message,
            assistant_response=assistant_response,
            context=context
        )
        return self.create(conversation)
    
    def get_by_id(self, id: str) -> Optional[Conversation]:
        """
        根据 ID 获取对话记录
        
        Args:
            id: 对话 ID
            
        Returns:
            对话实体，如果不存在则返回 None
        """
        return self.db.query(Conversation).filter(Conversation.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """
        获取对话列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            对话列表
        """
        return (
            self.db.query(Conversation)
            .order_by(Conversation.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_workflow_id(
        self, 
        workflow_id: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Conversation]:
        """
        获取指定工作流的对话历史
        
        Args:
            workflow_id: 工作流 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            对话列表（按时间正序）
        """
        conversations = (
            self.db.query(Conversation)
            .filter(Conversation.workflow_id == workflow_id)
            .order_by(Conversation.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        # 按时间正序返回
        return conversations[::-1]
    
    def get_recent_by_workflow(
        self, 
        workflow_id: str, 
        limit: int = 10
    ) -> List[Conversation]:
        """
        获取工作流最近的对话历史
        
        Args:
            workflow_id: 工作流 ID
            limit: 返回的最大条数
            
        Returns:
            对话列表（按时间正序）
        """
        return self.get_by_workflow_id(workflow_id, skip=0, limit=limit)
    
    def update(self, id: str, entity: Conversation) -> Conversation:
        """
        更新对话记录
        
        Args:
            id: 对话 ID
            entity: 更新后的对话实体
            
        Returns:
            更新后的对话实体
        """
        existing = self.get_by_id(id)
        if not existing:
            raise ValueError(f"对话记录不存在: {id}")
        
        # 更新字段
        for key, value in entity.__dict__.items():
            if not key.startswith('_') and key != 'id':
                setattr(existing, key, value)
        
        self.db.commit()
        self.db.refresh(existing)
        logger.debug(f"更新对话记录: {id}")
        return existing
    
    def update_response(
        self, 
        id: str, 
        assistant_response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        更新对话的助手响应
        
        Args:
            id: 对话 ID
            assistant_response: 助手响应
            context: 更新的上下文
            
        Returns:
            更新后的对话实体
        """
        conversation = self.get_by_id(id)
        if not conversation:
            raise ValueError(f"对话记录不存在: {id}")
        
        conversation.assistant_response = assistant_response
        if context:
            conversation.context = context
        
        self.db.commit()
        self.db.refresh(conversation)
        logger.debug(f"更新对话响应: {id}")
        return conversation
    
    def delete(self, id: str) -> bool:
        """
        删除对话记录
        
        Args:
            id: 对话 ID
            
        Returns:
            删除成功返回 True，否则返回 False
        """
        conversation = self.get_by_id(id)
        if not conversation:
            return False
        
        self.db.delete(conversation)
        self.db.commit()
        logger.debug(f"删除对话记录: {id}")
        return True
    
    def delete_by_workflow_id(self, workflow_id: str) -> int:
        """
        删除指定工作流的所有对话记录
        
        Args:
            workflow_id: 工作流 ID
            
        Returns:
            删除的记录数
        """
        count = (
            self.db.query(Conversation)
            .filter(Conversation.workflow_id == workflow_id)
            .delete()
        )
        self.db.commit()
        logger.debug(f"删除工作流 {workflow_id} 的所有对话记录: {count} 条")
        return count
    
    def find_by_conditions(
        self, 
        conditions: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Conversation]:
        """
        根据条件查询对话记录
        
        Args:
            conditions: 查询条件字典
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            符合条件的对话列表
        """
        query = self.db.query(Conversation)
        
        for key, value in conditions.items():
            if hasattr(Conversation, key):
                query = query.filter(getattr(Conversation, key) == value)
        
        return query.order_by(Conversation.timestamp.desc()).offset(skip).limit(limit).all()
    
    def count(self, conditions: Optional[Dict[str, Any]] = None) -> int:
        """
        统计对话记录数量
        
        Args:
            conditions: 查询条件字典
            
        Returns:
            对话数量
        """
        query = self.db.query(Conversation)
        
        if conditions:
            for key, value in conditions.items():
                if hasattr(Conversation, key):
                    query = query.filter(getattr(Conversation, key) == value)
        
        return query.count()
    
    def exists(self, id: str) -> bool:
        """
        检查对话记录是否存在
        
        Args:
            id: 对话 ID
            
        Returns:
            存在返回 True，否则返回 False
        """
        return self.db.query(Conversation).filter(Conversation.id == id).first() is not None
    
    def search_by_message(
        self, 
        keyword: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Conversation]:
        """
        根据消息内容搜索对话
        
        Args:
            keyword: 搜索关键词
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            匹配的对话列表
        """
        return (
            self.db.query(Conversation)
            .filter(
                Conversation.user_message.ilike(f"%{keyword}%") |
                Conversation.assistant_response.ilike(f"%{keyword}%")
            )
            .order_by(Conversation.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_context_chain(self, workflow_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取对话上下文链
        
        Args:
            workflow_id: 工作流 ID
            limit: 返回的最大条数
            
        Returns:
            对话上下文列表，格式为 [{"role": "user/assistant", "content": "..."}]
        """
        conversations = self.get_recent_by_workflow(workflow_id, limit)
        context_chain = []
        
        for conv in conversations:
            context_chain.append({"role": "user", "content": conv.user_message})
            if conv.assistant_response:
                context_chain.append({"role": "assistant", "content": conv.assistant_response})
        
        return context_chain

    def get_by_context_conversation_id(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Conversation]:
        """
        根据 context.conversation_id 获取同一会话链路的记录
        
        说明：
        - 兼容 SQLite / PostgreSQL，优先保证通用性
        - 对历史脏数据（context 非 dict）自动跳过
        
        Args:
            conversation_id: 会话ID（业务会话ID）
            limit: 返回最大条数（按时间正序的末尾 N 条）
        
        Returns:
            匹配的对话记录（按时间正序）
        """
        if not conversation_id:
            return []

        conversations = (
            self.db.query(Conversation)
            .order_by(Conversation.timestamp.asc())
            .all()
        )

        matched: List[Conversation] = []
        for conv in conversations:
            context = conv.context or {}
            if isinstance(context, dict) and context.get("conversation_id") == conversation_id:
                matched.append(conv)

        if limit and limit > 0:
            return matched[-limit:]
        return matched