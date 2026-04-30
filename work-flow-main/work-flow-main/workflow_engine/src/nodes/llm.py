"""
LLM 节点实现
支持调用大语言模型（如 DeepSeek、GPT 等），使用 Jinja2 风格的 Prompt 模板
"""
import os
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from .base import BaseNode
from ..core.schema import WorkflowState
from ..utils.logger import get_logger

logger = get_logger("llm_node")


class LLMNode(BaseNode):
    """
    LLM 节点
    支持调用 OpenAI 兼容的大语言模型，并使用 Prompt 模板
    """
    
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        执行 LLM 调用
        
        Args:
            state: 工作流当前状态
            
        Returns:
            包含 LLM 响应的字典
        """
        prompt_template = self.config.params.get("prompt", "")
        model_name = self.config.params.get("model", "deepseek-chat")
        
        logger.debug(
            f"执行 LLM 节点",
            node_id=self.node_id,
            model=model_name
        )
        
        # 准备模板变量
        variables = {}
        # 1. 注入全局上下文
        variables.update(state.context)
        # 2. 注入所有节点输出（扁平化或作为对象）
        # 简单起见，我们允许通过 node_id 直接访问
        variables.update(state.node_outputs)
        
        # 3. 处理特定的 inputs 映射（优先级更高）
        input_mapping = self.config.params.get("inputs", {})
        for k, v_ref in input_mapping.items():
            # 使用基类的引用解析方法
            variables[k] = self.get_input_value(state, k)
        
        # 渲染 Prompt
        try:
            # 简化的模板渲染，支持 {{variable}} 语法
            # 真正的实现应该使用 Jinja2
            rendered_prompt = prompt_template
            for key, val in variables.items():
                # 简单的字符串替换
                placeholder = "{{" + key + "}}"
                if placeholder in rendered_prompt:
                    rendered_prompt = rendered_prompt.replace(placeholder, str(val))
            
            logger.debug(f"渲染后的 Prompt: {rendered_prompt[:100]}...", node_id=self.node_id)
                    
        except Exception as e:
            logger.error(f"Prompt 渲染失败: {str(e)}", node_id=self.node_id)
            return {"error": f"Prompt 渲染失败: {str(e)}"}
            
        # 调用 LLM
        try:
            # 自动读取环境变量 OPENAI_API_BASE
            llm = ChatOpenAI(
                model=model_name,
                openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
                openai_api_key=os.environ.get("OPENAI_API_KEY"),
                temperature=0.7  # 默认温度参数
            )
            messages = [HumanMessage(content=rendered_prompt)]
            response = llm.invoke(messages)
            
            logger.info(f"LLM 调用成功", node_id=self.node_id, response_length=len(response.content))
            
            return {
                "content": response.content,
                "raw": response.dict()
            }
        except Exception as e:
            logger.error(f"LLM 调用失败: {str(e)}", node_id=self.node_id)
            return {"error": f"LLM 调用失败: {str(e)}"}