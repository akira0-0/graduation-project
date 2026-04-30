"""
情感分析智能体节点（增强版 V2）
继承 BaseNode，集成 SentimentAnalysisAgent 的功能

增强功能：
- LLM 深度语义理解：使用 LLM 进行上下文感知的情感分析
- 多维度分析：情感强度、情感原因、情感对象、情绪细分
- 智能归类：自动识别主题、观点、关键信息
- 情感趋势预测：基于历史数据预测情感走向
- 关键洞察提取：自动提取关键洞察和可操作建议

V2 新特性：
- ReAct 推理循环：自动规划-执行-反思迭代
- 工具调用能力：6 个专业情感分析工具
- 智能体协作：支持通过工作流状态协作
- 降级策略：V2 Agent 失败时自动回退到 V1
"""
from typing import Any, Dict, Optional
from .base import BaseNode
from ..core.schema import NodeDefinition, WorkflowState
from ..agents.sentiment_agent import SentimentAnalysisAgent
from ..agents.sentiment_agent_v2 import SentimentAgentV2
from ..utils.logger import get_logger

logger = get_logger("sentiment_agent_node")


class SentimentAgentNode(BaseNode):
    """情感分析智能体节点（增强版 V2）
    
    支持 V2 Agent（ReAct）和 V1 Agent（降级）两种模式：
    - V2 模式：使用 ReAct 推理循环，自动选择工具
    - V1 模式：原有的深度分析方法，作为降级方案
    """
    
    def __init__(self, node_def: NodeDefinition):
        """
        初始化情感分析智能体节点
        
        Args:
            node_def: 节点定义
        """
        super().__init__(node_def)
        self.agent = None
        self.agent_v2 = None
        self.use_v2 = True  # 默认使用 V2 Agent
        
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        执行情感分析（增强版 V2）
        
        支持两种模式：
        1. V2 模式（默认）：ReAct Agent 自动选择工具
        2. V1 模式（降级）：原有深度分析方法
        
        Args:
            state: 工作流状态
            
        Returns:
            情感分析结果
        """
        logger.info(f"执行情感分析智能体节点: {self.node_id}")
        
        try:
            # 获取输入数据（支持引用前序节点的输出）
            data_ref = self.get_input_value(state, "data")
            analysis_type = self.get_input_value(state, "analysis_type") or "sentiment"
            language = self.get_input_value(state, "language") or "zh"
            detail_level = self.get_input_value(state, "detail_level") or "detailed"
            
            # V2 Agent 参数
            use_v2_agent = self.get_input_value(state, "use_v2_agent")
            if use_v2_agent is None:
                use_v2_agent = self.use_v2  # 默认使用 V2
            
            # V1 增强参数
            use_deep_analysis = self.get_input_value(state, "use_deep_analysis")
            if use_deep_analysis is None:
                use_deep_analysis = True
            
            extract_insights = self.get_input_value(state, "extract_insights")
            if extract_insights is None:
                extract_insights = True
            
            topic = self.get_input_value(state, "topic")
            task_description = self.get_input_value(state, "task_description")  # V2 自定义任务描述
            
            # 解析数据
            data = self._parse_input_data(data_ref)
            
            if not data:
                logger.warning("没有输入数据，返回默认结果")
                return self._create_no_data_result()
            
            logger.info(f"开始分析 {len(data)} 条数据，V2 Agent: {use_v2_agent}")
            
            # 从状态中获取 workflow_id
            workflow_id = state.workflow_id
            
            # 选择 Agent 版本执行分析
            if use_v2_agent:
                result = self._execute_v2_agent(
                    state=state,
                    workflow_id=workflow_id,
                    data=data,
                    task_description=task_description,
                    topic=topic
                )
            else:
                result = self._execute_v1_agent(
                    workflow_id=workflow_id,
                    data=data,
                    use_deep_analysis=use_deep_analysis,
                    topic=topic,
                    extract_insights=extract_insights
                )
            
            # 添加元信息
            result["analysis_type"] = analysis_type
            result["language"] = language
            result["detail_level"] = detail_level
            result["data_count"] = len(data)
            
            return result
            
        except Exception as e:
            logger.error(f"情感分析失败: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "analysis_result": {},
                "message": f"情感分析失败: {str(e)}"
            }
    
    def _parse_input_data(self, data_ref: Any) -> list:
        """解析输入数据"""
        if isinstance(data_ref, str) and data_ref.startswith("$"):
            logger.warning(f"数据引用未解析: {data_ref}，请检查配置")
            return []
        elif isinstance(data_ref, list):
            return data_ref
        elif isinstance(data_ref, dict):
            # 支持不同上游节点的输出格式
            if "filtered_data" in data_ref:
                return data_ref.get("filtered_data", [])
            elif "collected_data" in data_ref:
                return data_ref.get("collected_data", [])
            elif "analyzed_data" in data_ref:
                return data_ref.get("analyzed_data", [])
            elif "data" in data_ref:
                return data_ref.get("data", [])
            else:
                logger.warning(f"无法识别的数据格式，可用键: {list(data_ref.keys())}")
                return []
        else:
            logger.warning(f"数据格式不正确: {type(data_ref)}，使用空列表")
            return []
    
    def _create_no_data_result(self) -> Dict[str, Any]:
        """创建无数据结果"""
        return {
            "status": "no_data",
            "message": "没有输入数据进行分析",
            "analysis_result": {
                "total_count": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "sentiment_distribution": {
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0
                }
            }
        }
    
    def _execute_v2_agent(
        self,
        state: WorkflowState,
        workflow_id: str,
        data: list,
        task_description: Optional[str] = None,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用 V2 Agent 执行分析
        
        Args:
            state: 工作流状态
            workflow_id: 工作流 ID
            data: 输入数据
            task_description: 任务描述
            topic: 分析主题
        
        Returns:
            分析结果
        """
        logger.info("使用 V2 Agent (ReAct) 执行分析")
        
        try:
            # 初始化 V2 Agent
            if self.agent_v2 is None:
                self.agent_v2 = SentimentAgentV2(
                    workflow_id=workflow_id or "default",
                    max_iterations=10,
                    fallback_enabled=True
                )
            
            # 构建任务描述
            if task_description is None:
                task_description = "对这些数据进行全面的情感分析"
                if topic:
                    task_description += f"，分析主题：{topic}"
            
            # 准备上下文
            context = {
                "topic": topic,
                "workflow_id": workflow_id
            }
            
            # 检查协作请求
            collaboration_result = self._check_collaboration(state)
            if collaboration_result:
                context["collaboration"] = collaboration_result
            
            # 执行分析
            result = self.agent_v2.analyze(
                data=data,
                task_description=task_description,
                context=context
            )
            
            # 获取工作记忆
            working_memory = self.agent_v2.get_working_memory()
            
            # 更新状态中的工具调用历史
            tool_calls = result.get("tools_used", [])
            
            # 构建返回结果
            return {
                "status": "success",
                "analysis_method": result.get("analysis_method", "react_agent_v2"),
                "analysis_result": result.get("parsed_result", result.get("output", {})),
                "tools_used": tool_calls,
                "iterations": result.get("iterations", 0),
                "working_memory": working_memory,
                "fallback_reason": result.get("fallback_reason"),
                "message": f"V2 Agent 分析完成，使用 {len(tool_calls)} 个工具"
            }
            
        except Exception as e:
            logger.error(f"V2 Agent 执行失败: {e}")
            # V2 Agent 内部已经有降级，如果到这里说明完全失败
            return {
                "status": "error",
                "analysis_method": "react_agent_v2_failed",
                "error": str(e),
                "message": f"V2 Agent 执行失败: {str(e)}"
            }
    
    def _execute_v1_agent(
        self,
        workflow_id: str,
        data: list,
        use_deep_analysis: bool,
        topic: Optional[str],
        extract_insights: bool
    ) -> Dict[str, Any]:
        """
        使用 V1 Agent 执行分析（原有方法）
        
        Args:
            workflow_id: 工作流 ID
            data: 输入数据
            use_deep_analysis: 是否深度分析
            topic: 分析主题
            extract_insights: 是否提取洞察
        
        Returns:
            分析结果
        """
        logger.info("使用 V1 Agent 执行分析")
        
        # 初始化智能体（启用 LLM 增强功能）
        self.agent = SentimentAnalysisAgent(
            workflow_id=workflow_id,
            auto_save=bool(workflow_id),
            use_llm=use_deep_analysis
        )
        
        # 根据模式选择分析方法
        if use_deep_analysis:
            logger.info("使用深度分析模式")
            result = self.agent.analyze_sentiment_deep(
                data=data,
                topic=topic,
                extract_insights=extract_insights
            )
        else:
            logger.info("使用基础分析模式")
            result = self.agent.analyze_sentiment(data)
        
        # 计算增强统计
        deep_summary = result.get("deep_summary", {})
        insights = result.get("insights", {})
        trend_prediction = result.get("trend_prediction", {})
        
        return {
            "status": "success",
            "analysis_method": "deep" if use_deep_analysis else "basic",
            "analysis_result": result,
            "deep_summary": deep_summary,
            "insights": insights,
            "trend_prediction": trend_prediction,
            "message": f"V1 Agent 分析完成（{'深度分析' if use_deep_analysis else '基础分析'}）"
        }
    
    def _check_collaboration(self, state: WorkflowState) -> Optional[Dict[str, Any]]:
        """
        检查协作请求
        
        检查工作流状态中是否有来自其他智能体的协作请求
        
        Args:
            state: 工作流状态
        
        Returns:
            协作信息或 None
        """
        collaboration_requests = state.collaboration_requests
        
        if not collaboration_requests:
            return None
        
        # 查找发往本智能体的协作请求
        for request in collaboration_requests:
            to_agent = request.get("to_agent", "")
            if "sentiment" in to_agent.lower():
                return {
                    "request_id": request.get("request_id"),
                    "from_agent": request.get("from_agent"),
                    "task": request.get("task"),
                    "context": request.get("context", {})
                }
        
        return None
    
    def _record_tool_call(
        self,
        state: WorkflowState,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Dict[str, Any]
    ) -> None:
        """
        记录工具调用到工作流状态
        
        Args:
            state: 工作流状态
            tool_name: 工具名称
            tool_input: 工具输入
            tool_output: 工具输出
        """
        from datetime import datetime
        
        tool_call = {
            "agent_id": self.node_id,
            "tool": tool_name,
            "input": tool_input,
            "output": tool_output,
            "timestamp": datetime.now().isoformat()
        }
        
        # 注意：这里需要通过返回值更新状态，而不是直接修改
        # 工具调用历史会在节点输出中合并到 state.tool_call_history
        logger.info(f"记录工具调用: {tool_name}")