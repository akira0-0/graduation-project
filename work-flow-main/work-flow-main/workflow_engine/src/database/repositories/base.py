"""
Repository 基类
定义通用的 CRUD 接口规范
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Repository 基类
    提供通用的 CRUD 操作接口
    """
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """
        创建实体
        
        Args:
            entity: 要创建的实体对象
            
        Returns:
            创建后的实体对象
        """
        pass
    
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T]:
        """
        根据 ID 获取实体
        
        Args:
            id: 实体 ID
            
        Returns:
            实体对象，如果不存在则返回 None
        """
        pass
    
    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        获取实体列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            实体列表
        """
        pass
    
    @abstractmethod
    def update(self, id: str, entity: T) -> T:
        """
        更新实体
        
        Args:
            id: 实体 ID
            entity: 更新后的实体对象
            
        Returns:
            更新后的实体对象
        """
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """
        删除实体
        
        Args:
            id: 实体 ID
            
        Returns:
            删除成功返回 True，否则返回 False
        """
        pass


class BaseFilterRepository(ABC, Generic[T]):
    """
    支持过滤查询的 Repository 基类
    """
    
    @abstractmethod
    def find_by_conditions(
        self, 
        conditions: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100
    ) -> List[T]:
        """
        根据条件查询实体
        
        Args:
            conditions: 查询条件字典
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            符合条件的实体列表
        """
        pass
    
    @abstractmethod
    def count(self, conditions: Optional[Dict[str, Any]] = None) -> int:
        """
        统计实体数量
        
        Args:
            conditions: 查询条件字典，如果为 None 则统计所有
            
        Returns:
            实体数量
        """
        pass
    
    @abstractmethod
    def exists(self, id: str) -> bool:
        """
        检查实体是否存在
        
        Args:
            id: 实体 ID
            
        Returns:
            存在返回 True，否则返回 False
        """
        pass