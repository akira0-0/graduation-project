"""
审计日志 Repository
提供审计日志数据的持久化操作
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models import AuditLog
from .base import BaseFilterRepository
from ...utils.logger import get_logger

logger = get_logger("audit_log_repository")


class AuditLogRepository(BaseFilterRepository[AuditLog]):
    """
    审计日志仓储
    管理审计日志（报告生成、数据分析等操作记录）的增删改查操作
    """
    
    def __init__(self, db: Session):
        """
        初始化仓储
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def create(self, entity: AuditLog) -> AuditLog:
        """
        创建审计日志记录
        
        Args:
            entity: 审计日志实体
            
        Returns:
            创建后的审计日志实体
        """
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        logger.debug(f"创建审计日志: {entity.operation_type}")
        return entity
    
    def log_operation(
        self,
        workflow_id: str,
        operation_type: str,
        operator: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        template_used: Optional[str] = None,
        rules_applied: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> AuditLog:
        """
        记录操作的便捷方法
        
        Args:
            workflow_id: 工作流 ID
            operation_type: 操作类型
            operator: 操作者（智能体名称）
            input_data: 输入数据
            output_data: 输出数据
            template_used: 使用的模板
            rules_applied: 应用的规则
            status: 状态
            error_message: 错误信息
            execution_time_ms: 执行时间（毫秒）
            
        Returns:
            创建后的审计日志实体
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
        return self.create(audit_log)
    
    def get_by_id(self, id: int) -> Optional[AuditLog]:
        """
        根据 ID 获取审计日志记录
        
        Args:
            id: 审计日志 ID
            
        Returns:
            审计日志实体，如果不存在则返回 None
        """
        return self.db.query(AuditLog).filter(AuditLog.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """
        获取审计日志列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            审计日志列表
        """
        return (
            self.db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_workflow(
        self, 
        workflow_id: str,
        skip: int = 0, 
        limit: int = 100
    ) -> List[AuditLog]:
        """
        获取指定工作流的审计日志
        
        Args:
            workflow_id: 工作流 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            审计日志列表
        """
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.workflow_id == workflow_id)
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_operation_type(
        self,
        operation_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        获取指定操作类型的审计日志
        
        Args:
            operation_type: 操作类型
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            审计日志列表
        """
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.operation_type == operation_type)
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_operator(
        self,
        operator: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        获取指定操作者的审计日志
        
        Args:
            operator: 操作者名称
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            审计日志列表
        """
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.operator == operator)
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        获取指定状态的审计日志
        
        Args:
            status: 状态（success, failed, warning）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            审计日志列表
        """
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.status == status)
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_errors(
        self,
        workflow_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        获取错误日志
        
        Args:
            workflow_id: 工作流 ID（可选）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            错误日志列表
        """
        query = self.db.query(AuditLog).filter(
            or_(AuditLog.status == "failed", AuditLog.status == "warning")
        )
        
        if workflow_id:
            query = query.filter(AuditLog.workflow_id == workflow_id)
        
        return query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    def get_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        workflow_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        获取指定时间范围内的审计日志
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            workflow_id: 工作流 ID（可选）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            审计日志列表
        """
        query = self.db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= start_time,
                AuditLog.timestamp <= end_time
            )
        )
        
        if workflow_id:
            query = query.filter(AuditLog.workflow_id == workflow_id)
        
        return query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    def update(self, id: int, entity: AuditLog) -> AuditLog:
        """
        更新审计日志记录
        
        注意：审计日志通常不应该被更新，此方法主要用于修正错误
        
        Args:
            id: 审计日志 ID
            entity: 更新后的审计日志实体
            
        Returns:
            更新后的审计日志实体
        """
        existing = self.get_by_id(id)
        if not existing:
            raise ValueError(f"审计日志不存在: {id}")
        
        # 更新字段
        for key, value in entity.__dict__.items():
            if not key.startswith('_') and key != 'id':
                setattr(existing, key, value)
        
        self.db.commit()
        self.db.refresh(existing)
        logger.debug(f"更新审计日志: {id}")
        return existing
    
    def delete(self, id: int) -> bool:
        """
        删除审计日志记录
        
        注意：审计日志通常不应该被删除，此方法主要用于清理过期日志
        
        Args:
            id: 审计日志 ID
            
        Returns:
            删除成功返回 True，否则返回 False
        """
        audit_log = self.get_by_id(id)
        if not audit_log:
            return False
        
        self.db.delete(audit_log)
        self.db.commit()
        logger.debug(f"删除审计日志: {id}")
        return True
    
    def delete_by_workflow(self, workflow_id: str) -> int:
        """
        删除指定工作流的所有审计日志
        
        Args:
            workflow_id: 工作流 ID
            
        Returns:
            删除的记录数
        """
        count = (
            self.db.query(AuditLog)
            .filter(AuditLog.workflow_id == workflow_id)
            .delete()
        )
        self.db.commit()
        logger.debug(f"删除工作流 {workflow_id} 的所有审计日志: {count} 条")
        return count
    
    def delete_before_time(self, before_time: datetime) -> int:
        """
        删除指定时间之前的审计日志（用于清理过期日志）
        
        Args:
            before_time: 截止时间
            
        Returns:
            删除的记录数
        """
        count = (
            self.db.query(AuditLog)
            .filter(AuditLog.timestamp < before_time)
            .delete()
        )
        self.db.commit()
        logger.info(f"清理 {before_time} 之前的审计日志: {count} 条")
        return count
    
    def find_by_conditions(
        self, 
        conditions: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100
    ) -> List[AuditLog]:
        """
        根据条件查询审计日志
        
        Args:
            conditions: 查询条件字典
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            符合条件的审计日志列表
        """
        query = self.db.query(AuditLog)
        
        for key, value in conditions.items():
            if hasattr(AuditLog, key):
                query = query.filter(getattr(AuditLog, key) == value)
        
        return query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    def count(self, conditions: Optional[Dict[str, Any]] = None) -> int:
        """
        统计审计日志数量
        
        Args:
            conditions: 查询条件字典
            
        Returns:
            审计日志数量
        """
        query = self.db.query(AuditLog)
        
        if conditions:
            for key, value in conditions.items():
                if hasattr(AuditLog, key):
                    query = query.filter(getattr(AuditLog, key) == value)
        
        return query.count()
    
    def exists(self, id: int) -> bool:
        """
        检查审计日志是否存在
        
        Args:
            id: 审计日志 ID
            
        Returns:
            存在返回 True，否则返回 False
        """
        return self.db.query(AuditLog).filter(AuditLog.id == id).first() is not None
    
    def count_by_status(self, workflow_id: Optional[str] = None) -> Dict[str, int]:
        """
        统计各状态的审计日志数量
        
        Args:
            workflow_id: 工作流 ID（可选）
            
        Returns:
            状态统计字典
        """
        query = self.db.query(AuditLog)
        
        if workflow_id:
            query = query.filter(AuditLog.workflow_id == workflow_id)
        
        result = {}
        for status in ["success", "failed", "warning"]:
            result[status] = query.filter(AuditLog.status == status).count()
        
        return result
    
    def get_average_execution_time(
        self,
        operation_type: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> Optional[float]:
        """
        获取平均执行时间
        
        Args:
            operation_type: 操作类型（可选）
            workflow_id: 工作流 ID（可选）
            
        Returns:
            平均执行时间（毫秒），如果没有数据则返回 None
        """
        query = self.db.query(AuditLog.execution_time_ms).filter(
            AuditLog.execution_time_ms.isnot(None)
        )
        
        if operation_type:
            query = query.filter(AuditLog.operation_type == operation_type)
        
        if workflow_id:
            query = query.filter(AuditLog.workflow_id == workflow_id)
        
        results = query.all()
        if not results:
            return None
        
        times = [r[0] for r in results if r[0] is not None]
        if not times:
            return None
        
        return sum(times) / len(times)
    
    def get_operation_types(self) -> List[str]:
        """
        获取所有操作类型
        
        Returns:
            操作类型列表
        """
        results = (
            self.db.query(AuditLog.operation_type)
            .distinct()
            .all()
        )
        return [r[0] for r in results if r[0]]
    
    def get_operators(self, workflow_id: Optional[str] = None) -> List[str]:
        """
        获取所有操作者
        
        Args:
            workflow_id: 工作流 ID（可选）
            
        Returns:
            操作者列表
        """
        query = self.db.query(AuditLog.operator)
        
        if workflow_id:
            query = query.filter(AuditLog.workflow_id == workflow_id)
        
        results = query.distinct().all()
        return [r[0] for r in results if r[0]]