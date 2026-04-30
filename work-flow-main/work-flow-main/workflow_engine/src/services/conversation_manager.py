"""
对话管理服务
管理多轮对话，支持上下文记忆和智能对话
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from ..agents.planning_agent import PlanningAgent, TaskPlan
from ..services.workflow_orchestrator import WorkflowOrchestrator
from ..core.schema import WorkflowDefinition
from ..database.repositories import ConversationRepository, WorkflowRepository
from ..database.connection import get_session
from ..utils.logger import get_logger

logger = get_logger("conversation_manager")


class ConversationContext:
    """对话上下文"""
    
    def __init__(
        self,
        conversation_id: str,
        workflow_id: Optional[str] = None,
        current_workflow: Optional[WorkflowDefinition] = None,
        user_intent: Optional[str] = None,
        task_plan: Optional[TaskPlan] = None
    ):
        self.conversation_id = conversation_id
        self.workflow_id = workflow_id
        self.current_workflow = current_workflow
        self.user_intent = user_intent
        self.task_plan = task_plan
        self.messages: List[Dict[str, Any]] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """添加消息到对话历史"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "conversation_id": self.conversation_id,
            "workflow_id": self.workflow_id,
            "user_intent": self.user_intent,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ConversationManager:
    """
    对话管理器
    管理多轮对话，支持上下文记忆和智能对话
    """
    
    def __init__(self, model_name: str = None):
        """初始化对话管理器"""
        from ..config import get_settings, get_llm_settings
        
        settings = get_settings()
        model = model_name or settings.llm_model
        
        # 使用统一配置管理初始化LLM
        llm_settings = get_llm_settings(model_name=model, temperature=0.7)
        self.llm = ChatOpenAI(**llm_settings.to_langchain_kwargs())
        
        self.planning_agent = PlanningAgent(model_name=model_name)
        self.orchestrator = WorkflowOrchestrator(model_name=model_name)
        
        # 初始化数据库仓库
        session = get_session()
        self.conversation_repo = ConversationRepository(session)
        self.workflow_repo = WorkflowRepository(session)
        
        # 对话上下文缓存
        self.contexts: Dict[str, ConversationContext] = {}
        
        # 初始化对话链
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    
    def start_conversation(
        self,
        user_input: str,
        workflow_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        开始新对话
        
        Args:
            user_input: 用户输入
            workflow_name: 工作流名称（可选）
            
        Returns:
            Dict[str, Any]: 对话响应
        """
        logger.info("开始新对话", user_input=user_input[:100])
        
        # 生成对话ID
        conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建对话上下文
        context = ConversationContext(conversation_id=conversation_id)
        context.add_message("user", user_input)
        
        # 1. 分析用户意图
        task_plan = self.planning_agent.analyze_intent(user_input)
        context.task_plan = task_plan
        context.user_intent = task_plan.main_task
        
        # 2. 生成工作流
        workflow = self.orchestrator.generate_workflow_from_plan(
            task_plan=task_plan,
            workflow_name=workflow_name
        )
        context.current_workflow = workflow
        
        # 3. 保存工作流到数据库
        workflow_dict = workflow.model_dump()
        saved_workflow = self.workflow_repo.create(
            name=workflow.name,
            description=workflow.description,
            definition=workflow_dict
        )
        context.workflow_id = saved_workflow.id
        
        # 4. 保存对话记录
        self.conversation_repo.create_conversation(
            workflow_id=saved_workflow.id,
            user_message=user_input,
            assistant_response=json.dumps({
                "type": "workflow_created",
                "workflow": workflow_dict,
                "explanation": self.planning_agent.explain_plan(task_plan)
            }, ensure_ascii=False),
            context={
                "conversation_id": conversation_id,
                "task_plan": task_plan.to_dict()
            }
        )
        
        # 缓存上下文
        self.contexts[conversation_id] = context
        
        # 添加助手消息
        response_message = f"我已为您创建了工作流「{workflow.name}」。\n\n{self.planning_agent.explain_plan(task_plan)}"
        context.add_message("assistant", response_message)
        
        return {
            "conversation_id": conversation_id,
            "workflow_id": saved_workflow.id,
            "workflow": workflow,
            "task_plan": task_plan.to_dict(),
            "message": response_message,
            "suggestions": self.planning_agent.suggest_improvements(task_plan)
        }
    
    def continue_conversation(
        self,
        conversation_id: str,
        user_input: str
    ) -> Dict[str, Any]:
        """
        继续对话
        
        Args:
            conversation_id: 对话ID
            user_input: 用户输入
            
        Returns:
            Dict[str, Any]: 对话响应
        """
        logger.info("继续对话", conversation_id=conversation_id, user_input=user_input[:50])
        
        # 获取对话上下文
        context = self.contexts.get(conversation_id)
        if not context:
            # 尝试从数据库恢复
            context = self._load_context_from_db(conversation_id)
            if not context:
                raise ValueError(f"对话不存在: {conversation_id}")
        
        # 添加用户消息
        context.add_message("user", user_input)
        
        # 分析用户意图类型
        intent_type = self._classify_intent(user_input)
        
        # 根据意图类型处理
        requires_workflow_intent = intent_type in {
            "modify_workflow", "ask_question", "add_step", "remove_step"
        }
        if requires_workflow_intent and not context.current_workflow:
            logger.warning(
                "恢复上下文缺少工作流，降级为一般对话处理",
                conversation_id=conversation_id,
                intent_type=intent_type
            )
            response = self._handle_general(context, user_input)
            response["type"] = "general_fallback"
            response["message"] = (
                "已恢复到基础会话上下文，但缺少可用工作流信息，先按一般对话处理。\n\n"
                f"{response.get('message', '')}"
            )
        elif intent_type == "modify_workflow":
            response = self._handle_modification(context, user_input)
        elif intent_type == "ask_question":
            response = self._handle_question(context, user_input)
        elif intent_type == "add_step":
            response = self._handle_add_step(context, user_input)
        elif intent_type == "remove_step":
            response = self._handle_remove_step(context, user_input)
        else:
            response = self._handle_general(context, user_input)
        
        # 添加助手消息
        context.add_message("assistant", response["message"])
        
        # 更新对话记录（workflow_id 缺失时跳过持久化，避免异常中断）
        if context.workflow_id:
            self.conversation_repo.create_conversation(
                workflow_id=context.workflow_id,
                user_message=user_input,
                assistant_response=json.dumps(response, ensure_ascii=False),
                context={
                    "conversation_id": conversation_id,
                    "intent_type": intent_type
                }
            )
        else:
            logger.warning(
                "会话缺少workflow_id，跳过对话持久化",
                conversation_id=conversation_id
            )
        
        return response
    
    def _classify_intent(self, user_input: str) -> str:
        """
        分类用户意图
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: 意图类型
        """
        user_input_lower = user_input.lower()
        
        # 修改意图
        if any(keyword in user_input_lower for keyword in ["修改", "改", "调整", "更新", "改变"]):
            return "modify_workflow"
        
        # 询问意图
        if any(keyword in user_input_lower for keyword in ["是什么", "为什么", "怎么", "如何", "能否", "可以"]):
            return "ask_question"
        
        # 添加意图
        if any(keyword in user_input_lower for keyword in ["添加", "增加", "加入", "新增"]):
            return "add_step"
        
        # 删除意图
        if any(keyword in user_input_lower for keyword in ["删除", "移除", "去掉", "不要"]):
            return "remove_step"
        
        return "general"
    
    def _handle_modification(
        self,
        context: ConversationContext,
        user_input: str
    ) -> Dict[str, Any]:
        """处理修改工作流请求"""
        # 使用工作流编排器修改工作流
        modified_workflow = self.orchestrator.modify_workflow(
            workflow=context.current_workflow,
            modification_request=user_input
        )
        
        # 更新上下文
        context.current_workflow = modified_workflow
        
        # 更新数据库
        self.workflow_repo.update(
            workflow_id=context.workflow_id,
            definition=modified_workflow.model_dump()
        )
        
        return {
            "type": "workflow_modified",
            "workflow": modified_workflow,
            "message": f"我已根据您的要求修改了工作流。当前工作流包含 {len(modified_workflow.nodes)} 个节点。"
        }
    
    def _handle_question(
        self,
        context: ConversationContext,
        user_input: str
    ) -> Dict[str, Any]:
        """处理问题"""
        # 使用LLM回答问题
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个工作流专家助手，帮助用户理解工作流相关的问题。
            
当前工作流信息：
- 名称：{workflow_name}
- 描述：{workflow_description}
- 节点数：{nodes_count}
- 节点类型：{node_types}

请用简洁、专业的语言回答用户的问题。"""),
            ("user", "{question}")
        ])
        
        chain = prompt | self.llm
        
        workflow = context.current_workflow
        response = chain.invoke({
            "workflow_name": workflow.name,
            "workflow_description": workflow.description,
            "nodes_count": len(workflow.nodes),
            "node_types": ", ".join([n.type for n in workflow.nodes]),
            "question": user_input
        })
        
        return {
            "type": "answer",
            "message": response.content
        }
    
    def _handle_add_step(
        self,
        context: ConversationContext,
        user_input: str
    ) -> Dict[str, Any]:
        """处理添加步骤请求"""
        # 分析需要添加的步骤类型
        add_prompt = ChatPromptTemplate.from_messages([
            ("system", """分析用户请求，确定需要添加的智能体类型。

可用的智能体类型：
- DataCollectionAgent: 数据收集
- FilterAgent: 数据过滤
- SentimentAgent: 情感分析
- ReportAgent: 报告生成

输出JSON格式：
{
  "agent_type": "智能体类型",
  "description": "步骤描述",
  "parameters": {}
}"""),
            ("user", "{input}")
        ])
        
        chain = add_prompt | self.llm | JsonOutputParser()
        result = chain.invoke({"input": user_input})
        
        # 添加新节点到工作流
        new_node = self.orchestrator._create_agent_node(
            node_id=f"added_{result['agent_type'].lower()}_{datetime.now().strftime('%H%M%S')}",
            agent_type=result["agent_type"],
            description=result["description"],
            parameters=result.get("parameters", {})
        )
        
        workflow = context.current_workflow
        workflow.nodes.append(new_node)
        
        # 连接到前一个节点
        if len(workflow.nodes) > 2:  # 除了Start和End
            last_agent_node = None
            for node in reversed(workflow.nodes):
                if node.type != "End":
                    last_agent_node = node
                    break
            
            if last_agent_node and last_agent_node.id != new_node.id:
                from ..core.schema import EdgeDefinition
                workflow.edges.append(EdgeDefinition(
                    source=last_agent_node.id,
                    target=new_node.id
                ))
        
        # 更新数据库
        self.workflow_repo.update(
            workflow_id=context.workflow_id,
            definition=workflow.model_dump()
        )
        
        return {
            "type": "step_added",
            "workflow": workflow,
            "message": f"我已添加了新的「{new_node.config.title}」步骤到工作流中。"
        }
    
    def _handle_remove_step(
        self,
        context: ConversationContext,
        user_input: str
    ) -> Dict[str, Any]:
        """处理删除步骤请求"""
        workflow = context.current_workflow
        
        # 识别要删除的节点类型
        remove_type = None
        if "数据收集" in user_input or "收集" in user_input:
            remove_type = "DataCollectionAgent"
        elif "过滤" in user_input:
            remove_type = "FilterAgent"
        elif "情感分析" in user_input or "分析" in user_input:
            remove_type = "SentimentAgent"
        elif "报告" in user_input:
            remove_type = "ReportAgent"
        
        if remove_type:
            # 移除节点
            removed_nodes = [n for n in workflow.nodes if n.type == remove_type]
            workflow.nodes = [n for n in workflow.nodes if n.type != remove_type]
            
            # 移除相关的边
            removed_ids = [n.id for n in removed_nodes]
            workflow.edges = [
                e for e in workflow.edges 
                if e.source not in removed_ids and e.target not in removed_ids
            ]
            
            # 更新数据库
            self.workflow_repo.update(
                workflow_id=context.workflow_id,
                definition=workflow.model_dump()
            )
            
            return {
                "type": "step_removed",
                "workflow": workflow,
                "message": f"我已从工作流中移除了「{remove_type}」步骤。"
            }
        else:
            return {
                "type": "error",
                "message": "抱歉，我无法识别要删除的步骤类型。请明确指定要删除的步骤。"
            }
    
    def _handle_general(
        self,
        context: ConversationContext,
        user_input: str
    ) -> Dict[str, Any]:
        """处理一般对话"""
        # 使用对话链处理
        chain = ConversationChain(llm=self.llm, memory=self.memory)
        response = chain.predict(input=user_input)
        
        return {
            "type": "general",
            "message": response
        }
    
    def _load_context_from_db(self, conversation_id: str) -> Optional[ConversationContext]:
        """从数据库加载对话上下文并回填缓存"""
        logger.info("尝试从数据库恢复会话上下文", conversation_id=conversation_id)

        if not conversation_id:
            return None

        try:
            if hasattr(self.conversation_repo, "get_by_context_conversation_id"):
                records = self.conversation_repo.get_by_context_conversation_id(conversation_id)
            else:
                records = self._fallback_find_context_records(conversation_id)
        except Exception as e:
            logger.error("查询会话记录失败", conversation_id=conversation_id, error=str(e))
            return None

        if not records:
            logger.warning("数据库中未找到会话记录", conversation_id=conversation_id)
            return None

        first_record = records[0]
        latest_record = records[-1]
        latest_context = latest_record.context if isinstance(latest_record.context, dict) else {}
        workflow_id = latest_record.workflow_id or first_record.workflow_id

        task_plan = self._build_task_plan_from_context(latest_context)
        user_intent = (
            latest_context.get("user_intent")
            if isinstance(latest_context, dict) else None
        ) or (task_plan.main_task if task_plan else None) or first_record.user_message

        current_workflow = None
        if workflow_id:
            try:
                workflow = self.workflow_repo.get_by_id(workflow_id)
                if workflow and isinstance(workflow.definition, dict):
                    current_workflow = WorkflowDefinition.model_validate(workflow.definition)
                else:
                    logger.warning(
                        "会话关联工作流不存在或定义无效，进入降级模式",
                        conversation_id=conversation_id,
                        workflow_id=workflow_id
                    )
            except Exception as e:
                logger.warning(
                    "解析工作流定义失败，进入降级模式",
                    conversation_id=conversation_id,
                    workflow_id=workflow_id,
                    error=str(e)
                )

        context = ConversationContext(
            conversation_id=conversation_id,
            workflow_id=workflow_id,
            current_workflow=current_workflow,
            user_intent=user_intent,
            task_plan=task_plan
        )

        restored_messages: List[Dict[str, Any]] = []
        for record in records:
            message_timestamp = (
                record.timestamp.isoformat()
                if getattr(record, "timestamp", None) else datetime.now().isoformat()
            )

            if record.user_message:
                restored_messages.append({
                    "role": "user",
                    "content": record.user_message,
                    "timestamp": message_timestamp,
                    "metadata": {"source": "db", "record_id": getattr(record, "id", None)}
                })

            assistant_content = self._extract_assistant_message(record.assistant_response)
            if assistant_content:
                restored_messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                    "timestamp": message_timestamp,
                    "metadata": {"source": "db", "record_id": getattr(record, "id", None)}
                })

        context.messages = restored_messages
        context.created_at = getattr(first_record, "timestamp", None) or context.created_at
        context.updated_at = getattr(latest_record, "timestamp", None) or context.updated_at

        self.contexts[conversation_id] = context

        logger.info(
            "会话上下文恢复完成",
            conversation_id=conversation_id,
            workflow_id=workflow_id,
            messages_count=len(context.messages),
            has_workflow=bool(context.current_workflow)
        )

        return context

    def _build_task_plan_from_context(self, context_data: Dict[str, Any]) -> Optional[TaskPlan]:
        """从上下文字段恢复 TaskPlan（容错）"""
        if not isinstance(context_data, dict):
            return None

        task_plan_data = context_data.get("task_plan")
        if not isinstance(task_plan_data, dict):
            return None

        try:
            return TaskPlan(
                main_task=task_plan_data.get("main_task", ""),
                subtasks=task_plan_data.get("subtasks", []),
                workflow_type=task_plan_data.get("workflow_type", "custom"),
                required_agents=task_plan_data.get("required_agents", []),
                estimated_steps=task_plan_data.get("estimated_steps", 1),
                complexity=task_plan_data.get("complexity", "medium")
            )
        except Exception as e:
            logger.warning("恢复task_plan失败", error=str(e))
            return None

    def _extract_assistant_message(self, assistant_response: Optional[str]) -> str:
        """提取助手消息文本，兼容 JSON 字符串与纯文本"""
        if not assistant_response:
            return ""

        response_text = (
            assistant_response if isinstance(assistant_response, str)
            else str(assistant_response)
        ).strip()

        if not response_text:
            return ""

        if response_text.startswith("{") or response_text.startswith("["):
            try:
                parsed = json.loads(response_text)
                if isinstance(parsed, dict):
                    return (
                        parsed.get("message")
                        or parsed.get("explanation")
                        or response_text
                    )
                return response_text
            except Exception:
                return response_text

        return response_text

    def _fallback_find_context_records(self, conversation_id: str) -> List[Any]:
        """仓储无专用查询时的降级查找（全量过滤）"""
        conversations = self.conversation_repo.get_all(skip=0, limit=500)
        matched_records = []

        for record in conversations:
            record_context = record.context or {}
            if isinstance(record_context, dict) and record_context.get("conversation_id") == conversation_id:
                matched_records.append(record)

        matched_records.sort(
            key=lambda item: getattr(item, "timestamp", datetime.min) or datetime.min
        )
        return matched_records
    
    def get_conversation_history(
        self,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            List[Dict[str, Any]]: 对话历史
        """
        context = self.contexts.get(conversation_id)
        if context:
            return context.messages
        return []
    
    def get_workflow_from_conversation(
        self,
        conversation_id: str
    ) -> Optional[WorkflowDefinition]:
        """
        从对话中获取当前工作流
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Optional[WorkflowDefinition]: 工作流定义
        """
        context = self.contexts.get(conversation_id)
        if context:
            return context.current_workflow
        return None