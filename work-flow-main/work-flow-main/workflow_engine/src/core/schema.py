"""
工作流引擎核心数据模型
定义工作流的 DSL（领域特定语言）格式和运行时状态
"""
from typing import List, Dict, Any, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field
import operator


# ==================== DSL 定义层 ====================
# 这些模型定义了工作流的存储格式 (JSON)

class NodeConfig(BaseModel):
    """节点配置信息"""
    title: str = Field(..., description="节点展示名称")
    description: Optional[str] = None
    # Agent 配置（用于智能体节点）
    agent_role: Optional[str] = Field(None, description="执行此节点的 Agent 角色")
    agent_goal: Optional[str] = Field(None, description="Agent 的目标")
    agent_backstory: Optional[str] = Field(None, description="Agent 的背景人设")
    
    # 不同节点类型的特定配置，例如 LLM 的 prompt, model 等
    # 使用 Dict 保持通用性，具体验证在运行时处理
    params: Dict[str, Any] = Field(default_factory=dict, description="节点特定参数")

class NodeDefinition(BaseModel):
    """节点定义"""
    id: str = Field(..., description="节点唯一标识符")
    type: Literal["Start", "End", "LLM", "Code", "Condition", "Loop",
                   "DataCollectionAgent", "SentimentAgent", "ReportAgent", "FilterAgent",
                   "XHSFilterAgent"] = Field(
        ...,
        description="节点类型：Start(开始), End(结束), LLM(大模型), Code(代码), Condition(条件), Loop(循环), "
                    "DataCollectionAgent(数据收集智能体), SentimentAgent(情感分析智能体), "
                    "ReportAgent(报告生成智能体), FilterAgent(信息过滤智能体), "
                    "XHSFilterAgent(XHS三层智能过滤，替代DataCollection+Filter组合)"
    )
    config: NodeConfig

class EdgeDefinition(BaseModel):
    """边定义：连接两个节点"""
    source: str = Field(..., description="起始节点ID")
    target: str = Field(..., description="目标节点ID")
    # 对于条件分支，可以指定 condition_value
    condition: Optional[str] = Field(None, description="条件分支的值，用于 Condition 节点的路由")
    # 循环节点分支标识
    branch: Optional[str] = Field(None, description="分支标识：'loop_body' 表示循环体，'loop_exit' 表示循环结束后执行")

class WorkflowDefinition(BaseModel):
    """完整的工作流定义 DSL"""
    name: str = Field(..., description="工作流名称")
    description: Optional[str] = Field(None, description="工作流描述")
    nodes: List[NodeDefinition] = Field(..., description="节点列表")
    edges: List[EdgeDefinition] = Field(..., description="连线列表")
    
    # 全局变量定义（可选）
    variables: Dict[str, Any] = Field(default_factory=dict, description="全局变量")


# ==================== 运行时状态层 ====================
# 这些模型定义了 LangGraph 运行时的状态

class WorkflowState(BaseModel):
    """工作流运行时的全局状态
    
    使用 Annotated 类型支持 LangGraph 的并发节点执行。
    - node_outputs: 使用 operator.or_ 合并多个节点的输出
    - context: 使用 operator.or_ 合并上下文更新
    - messages: 使用 operator.add 追加消息
    """
    # 工作流ID（用于数据库关联）
    workflow_id: Optional[str] = Field(
        None,
        description="工作流ID，用于数据库关联和审计"
    )
    
    # 存储每个节点的输出结果，key 为 node_id
    # 使用 Annotated 支持并发更新（多个节点同时写入不同的 key）
    node_outputs: Annotated[Dict[str, Any], operator.or_] = Field(
        default_factory=dict,
        description="节点执行结果"
    )
    
    # 全局上下文变量
    context: Annotated[Dict[str, Any], operator.or_] = Field(
        default_factory=dict,
        description="全局上下文"
    )
    
    # 历史消息 (用于 Chat 场景) - 使用 operator.add 追加消息
    messages: Annotated[List[Any], operator.add] = Field(
        default_factory=list,
        description="消息历史"
    )
    
    # 循环控制状态
    loop_counters: Annotated[Dict[str, int], operator.or_] = Field(
        default_factory=dict,
        description="循环计数器，key 为循环节点ID"
    )
    loop_outputs: Annotated[Dict[str, List[Any]], operator.or_] = Field(
        default_factory=dict,
        description="循环输出，存储每次迭代的结果"
    )
    
    # 条件分支决策记录
    branch_decisions: Annotated[Dict[str, str], operator.or_] = Field(
        default_factory=dict,
        description="分支决策记录"
    )
    
    # 当前执行的节点ID - 默认空字符串
    # 注意：current_node 不使用 operator.or_，因为字符串不支持 | 操作
    # 在并行执行时，current_node 会使用 "last write wins" 策略
    current_node: str = Field(
        default="",
        description="当前执行的节点ID"
    )
    
    # ==================== 智能体协作字段 ====================
    # 用于多智能体协作通信
    
    # 协作请求队列 - 存储智能体发起的协作请求
    collaboration_requests: Annotated[List[Dict[str, Any]], operator.add] = Field(
        default_factory=list,
        description="协作请求队列，格式: [{'request_id': str, 'from_agent': str, 'to_agent': str, 'task': str, 'context': dict}]"
    )
    
    # 协作响应存储 - 存储其他智能体的响应结果
    collaboration_responses: Annotated[Dict[str, Any], operator.or_] = Field(
        default_factory=dict,
        description="协作响应存储，key 为 request_id，value 为响应结果"
    )
    
    # 智能体工作记忆 - 存储各智能体的临时状态
    agent_memory: Annotated[Dict[str, Any], operator.or_] = Field(
        default_factory=dict,
        description="智能体工作记忆，key 为 agent_id，value 为记忆数据"
    )
    
    # 工具调用记录 - 记录智能体的工具调用历史
    tool_call_history: Annotated[List[Dict[str, Any]], operator.add] = Field(
        default_factory=list,
        description="工具调用历史，格式: [{'agent_id': str, 'tool': str, 'input': dict, 'output': dict, 'timestamp': str}]"
    )