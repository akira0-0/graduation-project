"""
智能体节点基类
提供类似 CrewAI 的角色定义能力，但使用 LangGraph 执行
"""
from abc import abstractmethod
from typing import Any, Dict, Optional
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from .base import BaseNode
from ..core.schema import NodeDefinition, WorkflowState
from ..utils.logger import get_logger

logger = get_logger("agent_node_base")


class AgentNodeBase(BaseNode):
    """
    智能体节点基类
    
    提供 CrewAI 风格的角色定义，但使用 LangChain 直接调用 LLM。
    继承此类的节点可以定义角色、目标和背景故事，实现智能体行为。
    """
    
    def __init__(self, node_def: NodeDefinition):
        """
        初始化智能体节点
        
        Args:
            node_def: 节点定义
        """
        super().__init__(node_def)
        
        # 从配置中提取智能体角色信息
        self.role = node_def.config.agent_role or "通用助手"
        self.goal = node_def.config.agent_goal or "完成任务"
        self.backstory = node_def.config.agent_backstory or ""
        
        # 初始化 LLM（延迟初始化，避免在导入时创建）
        self._llm = None
        
        logger.debug(
            f"初始化智能体节点",
            node_id=self.node_id,
            role=self.role,
            goal=self.goal
        )
    
    @property
    def llm(self) -> ChatOpenAI:
        """
        获取 LLM 实例（延迟初始化）
        
        Returns:
            ChatOpenAI 实例
        """
        if self._llm is None:
            self._llm = self._init_llm()
        return self._llm
    
    def _init_llm(self) -> ChatOpenAI:
        """
        初始化 LLM
        
        Returns:
            ChatOpenAI 实例
        """
        from ..config import get_llm_settings
        
        model = self.config.params.get("model")
        temperature = self.config.params.get("temperature")
        
        # 使用统一配置管理
        llm_settings = get_llm_settings(model_name=model, temperature=temperature)
        return ChatOpenAI(**llm_settings.to_langchain_kwargs())
    
    def _build_system_prompt(self) -> str:
        """
        构建系统提示词
        
        Returns:
            系统提示词字符串
        """
        prompt_parts = [f"你是一个{self.role}。"]
        
        if self.goal:
            prompt_parts.append(f"\n目标: {self.goal}")
        
        if self.backstory:
            prompt_parts.append(f"\n背景: {self.backstory}")
        
        prompt_parts.append("\n\n请根据以上设定完成任务。")
        
        return "".join(prompt_parts)
    
    def call_llm(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        include_system_prompt: bool = True
    ) -> str:
        """
        调用 LLM
        
        Args:
            prompt: 用户提示词
            context: 额外上下文（可选）
            include_system_prompt: 是否包含系统提示词
            
        Returns:
            LLM 响应内容
        """
        messages = []
        
        # 添加系统提示词
        if include_system_prompt:
            system_prompt = self._build_system_prompt()
            
            # 如果有额外上下文，添加到系统提示词中
            if context:
                context_str = "\n\n上下文信息:\n"
                for key, value in context.items():
                    context_str += f"- {key}: {value}\n"
                system_prompt += context_str
            
            messages.append(SystemMessage(content=system_prompt))
        
        # 添加用户消息
        messages.append(HumanMessage(content=prompt))
        
        try:
            response = self.llm.invoke(messages)
            logger.debug(
                "LLM 调用成功",
                node_id=self.node_id,
                role=self.role,
                response_length=len(response.content)
            )
            return response.content
        except Exception as e:
            logger.error(
                f"LLM 调用失败: {str(e)}",
                node_id=self.node_id,
                role=self.role
            )
            raise
    
    def call_llm_with_history(
        self,
        prompt: str,
        history: list,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        带对话历史调用 LLM
        
        Args:
            prompt: 用户提示词
            history: 对话历史列表
            context: 额外上下文
            
        Returns:
            LLM 响应内容
        """
        messages = [SystemMessage(content=self._build_system_prompt())]
        
        # 添加上下文
        if context:
            context_str = "\n\n上下文信息:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"
            messages.append(SystemMessage(content=context_str))
        
        # 添加历史消息
        for msg in history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(SystemMessage(content=msg.get("content", "")))
        
        # 添加当前用户消息
        messages.append(HumanMessage(content=prompt))
        
        response = self.llm.invoke(messages)
        return response.content
    
    @abstractmethod
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        执行节点逻辑（子类必须实现）
        
        Args:
            state: 工作流当前状态
            
        Returns:
            节点输出数据
        """
        pass
    
    def get_context_from_state(self, state: WorkflowState) -> Dict[str, Any]:
        """
        从工作流状态中提取上下文信息
        
        Args:
            state: 工作流状态
            
        Returns:
            上下文字典
        """
        context = {}
        
        # 从上下文变量中获取
        if state.context:
            context.update(state.context)
        
        # 从节点输出中获取（最新的几个节点）
        if state.node_outputs:
            # 只取最后3个节点的输出作为上下文，避免上下文过长
            recent_outputs = dict(list(state.node_outputs.items())[-3:])
            for node_id, output in recent_outputs.items():
                if isinstance(output, dict):
                    context[f"previous_{node_id}"] = output
                else:
                    context[f"previous_{node_id}"] = str(output)
        
        return context