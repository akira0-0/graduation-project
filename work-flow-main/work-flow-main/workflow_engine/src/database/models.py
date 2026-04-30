"""
数据库模型定义
使用 SQLAlchemy ORM 定义 PostgreSQL 数据库模型
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, DateTime, JSON, Integer, 
    Boolean, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Conversation(Base):
    """对话表：存储工作流对话历史"""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    context = Column(JSON, nullable=True)  # 存储对话上下文
    
    # 关系
    workflow = relationship("Workflow", back_populates="conversations")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, workflow_id={self.workflow_id}, timestamp={self.timestamp})>"


class Workflow(Base):
    """工作流表：存储工作流定义和元数据"""
    __tablename__ = "workflows"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    definition = Column(JSON, nullable=False)  # 存储完整的工作流 DSL
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 关系
    conversations = relationship("Conversation", back_populates="workflow", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="workflow", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="workflow", cascade="all, delete-orphan")
    execution_runs = relationship("ExecutionRun", back_populates="workflow", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Workflow(id={self.id}, name={self.name}, is_active={self.is_active})>"


class Memory(Base):
    """记忆表：存储智能体的各类记忆"""
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False, index=True)
    agent_type = Column(String, nullable=False, index=True)  # 智能体类型：data_collection, sentiment_analysis, report_generation
    memory_type = Column(String, nullable=False, index=True)  # 记忆类型：domain_knowledge, case_pattern, template, rule
    key = Column(String, nullable=False, index=True)  # 记忆键
    value = Column(JSON, nullable=False)  # 记忆值（支持复杂结构）
    extra_data = Column(JSON, nullable=True)  # 额外的元数据
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    workflow = relationship("Workflow", back_populates="memories")
    
    # 复合索引
    __table_args__ = (
        Index('idx_workflow_agent_type', 'workflow_id', 'agent_type'),
        Index('idx_agent_memory_type', 'agent_type', 'memory_type'),
    )
    
    def __repr__(self):
        return f"<Memory(id={self.id}, agent_type={self.agent_type}, memory_type={self.memory_type}, key={self.key})>"


class AuditLog(Base):
    """审计日志表：记录报告生成等关键操作的审计日志"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False, index=True)
    operation_type = Column(String, nullable=False, index=True)  # 操作类型：report_generation, data_analysis, etc.
    operator = Column(String, nullable=False)  # 操作者（智能体名称）
    input_data = Column(JSON, nullable=True)  # 输入数据
    output_data = Column(JSON, nullable=True)  # 输出数据
    template_used = Column(String, nullable=True)  # 使用的模板
    rules_applied = Column(JSON, nullable=True)  # 应用的规则
    status = Column(String, nullable=False, default="success")  # 状态：success, failed, warning
    error_message = Column(Text, nullable=True)  # 错误信息
    execution_time_ms = Column(Integer, nullable=True)  # 执行时间（毫秒）
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 关系
    workflow = relationship("Workflow", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, operation_type={self.operation_type}, status={self.status})>"


class ExecutionRun(Base):
    """执行运行记录表：记录一次工作流执行的总体状态与结果"""
    __tablename__ = "execution_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String, nullable=False, unique=True, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)  # pending, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    trigger_source = Column(String, nullable=True)  # manual, api, schedule 等
    error_message = Column(Text, nullable=True)
    final_report_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workflow = relationship("Workflow", back_populates="execution_runs")
    node_traces = relationship("ExecutionNodeTrace", back_populates="execution_run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_execution_runs_workflow_status", "workflow_id", "status"),
    )

    def __repr__(self):
        return f"<ExecutionRun(execution_id={self.execution_id}, workflow_id={self.workflow_id}, status={self.status})>"


class ExecutionNodeTrace(Base):
    """执行节点追踪表：记录单个节点在一次执行中的状态流转"""
    __tablename__ = "execution_node_traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String, ForeignKey("execution_runs.execution_id"), nullable=False, index=True)
    node_id = Column(String, nullable=False, index=True)
    node_type = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)  # pending, running, completed, failed
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    execution_run = relationship("ExecutionRun", back_populates="node_traces")

    __table_args__ = (
        Index("idx_execution_node_trace_exec_node", "execution_id", "node_id"),
    )

    def __repr__(self):
        return f"<ExecutionNodeTrace(execution_id={self.execution_id}, node_id={self.node_id}, status={self.status})>"