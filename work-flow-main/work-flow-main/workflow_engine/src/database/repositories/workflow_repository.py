"""
工作流 Repository
提供工作流数据的持久化操作
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..models import Workflow
from .base import BaseFilterRepository
from ...utils.logger import get_logger

logger = get_logger("workflow_repository")


class WorkflowRepository(BaseFilterRepository[Workflow]):
    """
    工作流仓储
    管理工作流定义的增删改查操作
    """
    
    def __init__(self, db: Session):
        """
        初始化仓储
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def create(self, entity: Workflow) -> Workflow:
        """
        创建工作流
        
        Args:
            entity: 工作流实体
            
        Returns:
            创建后的工作流实体
        """
        if not entity.id:
            entity.id = str(uuid.uuid4())
        
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        logger.info(f"创建工作流: {entity.id}")
        return entity
    
    def create_from_dict(
        self, 
        name: str, 
        definition: Dict[str, Any],
        description: Optional[str] = None
    ) -> Workflow:
        """
        从字典创建工作流
        
        Args:
            name: 工作流名称
            definition: 工作流定义（JSON）
            description: 工作流描述
            
        Returns:
            创建后的工作流实体
        """
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            definition=definition,
            is_active=True
        )
        return self.create(workflow)
    
    def get_by_id(self, id: str) -> Optional[Workflow]:
        """
        根据 ID 获取工作流
        
        Args:
            id: 工作流 ID
            
        Returns:
            工作流实体，如果不存在则返回 None
        """
        return self.db.query(Workflow).filter(Workflow.id == id).first()
    
    def get_by_name(self, name: str) -> Optional[Workflow]:
        """
        根据名称获取工作流
        
        Args:
            name: 工作流名称
            
        Returns:
            工作流实体，如果不存在则返回 None
        """
        return self.db.query(Workflow).filter(Workflow.name == name).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Workflow]:
        """
        获取工作流列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            工作流列表
        """
        return (
            self.db.query(Workflow)
            .filter(Workflow.is_active == True)
            .order_by(Workflow.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update(self, id: str, entity: Workflow) -> Workflow:
        """
        更新工作流
        
        Args:
            id: 工作流 ID
            entity: 更新后的工作流实体
            
        Returns:
            更新后的工作流实体
        """
        existing = self.get_by_id(id)
        if not existing:
            raise ValueError(f"工作流不存在: {id}")
        
        # 更新字段
        for key, value in entity.__dict__.items():
            if not key.startswith('_') and key != 'id':
                setattr(existing, key, value)
        
        existing.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(existing)
        logger.info(f"更新工作流: {id}")
        return existing
    
    def update_definition(self, id: str, definition: Dict[str, Any]) -> Workflow:
        """
        更新工作流定义
        
        Args:
            id: 工作流 ID
            definition: 新的工作流定义
            
        Returns:
            更新后的工作流实体
        """
        workflow = self.get_by_id(id)
        if not workflow:
            raise ValueError(f"工作流不存在: {id}")
        
        workflow.definition = definition
        workflow.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"更新工作流定义: {id}")
        return workflow
    
    def delete(self, id: str) -> bool:
        """
        删除工作流（软删除）
        
        Args:
            id: 工作流 ID
            
        Returns:
            删除成功返回 True，否则返回 False
        """
        workflow = self.get_by_id(id)
        if not workflow:
            return False
        
        workflow.is_active = False
        workflow.updated_at = datetime.utcnow()
        self.db.commit()
        logger.info(f"删除工作流（软删除）: {id}")
        return True
    
    def hard_delete(self, id: str) -> bool:
        """
        硬删除工作流
        
        Args:
            id: 工作流 ID
            
        Returns:
            删除成功返回 True，否则返回 False
        """
        workflow = self.get_by_id(id)
        if not workflow:
            return False
        
        self.db.delete(workflow)
        self.db.commit()
        logger.info(f"硬删除工作流: {id}")
        return True
    
    def find_by_conditions(
        self, 
        conditions: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Workflow]:
        """
        根据条件查询工作流
        
        Args:
            conditions: 查询条件字典
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            符合条件的工作流列表
        """
        query = self.db.query(Workflow).filter(Workflow.is_active == True)
        
        for key, value in conditions.items():
            if hasattr(Workflow, key):
                query = query.filter(getattr(Workflow, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, conditions: Optional[Dict[str, Any]] = None) -> int:
        """
        统计工作流数量
        
        Args:
            conditions: 查询条件字典
            
        Returns:
            工作流数量
        """
        query = self.db.query(Workflow).filter(Workflow.is_active == True)
        
        if conditions:
            for key, value in conditions.items():
                if hasattr(Workflow, key):
                    query = query.filter(getattr(Workflow, key) == value)
        
        return query.count()
    
    def exists(self, id: str) -> bool:
        """
        检查工作流是否存在
        
        Args:
            id: 工作流 ID
            
        Returns:
            存在返回 True，否则返回 False
        """
        return self.db.query(Workflow).filter(
            Workflow.id == id, 
            Workflow.is_active == True
        ).first() is not None
    
    def search_by_name(self, keyword: str, skip: int = 0, limit: int = 100) -> List[Workflow]:
        """
        根据名称关键词搜索工作流
        
        Args:
            keyword: 搜索关键词
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            匹配的工作流列表
        """
        return (
            self.db.query(Workflow)
            .filter(
                Workflow.is_active == True,
                Workflow.name.ilike(f"%{keyword}%")
            )
            .offset(skip)
            .limit(limit)
            .all()
        )