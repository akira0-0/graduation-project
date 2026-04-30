"""
记忆 Repository
提供智能体记忆数据的持久化操作
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..models import Memory, Workflow
from .base import BaseFilterRepository
from ...utils.logger import get_logger

logger = get_logger("memory_repository")


class MemoryRepository(BaseFilterRepository[Memory]):
    """
    记忆仓储
    管理智能体记忆（领域知识、案例模式、模板、规则等）的增删改查操作
    """
    
    def __init__(self, db: Session):
        """
        初始化仓储
        
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
    
    def create(self, entity: Memory) -> Memory:
        """
        创建记忆记录
        
        Args:
            entity: 记忆实体
            
        Returns:
            创建后的记忆实体
        """
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        logger.debug(f"创建记忆记录: {entity.key}")
        return entity
    
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
        保存智能体记忆（如果存在则更新）
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            memory_type: 记忆类型
            key: 记忆键
            value: 记忆值
            extra_data: 额外元数据
            
        Returns:
            创建或更新后的记忆实体
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

        # 检查是否已存在
        existing = self.find_one(
            workflow_id=workflow_id,
            agent_type=agent_type,
            memory_type=memory_type,
            key=key
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
        return self.create(memory)
    
    def get_by_id(self, id: int) -> Optional[Memory]:
        """
        根据 ID 获取记忆记录
        
        Args:
            id: 记忆 ID
            
        Returns:
            记忆实体，如果不存在则返回 None
        """
        return self.db.query(Memory).filter(Memory.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Memory]:
        """
        获取记忆列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            记忆列表
        """
        return (
            self.db.query(Memory)
            .order_by(Memory.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def find_one(
        self,
        workflow_id: str,
        agent_type: str,
        memory_type: str,
        key: str
    ) -> Optional[Memory]:
        """
        查找特定的记忆记录
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            memory_type: 记忆类型
            key: 记忆键
            
        Returns:
            记忆实体，如果不存在则返回 None
        """
        return (
            self.db.query(Memory)
            .filter(
                Memory.workflow_id == workflow_id,
                Memory.agent_type == agent_type,
                Memory.memory_type == memory_type,
                Memory.key == key
            )
            .first()
        )
    
    def get_by_workflow(
        self, 
        workflow_id: str,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Memory]:
        """
        获取工作流的所有记忆
        
        Args:
            workflow_id: 工作流 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            记忆列表
        """
        return (
            self.db.query(Memory)
            .filter(Memory.workflow_id == workflow_id)
            .order_by(Memory.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_agent_type(
        self,
        workflow_id: str,
        agent_type: str,
        memory_type: Optional[str] = None
    ) -> List[Memory]:
        """
        获取指定智能体类型的记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            memory_type: 记忆类型（可选）
            
        Returns:
            记忆列表
        """
        query = self.db.query(Memory).filter(
            Memory.workflow_id == workflow_id,
            Memory.agent_type == agent_type
        )
        
        if memory_type:
            query = query.filter(Memory.memory_type == memory_type)
        
        return query.order_by(Memory.updated_at.desc()).all()
    
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
        memories = self.get_by_agent_type(
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
        memories = self.get_by_agent_type(
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
        memories = self.get_by_agent_type(
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
        memories = self.get_by_agent_type(
            workflow_id,
            agent_type,
            memory_type="rule"
        )
        return [m.value for m in memories]
    
    def update(self, id: int, entity: Memory) -> Memory:
        """
        更新记忆记录
        
        Args:
            id: 记忆 ID
            entity: 更新后的记忆实体
            
        Returns:
            更新后的记忆实体
        """
        existing = self.get_by_id(id)
        if not existing:
            raise ValueError(f"记忆记录不存在: {id}")
        
        # 更新字段
        for key, value in entity.__dict__.items():
            if not key.startswith('_') and key != 'id':
                setattr(existing, key, value)
        
        existing.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(existing)
        logger.debug(f"更新记忆记录: {id}")
        return existing
    
    def delete(self, id: int) -> bool:
        """
        删除记忆记录
        
        Args:
            id: 记忆 ID
            
        Returns:
            删除成功返回 True，否则返回 False
        """
        memory = self.get_by_id(id)
        if not memory:
            return False
        
        self.db.delete(memory)
        self.db.commit()
        logger.debug(f"删除记忆记录: {id}")
        return True
    
    def delete_by_workflow(self, workflow_id: str) -> int:
        """
        删除指定工作流的所有记忆
        
        Args:
            workflow_id: 工作流 ID
            
        Returns:
            删除的记录数
        """
        count = (
            self.db.query(Memory)
            .filter(Memory.workflow_id == workflow_id)
            .delete()
        )
        self.db.commit()
        logger.debug(f"删除工作流 {workflow_id} 的所有记忆: {count} 条")
        return count
    
    def delete_by_agent_type(
        self,
        workflow_id: str,
        agent_type: str,
        memory_type: Optional[str] = None
    ) -> int:
        """
        删除指定智能体类型的记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            memory_type: 记忆类型（可选）
            
        Returns:
            删除的记录数
        """
        query = self.db.query(Memory).filter(
            Memory.workflow_id == workflow_id,
            Memory.agent_type == agent_type
        )
        
        if memory_type:
            query = query.filter(Memory.memory_type == memory_type)
        
        count = query.delete()
        self.db.commit()
        logger.debug(f"删除智能体 {agent_type} 的记忆: {count} 条")
        return count
    
    def find_by_conditions(
        self, 
        conditions: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Memory]:
        """
        根据条件查询记忆记录
        
        Args:
            conditions: 查询条件字典
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            符合条件的记忆列表
        """
        query = self.db.query(Memory)
        
        for key, value in conditions.items():
            if hasattr(Memory, key):
                query = query.filter(getattr(Memory, key) == value)
        
        return query.order_by(Memory.updated_at.desc()).offset(skip).limit(limit).all()
    
    def count(self, conditions: Optional[Dict[str, Any]] = None) -> int:
        """
        统计记忆记录数量
        
        Args:
            conditions: 查询条件字典
            
        Returns:
            记忆数量
        """
        query = self.db.query(Memory)
        
        if conditions:
            for key, value in conditions.items():
                if hasattr(Memory, key):
                    query = query.filter(getattr(Memory, key) == value)
        
        return query.count()
    
    def exists(self, id: int) -> bool:
        """
        检查记忆记录是否存在
        
        Args:
            id: 记忆 ID
            
        Returns:
            存在返回 True，否则返回 False
        """
        return self.db.query(Memory).filter(Memory.id == id).first() is not None
    
    def get_memory_types(self, workflow_id: str) -> List[str]:
        """
        获取工作流中使用的所有记忆类型
        
        Args:
            workflow_id: 工作流 ID
            
        Returns:
            记忆类型列表
        """
        results = (
            self.db.query(Memory.memory_type)
            .filter(Memory.workflow_id == workflow_id)
            .distinct()
            .all()
        )
        return [r[0] for r in results]
    
    def get_agent_types(self, workflow_id: str) -> List[str]:
        """
        获取工作流中使用的所有智能体类型
        
        Args:
            workflow_id: 工作流 ID
            
        Returns:
            智能体类型列表
        """
        results = (
            self.db.query(Memory.agent_type)
            .filter(Memory.workflow_id == workflow_id)
            .distinct()
            .all()
        )
        return [r[0] for r in results]