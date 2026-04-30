"""
AI对话服务
实现对话式工作流生成和调整功能
"""
import json
from typing import Optional, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..core.schema import WorkflowDefinition
from ..database.repositories import WorkflowRepository, ConversationRepository
from ..database.models import Workflow
from ..database.connection import get_session
from .workflow_service import WorkflowService
from ..planner.llm_planner import parse_workflow_json_output, WorkflowJSONProcessingError
from ..utils.logger import get_logger

logger = get_logger("ai_conversation_service")


class AIConversationService:
    """
    AI对话服务
    支持多轮对话生成和调整工作流
    """
    
    def __init__(
        self,
        workflow_service: Optional[WorkflowService] = None,
        model_name: str = "deepseek-chat"
    ):
        """
        初始化AI对话服务
        
        Args:
            workflow_service: 工作流服务
            model_name: LLM模型名称
        """
        from ..config import get_llm_settings
        
        # 使用统一配置管理初始化LLM
        llm_settings = get_llm_settings(model_name=model_name, temperature=0.7)
        self.llm = ChatOpenAI(**llm_settings.to_langchain_kwargs())
        
        # 初始化工作流服务
        if workflow_service:
            self.workflow_service = workflow_service
        else:
            session = get_session()
            workflow_repo = WorkflowRepository(session)
            conversation_repo = ConversationRepository(session)
            self.workflow_service = WorkflowService(
                workflow_repo=workflow_repo,
                conversation_repo=conversation_repo
            )
        
        self.conversation_repo = self.workflow_service.conversation_repo
    
    def start_conversation(
        self,
        user_intent: str,
        workflow_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        开始新的对话，生成初始工作流
        
        Args:
            user_intent: 用户意图描述
            workflow_type: 工作流类型（可选）
            
        Returns:
            包含工作流和对话信息的字典
        """
        logger.info("开始新对话", user_intent=user_intent[:50])
        
        # 生成工作流
        result = self.workflow_service.generate_workflow(
            intent=user_intent,
            save=True
        )
        
        workflow_id = result.get("workflow_id")
        workflow_def = result.get("workflow")
        
        # 检查工作流是否成功保存
        if not workflow_id:
            logger.error("工作流保存失败，workflow_id 为空")
            raise ValueError("工作流保存失败，无法获取 workflow_id")
        
        # 保存对话记录
        conversation = self.conversation_repo.create_conversation(
            workflow_id=workflow_id,
            user_message=user_intent,
            assistant_response=json.dumps(workflow_def.model_dump(), ensure_ascii=False),
            context={
                "type": "workflow_generation",
                "workflow_type": workflow_type,
                "iteration": 1
            }
        )
        
        logger.info("对话记录已保存",
                   conversation_id=conversation.id,
                   workflow_id=workflow_id)
        
        return {
            "conversation_id": conversation.id,
            "workflow_id": workflow_id,
            "workflow": workflow_def,
            "message": "工作流已生成，您可以继续对话来调整工作流"
        }
    
    def continue_conversation(
        self,
        workflow_id: str,
        user_message: str
    ) -> Dict[str, Any]:
        """
        继续对话，根据用户反馈调整工作流
        
        Args:
            workflow_id: 工作流ID
            user_message: 用户消息
            
        Returns:
            包含调整后的工作流和对话信息的字典
        """
        logger.info(f"继续对话: workflow_id={workflow_id}, message={user_message[:50]}")
        
        # 获取现有工作流
        workflow = self.workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"工作流不存在: {workflow_id}")
        
        # 获取对话历史
        history = self.conversation_repo.get_recent_by_workflow(workflow_id, limit=5)
        
        # 调整工作流
        adjusted_workflow = self._adjust_workflow_via_llm(
            current_workflow=workflow.definition,
            user_message=user_message,
            conversation_history=history
        )
        
        # 更新工作流
        updated_workflow = self.workflow_service.update_workflow_definition(
            workflow_id=workflow_id,
            definition=adjusted_workflow
        )
        
        # 保存对话记录
        conversation = self.conversation_repo.create_conversation(
            workflow_id=workflow_id,
            user_message=user_message,
            assistant_response=json.dumps(adjusted_workflow, ensure_ascii=False),
            context={
                "type": "workflow_adjustment",
                "iteration": len(history) + 1
            }
        )
        
        return {
            "conversation_id": conversation.id,
            "workflow_id": workflow_id,
            "workflow": WorkflowDefinition(**adjusted_workflow),
            "message": "工作流已根据您的反馈调整"
        }
    
    def _adjust_workflow_via_llm(
        self,
        current_workflow: Dict[str, Any],
        user_message: str,
        conversation_history: List[Any]
    ) -> Dict[str, Any]:
        """
        使用LLM调整工作流
        
        Args:
            current_workflow: 当前工作流定义
            user_message: 用户消息
            conversation_history: 对话历史
            
        Returns:
            调整后的工作流定义
        """
        # 构建对话历史文本
        history_text = self._format_conversation_history(conversation_history)
        
        # 构建提示词
        system_prompt = """你是一个工作流调整助手。你的任务是根据用户的反馈调整现有的工作流定义。

当前工作流定义（JSON格式）:
```json
{current_workflow}
```

对话历史:
{history_text}

调整要求：
1. 保持工作流的完整性和一致性
2. 只修改用户要求的部分
3. 确保节点ID唯一且连接正确
4. 输出必须是完整的JSON工作流定义

请输出调整后的完整工作流JSON定义。只输出JSON，不要有其他文字。"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{user_message}")
        ])
        
        # 调用LLM
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "current_workflow": json.dumps(current_workflow, ensure_ascii=False, indent=2),
                "history_text": history_text,
                "user_message": user_message
            })
            
            content = response.content if hasattr(response, "content") else str(response)
            adjusted_workflow = parse_workflow_json_output(content)
            
            logger.info("工作流调整成功")
            return adjusted_workflow
            
        except WorkflowJSONProcessingError as e:
            logger.error(
                "LLM调整工作流失败：JSON处理异常",
                stage=e.stage,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(f"LLM调整工作流失败: {e}")
            raise
    
    def _format_conversation_history(self, history: List[Any]) -> str:
        """
        格式化对话历史
        
        Args:
            history: 对话历史列表
            
        Returns:
            格式化的对话历史文本
        """
        if not history:
            return "无历史对话"
        
        formatted = []
        for conv in history[-3:]:  # 只取最近3轮
            formatted.append(f"用户: {conv.user_message}")
            formatted.append(f"助手: [工作流定义]")
        
        return "\n".join(formatted)
    
    def get_conversation_history(
        self,
        workflow_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取工作流的对话历史
        
        Args:
            workflow_id: 工作流ID
            limit: 返回的最大条数
            
        Returns:
            对话历史列表
        """
        conversations = self.conversation_repo.get_recent_by_workflow(
            workflow_id=workflow_id,
            limit=limit
        )
        
        return [
            {
                "id": conv.id,
                "user_message": conv.user_message,
                "assistant_response": conv.assistant_response,
                "timestamp": conv.timestamp.isoformat(),
                "context": conv.context
            }
            for conv in conversations
        ]
    
    def get_workflow_with_history(
        self,
        workflow_id: str
    ) -> Dict[str, Any]:
        """
        获取工作流及其对话历史
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            包含工作流和对话历史的字典
        """
        workflow = self.workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"工作流不存在: {workflow_id}")
        
        history = self.get_conversation_history(workflow_id)
        
        return {
            "workflow_id": workflow.id,
            "workflow": WorkflowDefinition(**workflow.definition),
            "conversation_history": history,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat()
        }
    
    def suggest_improvements(
        self,
        workflow_id: str
    ) -> Dict[str, Any]:
        """
        使用AI分析工作流并提供改进建议
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            包含改进建议的字典
        """
        workflow = self.workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"工作流不存在: {workflow_id}")
        
        workflow_def = workflow.definition
        
        system_prompt = """你是一个工作流优化专家。请分析以下工作流定义并提供改进建议。

工作流定义:
```json
{workflow}
```

请从以下几个方面提供具体的改进建议：
1. 节点配置优化
2. 流程顺序优化
3. 参数设置优化
4. 潜在问题提示

请以JSON格式输出建议:
{
  "improvements": [
    {
      "node_id": "节点ID",
      "type": "优化类型",
      "suggestion": "具体建议",
      "priority": "high/medium/low"
    }
  ],
  "overall_score": 1-10分,
  "summary": "总体评价"
}"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "请分析并提供改进建议")
        ])
        
        chain = prompt | self.llm | JsonOutputParser()
        
        try:
            suggestions = chain.invoke({
                "workflow": json.dumps(workflow_def, ensure_ascii=False, indent=2)
            })
            
            return {
                "workflow_id": workflow_id,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"生成改进建议失败: {e}")
            return {
                "workflow_id": workflow_id,
                "suggestions": {
                    "improvements": [],
                    "overall_score": 0,
                    "summary": f"分析失败: {str(e)}"
                }
            }