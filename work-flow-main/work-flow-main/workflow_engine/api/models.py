"""
API 数据模型
定义 API 请求和响应的数据结构
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from workflow_engine.src.core.schema import WorkflowDefinition


class GenerateRequest(BaseModel):
    """
    工作流生成请求模型
    """
    intent: str = Field(..., description="用户的自然语言描述，用于生成工作流")
    model: Optional[str] = Field(default=None, description="用于生成的 LLM 模型，不传时使用服务端配置")


class GenerateResponse(BaseModel):
    """
    工作流生成响应模型
    """
    workflow: WorkflowDefinition = Field(..., description="生成的工作流定义")
    status: str = Field(default="success", description="生成状态")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class ExecuteRequest(BaseModel):
    """
    工作流执行请求模型
    """
    workflow: WorkflowDefinition = Field(..., description="要执行的工作流定义")
    workflow_id: Optional[str] = Field(None, description="工作流数据库主键ID（UUID）")
    model: Optional[str] = Field(default=None, description="LLM 模型名称（用于 LLM 节点，不传时使用服务端配置）")
    enable_monitoring: bool = Field(default=True, description="是否启用执行监控")


class ExecuteResponse(BaseModel):
    """
    工作流执行响应模型
    """
    status: str = Field(..., description="执行状态（running, completed, failed）")
    execution_id: Optional[str] = Field(None, description="执行ID")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果（节点输出）")
    summary: Optional[Dict[str, Any]] = Field(None, description="执行摘要")
    report_path: Optional[str] = Field(None, description="执行报告文件路径")
    report_content: Optional[str] = Field(None, description="报告正文内容（优先提取自报告节点输出）")


class ErrorResponse(BaseModel):
    """
    标准错误响应模型（兼容旧结构并支持结构化错误）
    """
    code: Optional[str] = Field(None, description="稳定错误码")
    message: Optional[str] = Field(None, description="人类可读错误信息")
    details: Optional[Any] = Field(None, description="结构化错误上下文")
    error: Optional[str] = Field(None, description="旧版错误消息字段（兼容）")
    timestamp: Optional[str] = Field(None, description="错误时间戳")


class PublicOpinionRequest(BaseModel):
    """
    舆论分析工作流生成请求模型
    """
    topic: str = Field(..., description="分析主题，例如：某品牌、某事件、某产品等")
    requirements: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="额外需求配置，如数据源、时间范围、过滤条件等"
    )
    model: Optional[str] = Field(default=None, description="用于生成的 LLM 模型，不传时使用服务端配置")


class PublicOpinionResponse(BaseModel):
    """
    舆论分析工作流生成响应模型
    """
    workflow: WorkflowDefinition = Field(..., description="生成的舆论分析工作流定义")
    status: str = Field(default="success", description="生成状态")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="工作流元数据")


class AgentTemplateResponse(BaseModel):
    """
    智能体模板响应模型
    """
    templates: Dict[str, Dict[str, Any]] = Field(..., description="智能体模板字典")
    status: str = Field(default="success", description="响应状态")


class StartConversationRequest(BaseModel):
    """
    开始对话请求模型
    """
    user_intent: str = Field(..., description="用户的自然语言意图描述")
    workflow_type: Optional[str] = Field(None, description="工作流类型（可选）")


class ConversationMessageRequest(BaseModel):
    """
    对话消息请求模型
    """
    workflow_id: str = Field(..., description="工作流ID")
    user_message: str = Field(..., description="用户消息")


class ConversationResponse(BaseModel):
    """
    对话响应模型
    """
    conversation_id: str = Field(..., description="对话ID")
    workflow_id: str = Field(..., description="工作流ID")
    workflow: WorkflowDefinition = Field(..., description="工作流定义")
    message: str = Field(..., description="响应消息")


class ConversationHistoryResponse(BaseModel):
    """
    对话历史响应模型
    """
    workflow_id: str = Field(..., description="工作流ID")
    workflow: WorkflowDefinition = Field(..., description="工作流定义")
    conversation_history: List[Dict[str, Any]] = Field(..., description="对话历史")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class WorkflowImprovementResponse(BaseModel):
    """
    工作流改进建议响应模型
    """
    workflow_id: str = Field(..., description="工作流ID")
    suggestions: Dict[str, Any] = Field(..., description="改进建议")


class ExecutionNodeTraceResponse(BaseModel):
    """
    执行节点追踪响应模型
    """
    execution_id: str = Field(..., description="执行ID")
    node_id: str = Field(..., description="节点ID")
    node_type: Optional[str] = Field(None, description="节点类型")
    status: str = Field(..., description="节点执行状态")
    input_payload: Optional[Dict[str, Any]] = Field(None, description="节点输入")
    output_payload: Optional[Dict[str, Any]] = Field(None, description="节点输出")
    error_message: Optional[str] = Field(None, description="节点错误信息")
    started_at: Optional[str] = Field(None, description="节点开始时间")
    completed_at: Optional[str] = Field(None, description="节点完成时间")
    duration_ms: Optional[int] = Field(None, description="节点耗时（毫秒）")
    created_at: Optional[str] = Field(None, description="追踪记录创建时间")


class ExecutionRunResponse(BaseModel):
    """
    执行运行详情响应模型
    """
    execution_id: str = Field(..., description="执行ID")
    workflow_id: str = Field(..., description="工作流ID")
    status: str = Field(..., description="执行状态")
    started_at: Optional[str] = Field(None, description="执行开始时间")
    completed_at: Optional[str] = Field(None, description="执行完成时间")
    duration_ms: Optional[int] = Field(None, description="执行耗时（毫秒）")
    trigger_source: Optional[str] = Field(None, description="触发来源")
    error_message: Optional[str] = Field(None, description="执行错误信息")
    final_report_path: Optional[str] = Field(None, description="最终报告路径")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    node_traces: List[ExecutionNodeTraceResponse] = Field(default_factory=list, description="节点追踪记录")


class ExecutionListResponse(BaseModel):
    """
    工作流执行历史列表响应模型
    """
    workflow_id: str = Field(..., description="工作流ID")
    total: int = Field(..., description="执行记录总数")
    limit: int = Field(..., description="分页大小")
    offset: int = Field(..., description="分页偏移量")
    items: List[ExecutionRunResponse] = Field(default_factory=list, description="执行记录列表")


class ExecutionReportResponse(BaseModel):
    """
    执行报告读取响应模型
    """
    execution_id: str = Field(..., description="执行ID")
    report_path: Optional[str] = Field(None, description="报告文件路径")
    report_content: Optional[Any] = Field(None, description="报告内容")
    source: str = Field(..., description="报告来源（execution_run_report_path 或 logs_default_path）")


class WorkflowCreateRequest(BaseModel):
    """
    工作流创建请求模型
    """
    workflow: WorkflowDefinition = Field(..., description="要创建的工作流定义")
    description: Optional[str] = Field(None, description="工作流描述")


class WorkflowCreateResponse(BaseModel):
    """
    工作流创建响应模型
    """
    workflow_id: str = Field(..., description="创建的工作流ID（UUID）")
    name: str = Field(..., description="工作流名称")
    description: Optional[str] = Field(None, description="工作流描述")
    created_at: Optional[str] = Field(None, description="创建时间")
    status: str = Field(default="created", description="创建状态")
