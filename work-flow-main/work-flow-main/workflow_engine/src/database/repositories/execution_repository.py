"""
执行记录 Repository
提供执行运行记录与节点追踪的持久化操作
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..models import ExecutionRun, ExecutionNodeTrace
from .base import BaseFilterRepository
from ...utils.logger import get_logger

logger = get_logger("execution_repository")


class ExecutionRepository(BaseFilterRepository[ExecutionRun]):
    """
    执行仓储
    管理执行运行记录和节点追踪记录的增删改查操作
    """

    def __init__(self, db: Session):
        """
        初始化仓储

        Args:
            db: 数据库会话
        """
        self.db = db

    @staticmethod
    def _calculate_duration_ms(
        started_at: Optional[datetime],
        completed_at: Optional[datetime]
    ) -> Optional[int]:
        """计算执行耗时（毫秒）"""
        if not started_at or not completed_at:
            return None
        duration = (completed_at - started_at).total_seconds() * 1000
        return max(0, int(duration))

    def create(self, entity: ExecutionRun) -> ExecutionRun:
        """
        创建执行运行记录
        """
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        logger.debug(f"创建执行运行记录: {entity.execution_id}")
        return entity

    def get_by_id(self, id: int) -> Optional[ExecutionRun]:
        """
        根据主键 ID 获取执行运行记录
        """
        return self.db.query(ExecutionRun).filter(ExecutionRun.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ExecutionRun]:
        """
        获取执行运行记录列表
        """
        return (
            self.db.query(ExecutionRun)
            .order_by(ExecutionRun.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(self, id: int, entity: ExecutionRun) -> ExecutionRun:
        """
        更新执行运行记录
        """
        existing = self.get_by_id(id)
        if not existing:
            raise ValueError(f"执行运行记录不存在: {id}")

        for key, value in entity.__dict__.items():
            if not key.startswith("_") and key not in {"id", "created_at"}:
                setattr(existing, key, value)

        existing.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(existing)
        logger.debug(f"更新执行运行记录: {id}")
        return existing

    def delete(self, id: int) -> bool:
        """
        删除执行运行记录（硬删除）
        """
        execution_run = self.get_by_id(id)
        if not execution_run:
            return False

        self.db.delete(execution_run)
        self.db.commit()
        logger.debug(f"删除执行运行记录: {id}")
        return True

    def find_by_conditions(
        self,
        conditions: Dict[str, Any],
        skip: int = 0,
        limit: int = 100
    ) -> List[ExecutionRun]:
        """
        根据条件查询执行运行记录
        """
        query = self.db.query(ExecutionRun)

        for key, value in conditions.items():
            if hasattr(ExecutionRun, key):
                query = query.filter(getattr(ExecutionRun, key) == value)

        return (
            query.order_by(ExecutionRun.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count(self, conditions: Optional[Dict[str, Any]] = None) -> int:
        """
        统计执行运行记录数量
        """
        query = self.db.query(ExecutionRun)

        if conditions:
            for key, value in conditions.items():
                if hasattr(ExecutionRun, key):
                    query = query.filter(getattr(ExecutionRun, key) == value)

        return query.count()

    def exists(self, id: int) -> bool:
        """
        检查执行运行记录是否存在
        """
        return self.db.query(ExecutionRun).filter(ExecutionRun.id == id).first() is not None

    def create_execution_run(
        self,
        execution_id: str,
        workflow_id: str,
        status: str = "pending",
        trigger_source: Optional[str] = None,
        started_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        final_report_path: Optional[str] = None
    ) -> ExecutionRun:
        """
        创建执行运行记录（便捷方法）
        """
        run = ExecutionRun(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=status,
            trigger_source=trigger_source,
            started_at=started_at,
            error_message=error_message,
            final_report_path=final_report_path
        )
        return self.create(run)

    def get_execution_run_by_execution_id(self, execution_id: str) -> Optional[ExecutionRun]:
        """
        根据 execution_id 获取执行运行记录
        """
        return (
            self.db.query(ExecutionRun)
            .filter(ExecutionRun.execution_id == execution_id)
            .first()
        )

    def list_execution_runs_by_workflow_id(
        self,
        workflow_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[ExecutionRun]:
        """
        按 workflow_id 分页查询执行运行记录
        """
        return (
            self.db.query(ExecutionRun)
            .filter(ExecutionRun.workflow_id == workflow_id)
            .order_by(ExecutionRun.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update_execution_run_status(
        self,
        execution_id: str,
        status: str,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> ExecutionRun:
        """
        更新执行运行状态
        """
        run = self.get_execution_run_by_execution_id(execution_id)
        if not run:
            raise ValueError(f"执行运行记录不存在: {execution_id}")

        run.status = status

        if started_at is not None:
            run.started_at = started_at
        elif status == "running" and run.started_at is None:
            run.started_at = datetime.utcnow()

        if completed_at is not None:
            run.completed_at = completed_at
        elif status in {"completed", "failed"}:
            run.completed_at = datetime.utcnow()

        if error_message is not None:
            run.error_message = error_message

        run.duration_ms = self._calculate_duration_ms(run.started_at, run.completed_at)
        run.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(run)
        logger.debug(f"更新执行运行状态: {execution_id} -> {status}")
        return run

    def finalize_execution_run(
        self,
        execution_id: str,
        status: str,
        final_report_path: Optional[str] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ) -> ExecutionRun:
        """
        完结执行运行记录
        """
        run = self.update_execution_run_status(
            execution_id=execution_id,
            status=status,
            error_message=error_message,
            completed_at=completed_at
        )

        if final_report_path is not None:
            run.final_report_path = final_report_path
            run.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(run)

        logger.debug(f"完结执行运行记录: {execution_id} -> {status}")
        return run

    def upsert_node_trace_status(
        self,
        execution_id: str,
        node_id: str,
        status: str,
        node_type: Optional[str] = None,
        input_payload: Optional[Dict[str, Any]] = None,
        output_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> ExecutionNodeTrace:
        """
        创建或更新节点追踪状态
        """
        trace = (
            self.db.query(ExecutionNodeTrace)
            .filter(
                ExecutionNodeTrace.execution_id == execution_id,
                ExecutionNodeTrace.node_id == node_id
            )
            .first()
        )

        if trace is None:
            trace = ExecutionNodeTrace(
                execution_id=execution_id,
                node_id=node_id,
                status=status,
                node_type=node_type,
                input_payload=input_payload,
                output_payload=output_payload,
                error_message=error_message,
                started_at=started_at,
                completed_at=completed_at
            )
            if status == "running" and trace.started_at is None:
                trace.started_at = datetime.utcnow()
            if status in {"completed", "failed"} and trace.completed_at is None:
                trace.completed_at = datetime.utcnow()

            trace.duration_ms = self._calculate_duration_ms(trace.started_at, trace.completed_at)
            self.db.add(trace)
            self.db.commit()
            self.db.refresh(trace)
            logger.debug(f"创建节点追踪: {execution_id}/{node_id} -> {status}")
            return trace

        trace.status = status

        if node_type is not None:
            trace.node_type = node_type
        if input_payload is not None:
            trace.input_payload = input_payload
        if output_payload is not None:
            trace.output_payload = output_payload
        if error_message is not None:
            trace.error_message = error_message

        if started_at is not None:
            trace.started_at = started_at
        elif status == "running" and trace.started_at is None:
            trace.started_at = datetime.utcnow()

        if completed_at is not None:
            trace.completed_at = completed_at
        elif status in {"completed", "failed"}:
            trace.completed_at = datetime.utcnow()

        trace.duration_ms = self._calculate_duration_ms(trace.started_at, trace.completed_at)

        self.db.commit()
        self.db.refresh(trace)
        logger.debug(f"更新节点追踪: {execution_id}/{node_id} -> {status}")
        return trace

    def list_node_traces_by_execution_id(self, execution_id: str) -> List[ExecutionNodeTrace]:
        """
        查询指定 execution_id 的全部节点追踪
        """
        return (
            self.db.query(ExecutionNodeTrace)
            .filter(ExecutionNodeTrace.execution_id == execution_id)
            .order_by(ExecutionNodeTrace.created_at.asc(), ExecutionNodeTrace.id.asc())
            .all()
        )