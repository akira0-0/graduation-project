"""
执行监控模块
跟踪工作流执行过程，记录节点状态、执行时间、错误信息等
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import json

from ..utils.logger import get_logger

logger = get_logger("execution_monitor")


class NodeStatus(Enum):
    """节点执行状态枚举"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 正在执行
    SUCCESS = "success"       # 执行成功
    FAILED = "failed"         # 执行失败
    SKIPPED = "skipped"       # 被跳过


class ExecutionRecord:
    """执行记录类，记录单个节点的执行情况"""
    
    def __init__(self, node_id: str, node_type: str):
        """
        初始化执行记录
        
        Args:
            node_id: 节点ID
            node_type: 节点类型
        """
        self.node_id = node_id
        self.node_type = node_type
        self.status = NodeStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.input_data: Optional[Dict] = None
        self.output_data: Optional[Dict] = None
        self.error_message: Optional[str] = None
        self.retries: int = 0
    
    def start(self, input_data: Optional[Dict] = None):
        """开始执行"""
        self.status = NodeStatus.RUNNING
        self.start_time = datetime.now()
        self.input_data = input_data
        logger.info(f"节点 {self.node_id} 开始执行", node_id=self.node_id, node_type=self.node_type)
    
    def complete(self, output_data: Dict):
        """执行完成"""
        self.status = NodeStatus.SUCCESS
        self.end_time = datetime.now()
        self.output_data = output_data
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        logger.info(f"节点 {self.node_id} 执行成功", node_id=self.node_id, duration=f"{duration:.2f}s")
    
    def fail(self, error_message: str):
        """执行失败"""
        self.status = NodeStatus.FAILED
        self.end_time = datetime.now()
        self.error_message = error_message
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        logger.error(f"节点 {self.node_id} 执行失败", node_id=self.node_id, error=error_message, duration=f"{duration:.2f}s")
    
    def skip(self):
        """跳过执行"""
        self.status = NodeStatus.SKIPPED
        logger.info(f"节点 {self.node_id} 被跳过", node_id=self.node_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "retries": self.retries
        }


class ExecutionMonitor:
    """工作流执行监控器"""
    
    def __init__(self, workflow_id: str, workflow_name: str):
        """
        初始化执行监控器
        
        Args:
            workflow_id: 工作流ID
            workflow_name: 工作流名称
        """
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.status = "running"
        self.node_records: Dict[str, ExecutionRecord] = {}
        self.execution_id = f"exec_{self.start_time.strftime('%Y%m%d_%H%M%S')}"
        self.global_variables: Dict[str, Any] = {}
        self.error_logs: List[str] = []
        
        logger.info(f"工作流执行开始", workflow_id=workflow_id, workflow_name=workflow_name, execution_id=self.execution_id)
    
    def start_node(self, node_id: str, node_type: str, input_data: Optional[Dict] = None):
        """
        记录节点开始执行
        
        Args:
            node_id: 节点ID
            node_type: 节点类型
            input_data: 输入数据
        """
        if node_id not in self.node_records:
            self.node_records[node_id] = ExecutionRecord(node_id, node_type)
        self.node_records[node_id].start(input_data)
    
    def complete_node(self, node_id: str, output_data: Dict):
        """
        记录节点执行完成
        
        Args:
            node_id: 节点ID
            output_data: 输出数据
        """
        if node_id in self.node_records:
            self.node_records[node_id].complete(output_data)
    
    def fail_node(self, node_id: str, error_message: str):
        """
        记录节点执行失败
        
        Args:
            node_id: 节点ID
            error_message: 错误信息
        """
        if node_id in self.node_records:
            self.node_records[node_id].fail(error_message)
            self.error_logs.append(f"[{node_id}] {error_message}")
    
    def skip_node(self, node_id: str):
        """
        记录节点被跳过
        
        Args:
            node_id: 节点ID
        """
        if node_id in self.node_records:
            self.node_records[node_id].skip()
    
    def complete_workflow(self, success: bool = True):
        """
        记录工作流执行完成
        
        Args:
            success: 是否成功
        """
        self.end_time = datetime.now()
        self.status = "completed" if success else "failed"
        duration = (self.end_time - self.start_time).total_seconds()
        
        # 统计执行情况
        total_nodes = len(self.node_records)
        success_nodes = sum(1 for r in self.node_records.values() if r.status == NodeStatus.SUCCESS)
        failed_nodes = sum(1 for r in self.node_records.values() if r.status == NodeStatus.FAILED)
        skipped_nodes = sum(1 for r in self.node_records.values() if r.status == NodeStatus.SKIPPED)
        
        logger.info(
            f"工作流执行{'成功' if success else '失败'}",
            workflow_id=self.workflow_id,
            execution_id=self.execution_id,
            duration=f"{duration:.2f}s",
            total_nodes=total_nodes,
            success_nodes=success_nodes,
            failed_nodes=failed_nodes,
            skipped_nodes=skipped_nodes
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要
        
        Returns:
            执行摘要字典
        """
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else None
        
        total_nodes = len(self.node_records)
        success_nodes = sum(1 for r in self.node_records.values() if r.status == NodeStatus.SUCCESS)
        failed_nodes = sum(1 for r in self.node_records.values() if r.status == NodeStatus.FAILED)
        skipped_nodes = sum(1 for r in self.node_records.values() if r.status == NodeStatus.SKIPPED)
        
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": duration,
            "statistics": {
                "total_nodes": total_nodes,
                "success_nodes": success_nodes,
                "failed_nodes": failed_nodes,
                "skipped_nodes": skipped_nodes,
                "success_rate": f"{(success_nodes/total_nodes*100):.1f}%" if total_nodes > 0 else "0%"
            },
            "error_count": len(self.error_logs)
        }
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """
        获取详细执行报告
        
        Returns:
            详细报告字典
        """
        return {
            **self.get_summary(),
            "node_records": [record.to_dict() for record in self.node_records.values()],
            "error_logs": self.error_logs,
            "global_variables": self.global_variables
        }
    
    def save_report(self, filepath: str):
        """
        保存执行报告到文件
        
        Args:
            filepath: 文件路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.get_detailed_report(), f, ensure_ascii=False, indent=2)
        logger.info(f"执行报告已保存到 {filepath}")