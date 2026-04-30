"""
规划智能体
分析用户自然语言输入，拆解任务并规划工作流
"""
import json
import os
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..utils.logger import get_logger

logger = get_logger("planning_agent")


class TaskPlan:
    """任务规划"""
    
    def __init__(
        self,
        main_task: str,
        subtasks: List[Dict[str, Any]],
        workflow_type: str,
        required_agents: List[str],
        estimated_steps: int,
        complexity: str
    ):
        self.main_task = main_task
        self.subtasks = subtasks
        self.workflow_type = workflow_type
        self.required_agents = required_agents
        self.estimated_steps = estimated_steps
        self.complexity = complexity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "main_task": self.main_task,
            "subtasks": self.subtasks,
            "workflow_type": self.workflow_type,
            "required_agents": self.required_agents,
            "estimated_steps": self.estimated_steps,
            "complexity": self.complexity
        }


class PlanningAgent:
    """
    规划智能体
    分析用户输入的自然语言，理解意图，拆解任务，规划工作流步骤
    """
    
    def __init__(self, model_name: str = None):
        """初始化规划智能体"""
        from ..config import get_settings, get_llm_settings
        
        settings = get_settings()
        llm_settings = get_llm_settings(model_name=model_name or settings.llm_model, temperature=0.3)
        self.llm = ChatOpenAI(**llm_settings.to_langchain_kwargs())
        
        self.system_prompt = self._get_planning_prompt()
    
    def _get_planning_prompt(self) -> str:
        """获取规划提示词"""
        return """你是一个专业的工作流规划智能体，专门负责分析用户的自然语言需求，拆解任务，并规划舆情分析工作流。

你的职责是：
1. 理解用户的自然语言输入
2. 识别用户的核心需求和意图
3. 将复杂任务拆解为可执行的子任务
4. 确定需要使用的智能体类型
5. 规划工作流的执行步骤
6. 评估任务的复杂度

**可用的智能体类型：**
- DataCollectionAgent: 数据收集智能体，从互联网、知识库等数据源收集信息
- FilterAgent: 信息过滤智能体，根据关键词、置信度等条件过滤数据
- SentimentAgent: 情感分析智能体，分析文本的情感倾向
- ReportAgent: 报告生成智能体，生成分析报告

**工作流类型：**
- public_opinion_analysis: 舆情分析工作流（数据收集→过滤→情感分析→报告生成）
- data_collection: 数据收集工作流（仅收集数据）
- sentiment_analysis: 情感分析工作流（对已有数据进行情感分析）
- custom: 自定义工作流

**输出格式要求（JSON）：**
{{
  "main_task": "用户的主要任务描述",
  "workflow_type": "工作流类型",
  "subtasks": [
    {{
      "task_id": "task_1",
      "description": "子任务描述",
      "agent_type": "智能体类型",
      "parameters": {{
        "param1": "value1"
      }},
      "dependencies": ["前置任务ID"]
    }}
  ],
  "required_agents": ["智能体列表"],
  "estimated_steps": 预估步骤数,
  "complexity": "simple|medium|complex"
}}

**示例输入：**
"分析DeepSeek用户在Twitter上的评价"

**示例输出：**
{{
  "main_task": "分析DeepSeek在Twitter上的用户评价",
  "workflow_type": "public_opinion_analysis",
  "subtasks": [
    {{
      "task_id": "collect_data",
      "description": "从Twitter收集DeepSeek相关的用户评价",
      "agent_type": "DataCollectionAgent",
      "parameters": {{
        "topic": "DeepSeek用户评价",
        "sources": ["twitter"],
        "max_results": 50,
        "time_range": "month"
      }},
      "dependencies": []
    }},
    {{
      "task_id": "filter_data",
      "description": "过滤低质量和无关的数据",
      "agent_type": "FilterAgent",
      "parameters": {{
        "data_reference": "$collect_data",
        "filters": {{
          "min_length": 20,
          "min_confidence": 0.6,
          "exclude_duplicates": true
        }}
      }},
      "dependencies": ["collect_data"]
    }},
    {{
      "task_id": "analyze_sentiment",
      "description": "分析用户评价的情感倾向",
      "agent_type": "SentimentAgent",
      "parameters": {{
        "data_reference": "$filter_data",
        "analysis_type": "sentiment",
        "language": "zh"
      }},
      "dependencies": ["filter_data"]
    }},
    {{
      "task_id": "generate_report",
      "description": "生成DeepSeek用户评价分析报告",
      "agent_type": "ReportAgent",
      "parameters": {{
        "report_type": "sentiment_analysis",
        "template": "detailed"
      }},
      "dependencies": ["analyze_sentiment"]
    }}
  ],
  "required_agents": ["DataCollectionAgent", "FilterAgent", "SentimentAgent", "ReportAgent"],
  "estimated_steps": 4,
  "complexity": "medium"
}}

现在请分析以下用户输入，生成任务规划："""
    
    def analyze_intent(self, user_input: str) -> TaskPlan:
        """
        分析用户意图并生成任务规划
        
        Args:
            user_input: 用户输入的自然语言
            
        Returns:
            TaskPlan: 任务规划对象
        """
        logger.info("开始分析用户意图", user_input=user_input[:100])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("user", "{input}")
        ])
        
        chain = prompt | self.llm | JsonOutputParser()
        
        try:
            result = chain.invoke({"input": user_input})
            
            # 创建任务规划对象
            task_plan = TaskPlan(
                main_task=result.get("main_task", ""),
                subtasks=result.get("subtasks", []),
                workflow_type=result.get("workflow_type", "custom"),
                required_agents=result.get("required_agents", []),
                estimated_steps=result.get("estimated_steps", 1),
                complexity=result.get("complexity", "medium")
            )
            
            logger.info(
                "任务规划完成",
                workflow_type=task_plan.workflow_type,
                subtasks_count=len(task_plan.subtasks),
                complexity=task_plan.complexity
            )
            
            return task_plan
            
        except Exception as e:
            logger.error("任务规划失败", error=str(e))
            # 返回默认规划
            return TaskPlan(
                main_task=user_input,
                subtasks=[{
                    "task_id": "default_task",
                    "description": user_input,
                    "agent_type": "DataCollectionAgent",
                    "parameters": {},
                    "dependencies": []
                }],
                workflow_type="custom",
                required_agents=["DataCollectionAgent"],
                estimated_steps=1,
                complexity="simple"
            )
    
    def optimize_plan(self, task_plan: TaskPlan) -> TaskPlan:
        """
        优化任务规划
        
        Args:
            task_plan: 原始任务规划
            
        Returns:
            TaskPlan: 优化后的任务规划
        """
        # 检查是否有可以并行的任务
        optimized_subtasks = []
        for subtask in task_plan.subtasks:
            # 如果没有依赖项，可以并行执行
            if not subtask.get("dependencies"):
                subtask["can_parallel"] = True
            optimized_subtasks.append(subtask)
        
        task_plan.subtasks = optimized_subtasks
        return task_plan
    
    def suggest_improvements(self, task_plan: TaskPlan) -> List[str]:
        """
        建议改进方案
        
        Args:
            task_plan: 任务规划
            
        Returns:
            List[str]: 改进建议列表
        """
        suggestions = []
        
        # 检查是否需要数据过滤
        if "DataCollectionAgent" in task_plan.required_agents and "FilterAgent" not in task_plan.required_agents:
            suggestions.append("建议在数据收集后添加过滤步骤，以提高数据质量")
        
        # 检查是否需要情感分析
        if task_plan.workflow_type == "public_opinion_analysis" and "SentimentAgent" not in task_plan.required_agents:
            suggestions.append("建议添加情感分析步骤，以获得更深入的洞察")
        
        # 检查是否有报告生成
        if "ReportAgent" not in task_plan.required_agents:
            suggestions.append("建议添加报告生成步骤，便于结果展示和分享")
        
        # 检查复杂度
        if task_plan.complexity == "complex" and task_plan.estimated_steps > 5:
            suggestions.append("工作流较复杂，建议拆分为多个子工作流")
        
        return suggestions
    
    def explain_plan(self, task_plan: TaskPlan) -> str:
        """
        生成任务规划的解释说明
        
        Args:
            task_plan: 任务规划
            
        Returns:
            str: 解释说明文本
        """
        explanation = f"## 任务规划说明\n\n"
        explanation += f"**主要任务**: {task_plan.main_task}\n\n"
        explanation += f"**工作流类型**: {task_plan.workflow_type}\n\n"
        explanation += f"**复杂度**: {task_plan.complexity}\n\n"
        explanation += f"**预估步骤数**: {task_plan.estimated_steps}\n\n"
        
        explanation += "### 子任务列表\n\n"
        for i, subtask in enumerate(task_plan.subtasks, 1):
            explanation += f"{i}. **{subtask['description']}**\n"
            explanation += f"   - 智能体类型: {subtask['agent_type']}\n"
            if subtask.get("dependencies"):
                explanation += f"   - 依赖任务: {', '.join(subtask['dependencies'])}\n"
            explanation += "\n"
        
        suggestions = self.suggest_improvements(task_plan)
        if suggestions:
            explanation += "### 改进建议\n\n"
            for i, suggestion in enumerate(suggestions, 1):
                explanation += f"{i}. {suggestion}\n"
        
        return explanation