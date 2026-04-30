"""
情感分析智能体 V2 - 真正的 AI Agent 实现
基于 LangChain create_agent 和 ReAct 推理循环

核心特性：
- ReAct 推理循环：Thought → Action → Observation → Continue
- 工具调用能力：通过 @tool 装饰器定义可调用工具
- 记忆系统：短期工作记忆 + 长期知识存储
- 降级策略：失败时自动回退到原有 SentimentAnalysisAgent

注意：使用 langchain 1.2.6 的新 API (create_agent + StateGraph)
"""
from typing import List, Dict, Any, Optional, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
import os
import json

from ..tools.sentiment_tools import SENTIMENT_TOOLS
from ..utils.logger import get_logger

logger = get_logger("sentiment_agent_v2")


class SentimentAgentV2:
    """
    情感分析智能体 V2 - 真正的 AI Agent
    
    使用 LangChain create_agent 机制实现：
    1. 工具定义：6 个专业情感分析工具
    2. ReAct 循环：自动推理-行动-观察迭代
    3. 记忆系统：工作流级别的上下文保持
    4. 降级策略：失败时回退到 V1 实现
    """
    
    # 系统提示词 - 定义智能体角色和能力
    SYSTEM_PROMPT = """你是一个专业的情感分析智能体，具备深度情感分析能力。

## 你的角色
你是一个 AI 情感分析专家，能够理解复杂的情感语义，识别隐含情绪，并提供专业的分析洞察。

## 可用工具
你可以使用以下工具完成任务：

1. **analyze_text_sentiment**: 分析单条文本的情感倾向
   - 输入：文本内容、可选上下文
   - 输出：情感标签、置信度、情绪细分、关键短语

2. **batch_analyze_sentiment**: 批量分析多条文本
   - 输入：文本列表
   - 输出：每条文本分析结果 + 统计汇总

3. **extract_insights**: 从分析数据中提取关键洞察
   - 输入：已分析数据、主题
   - 输出：主要主题、痛点、亮点、建议

4. **predict_trend**: 预测情感趋势
   - 输入：历史数据
   - 输出：趋势方向、预测、建议

5. **query_domain_knowledge**: 查询领域知识
   - 输入：查询关键词
   - 输出：相关领域知识、案例模式

6. **update_memory**: 更新智能体记忆
   - 输入：键名、值、记忆类型
   - 输出：操作结果

## 工作流程
1. **分析任务**：理解用户需求，确定分析目标
2. **选择工具**：根据任务选择合适的工具
3. **执行分析**：调用工具获取结果
4. **综合判断**：基于结果做出综合判断
5. **输出结果**：提供结构化的分析报告

## 分析原则
- 客观中立：不带偏见地分析情感
- 上下文敏感：考虑语境对情感的影响
- 多维度分析：综合情感、情绪、原因等多角度
- 可解释性：提供分析依据和理由

## 输出格式
始终以结构化的 JSON 格式返回结果，包含：
- sentiment: 情感标签
- confidence: 置信度
- reasoning: 分析推理过程
- tools_used: 使用的工具列表
- insights: 关键洞察
"""

    def __init__(
        self,
        workflow_id: str,
        max_iterations: int = 10,
        fallback_enabled: bool = True
    ):
        """
        初始化智能体 V2
        
        Args:
            workflow_id: 工作流 ID
            max_iterations: ReAct 循环最大迭代次数
            fallback_enabled: 是否启用降级策略
        """
        self.workflow_id = workflow_id
        self.max_iterations = max_iterations
        self.fallback_enabled = fallback_enabled
        
        # 工作记忆：存储对话历史和中间结果
        self.working_memory: List[Dict[str, Any]] = []
        
        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
            openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0.3
        )
        
        # 创建 Agent
        self._setup_agent()
        
        # 延迟初始化降级 Agent
        self._fallback_agent = None
        
        logger.info(f"SentimentAgentV2 初始化完成, workflow_id={workflow_id}")
    
    def _setup_agent(self):
        """设置 Agent"""
        try:
            # 使用 langgraph.prebuilt 的 create_react_agent API
            self.agent = create_react_agent(
                model=self.llm,
                tools=SENTIMENT_TOOLS,
                state_modifier=self.SYSTEM_PROMPT
            )
            logger.info("Agent 设置完成")
            
        except Exception as e:
            logger.error(f"Agent 设置失败: {e}")
            raise
    
    def _get_fallback_agent(self):
        """获取降级 Agent（延迟加载）"""
        if self._fallback_agent is None and self.fallback_enabled:
            try:
                from .sentiment_agent import SentimentAnalysisAgent
                self._fallback_agent = SentimentAnalysisAgent(
                    workflow_id=self.workflow_id,
                    auto_save=True,
                    use_llm=True
                )
                logger.info("降级 Agent 加载完成")
            except Exception as e:
                import traceback
                logger.error(f"降级 Agent 加载失败: {e}\n{traceback.format_exc()}")
        return self._fallback_agent
    
    def analyze(
        self,
        data: List[Dict[str, Any]],
        task_description: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行情感分析（核心方法）
        
        使用 Agent 自动选择和调用工具，完成复杂分析任务。
        
        Args:
            data: 待分析的数据列表
            task_description: 任务描述（可选）
            context: 上下文信息（可选）
        
        Returns:
            结构化分析结果
        """
        logger.info(f"开始 Agent 分析，数据量: {len(data)}")
        
        # 构建输入
        if task_description is None:
            task_description = "对这些数据进行全面的情感分析"
        
        input_text = f"""
任务：{task_description}

数据概览：
- 数据量：{len(data)} 条
- 数据样例：{json.dumps(data[:3], ensure_ascii=False, indent=2) if data else '无数据'}

请使用可用工具完成分析，并提供结构化的分析结果。
"""
        
        # 构建消息
        messages = [HumanMessage(content=input_text)]
        if context:
            messages.insert(0, SystemMessage(content=f"上下文信息：{json.dumps(context, ensure_ascii=False)}"))
        
        try:
            # 执行 Agent
            result = self.agent.invoke({"messages": messages})
            
            # 提取输出
            output_messages = result.get("messages", [])
            output = ""
            tools_used = []
            
            for msg in output_messages:
                if isinstance(msg, AIMessage):
                    output = msg.content
                    # 提取工具调用
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tools_used.append({
                                "tool": tc.get("name", "unknown"),
                                "input": tc.get("args", {}),
                            })
            
            # 记录到工作记忆
            self.working_memory.append({
                "task": task_description,
                "data_count": len(data),
                "tools_used": tools_used,
                "result_summary": str(output)[:500]
            })
            
            # 构建返回结果
            analysis_result = {
                "status": "success",
                "analysis_method": "langchain_agent_v2",
                "output": output,
                "tools_used": tools_used,
                "workflow_id": self.workflow_id
            }
            
            # 尝试解析结构化输出
            try:
                # 如果输出包含 JSON，提取它
                if "{" in output and "}" in output:
                    json_start = output.find("{")
                    json_end = output.rfind("}") + 1
                    json_str = output[json_start:json_end]
                    parsed = json.loads(json_str)
                    analysis_result["parsed_result"] = parsed
            except json.JSONDecodeError:
                pass
            
            logger.info(f"Agent 分析完成，使用了 {len(tools_used)} 个工具")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Agent 分析失败: {e}")
            
            # 尝试降级
            if self.fallback_enabled:
                logger.info("尝试降级到 V1 Agent...")
                return self._fallback_analyze(data, task_description, str(e))
            
            return {
                "status": "error",
                "error": str(e),
                "analysis_method": "langchain_agent_v2_failed"
            }
    
    def _fallback_analyze(
        self,
        data: List[Dict[str, Any]],
        task_description: str,
        error: str
    ) -> Dict[str, Any]:
        """降级分析：使用原有 Agent"""
        fallback_agent = self._get_fallback_agent()
        
        if fallback_agent is None:
            return {
                "status": "error",
                "error": f"主 Agent 失败: {error}，且降级 Agent 不可用",
                "analysis_method": "fallback_failed"
            }
        
        try:
            # 调用原有分析方法
            result = fallback_agent.analyze_sentiment_deep(data)
            
            return {
                "status": "success",
                "analysis_method": "fallback_v1",
                "fallback_reason": error,
                "analysis_result": result,
                "workflow_id": self.workflow_id
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"主 Agent 失败: {error}，降级 Agent 也失败: {str(e)}",
                "analysis_method": "all_failed"
            }
    
    def analyze_single(
        self,
        text: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析单条文本
        
        直接调用 analyze_text_sentiment 工具
        
        Args:
            text: 待分析文本
            context: 上下文信息
        
        Returns:
            分析结果
        """
        logger.info(f"分析单条文本: {text[:50]}...")
        
        # 构建任务
        task = f"分析以下文本的情感：{text}"
        if context:
            task += f"\n上下文：{context}"
        
        return self.analyze(
            data=[{"content": text, "context": context}],
            task_description=task
        )
    
    def batch_analyze(
        self,
        texts: List[str],
        extract_insights: bool = True,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量分析文本
        
        使用 batch_analyze_sentiment 工具，可选择提取洞察
        
        Args:
            texts: 文本列表
            extract_insights: 是否提取洞察
            topic: 洞察主题
        
        Returns:
            批量分析结果
        """
        logger.info(f"批量分析 {len(texts)} 条文本")
        
        data = [{"content": t} for t in texts]
        task = f"批量分析 {len(texts)} 条文本的情感倾向"
        
        if extract_insights and topic:
            task += f"，并基于主题 '{topic}' 提取关键洞察"
        
        return self.analyze(
            data=data,
            task_description=task,
            context={"batch_size": len(texts), "topic": topic}
        )
    
    def predict_trend(
        self,
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        预测情感趋势
        
        使用 predict_trend 工具分析历史数据
        
        Args:
            historical_data: 历史分析数据
        
        Returns:
            趋势预测结果
        """
        logger.info(f"预测趋势，历史数据量: {len(historical_data)}")
        
        return self.analyze(
            data=historical_data,
            task_description="基于历史情感分析数据，预测未来情感趋势"
        )
    
    def query_knowledge(self, query: str) -> Dict[str, Any]:
        """
        查询领域知识
        
        使用 query_domain_knowledge 工具
        
        Args:
            query: 查询关键词
        
        Returns:
            相关领域知识
        """
        logger.info(f"查询领域知识: {query}")
        
        # 直接使用工具
        from ..tools.sentiment_tools import query_domain_knowledge
        
        result = query_domain_knowledge.invoke({
            "query": query,
            "workflow_id": self.workflow_id
        })
        
        return result
    
    def update_knowledge(
        self,
        key: str,
        value: Any,
        memory_type: str = "domain_knowledge"
    ) -> Dict[str, Any]:
        """
        更新领域知识
        
        使用 update_memory 工具
        
        Args:
            key: 知识键名
            value: 知识值
            memory_type: 记忆类型
        
        Returns:
            更新结果
        """
        logger.info(f"更新领域知识: {key}")
        
        # 直接使用工具
        from ..tools.sentiment_tools import update_memory
        
        result = update_memory.invoke({
            "key": key,
            "value": value,
            "memory_type": memory_type,
            "workflow_id": self.workflow_id
        })
        
        return result
    
    def get_working_memory(self) -> List[Dict[str, Any]]:
        """获取工作记忆"""
        return self.working_memory.copy()
    
    def clear_working_memory(self):
        """清空工作记忆"""
        self.working_memory = []
        logger.info("工作记忆已清空")


# 便捷函数：创建智能体实例
def create_sentiment_agent_v2(
    workflow_id: str,
    max_iterations: int = 10,
    fallback_enabled: bool = True
) -> SentimentAgentV2:
    """
    创建情感分析智能体 V2 实例
    
    Args:
        workflow_id: 工作流 ID
        max_iterations: 最大迭代次数
        fallback_enabled: 是否启用降级
    
    Returns:
        SentimentAgentV2 实例
    """
    return SentimentAgentV2(
        workflow_id=workflow_id,
        max_iterations=max_iterations,
        fallback_enabled=fallback_enabled
    )