"""
工作流编排服务
根据任务规划自动生成和编排工作流
"""
import json
from typing import Dict, List, Any, Optional
from ..agents.planning_agent import PlanningAgent, TaskPlan
from ..core.schema import WorkflowDefinition, NodeDefinition, EdgeDefinition, NodeConfig
from ..utils.logger import get_logger

logger = get_logger("workflow_orchestrator")


class WorkflowOrchestrator:
    """
    工作流编排器
    根据规划智能体的输出自动生成完整的工作流定义
    """
    
    def __init__(self, model_name: str = "deepseek-chat"):
        """初始化工作流编排器"""
        self.planning_agent = PlanningAgent(model_name=model_name)
    
    def create_workflow_from_user_input(
        self,
        user_input: str,
        workflow_name: Optional[str] = None,
        workflow_description: Optional[str] = None
    ) -> WorkflowDefinition:
        """
        从用户输入创建工作流
        
        Args:
            user_input: 用户输入的自然语言
            workflow_name: 工作流名称（可选）
            workflow_description: 工作流描述（可选）
            
        Returns:
            WorkflowDefinition: 工作流定义
        """
        logger.info("从用户输入创建工作流", user_input=user_input[:100])
        
        # 1. 分析用户意图，生成任务规划
        task_plan = self.planning_agent.analyze_intent(user_input)
        
        # 2. 优化任务规划
        optimized_plan = self.planning_agent.optimize_plan(task_plan)
        
        # 3. 根据任务规划生成工作流
        workflow = self.generate_workflow_from_plan(
            task_plan=optimized_plan,
            workflow_name=workflow_name,
            workflow_description=workflow_description
        )
        
        logger.info(
            "工作流创建完成",
            workflow_name=workflow.name,
            nodes_count=len(workflow.nodes),
            edges_count=len(workflow.edges)
        )
        
        return workflow
    
    def generate_workflow_from_plan(
        self,
        task_plan: TaskPlan,
        workflow_name: Optional[str] = None,
        workflow_description: Optional[str] = None
    ) -> WorkflowDefinition:
        """
        根据任务规划生成工作流定义
        
        Args:
            task_plan: 任务规划
            workflow_name: 工作流名称
            workflow_description: 工作流描述
            
        Returns:
            WorkflowDefinition: 工作流定义
        """
        # 创建节点列表
        nodes = []
        edges = []
        
        # 1. 添加Start节点
        start_node = NodeDefinition(
            id="start",
            type="Start",
            config=NodeConfig(
                title="开始",
                description="工作流开始",
                params={}
            )
        )
        nodes.append(start_node)
        
        # 2. 根据子任务创建智能体节点
        task_id_to_node_id = {}
        for i, subtask in enumerate(task_plan.subtasks):
            node_id = subtask["task_id"]
            task_id_to_node_id[subtask["task_id"]] = node_id
            
            # 创建智能体节点
            agent_node = self._create_agent_node(
                node_id=node_id,
                agent_type=subtask["agent_type"],
                description=subtask["description"],
                parameters=subtask.get("parameters", {})
            )
            nodes.append(agent_node)
        
        # 3. 创建边连接
        # Start节点连接到第一个任务
        if task_plan.subtasks:
            first_task_id = task_plan.subtasks[0]["task_id"]
            edges.append(EdgeDefinition(
                source="start",
                target=first_task_id
            ))
        
        # 根据依赖关系创建边
        for subtask in task_plan.subtasks:
            task_id = subtask["task_id"]
            dependencies = subtask.get("dependencies", [])
            
            if dependencies:
                # 如果有依赖项，连接到所有依赖项
                for dep_id in dependencies:
                    edges.append(EdgeDefinition(
                        source=dep_id,
                        target=task_id
                    ))
            else:
                # 如果没有依赖项且不是第一个任务，连接到前一个任务
                task_index = next(
                    (i for i, t in enumerate(task_plan.subtasks) if t["task_id"] == task_id),
                    -1
                )
                if task_index > 0:
                    prev_task_id = task_plan.subtasks[task_index - 1]["task_id"]
                    edges.append(EdgeDefinition(
                        source=prev_task_id,
                        target=task_id
                    ))
        
        # 4. 添加End节点
        end_node = NodeDefinition(
            id="end",
            type="End",
            config=NodeConfig(
                title="结束",
                description="工作流结束",
                params={}
            )
        )
        nodes.append(end_node)
        
        # 最后一个任务连接到End节点
        if task_plan.subtasks:
            last_task_id = task_plan.subtasks[-1]["task_id"]
            edges.append(EdgeDefinition(
                source=last_task_id,
                target="end"
            ))
        else:
            # 如果没有任务，Start直接连接到End
            edges.append(EdgeDefinition(
                source="start",
                target="end"
            ))
        
        # 5. 创建工作流定义
        workflow = WorkflowDefinition(
            name=workflow_name or f"{task_plan.main_task[:30]} - 工作流",
            description=workflow_description or f"自动生成的工作流：{task_plan.main_task}",
            nodes=nodes,
            edges=edges,
            variables={}
        )
        
        return workflow
    
    def _create_agent_node(
        self,
        node_id: str,
        agent_type: str,
        description: str,
        parameters: Dict[str, Any]
    ) -> NodeDefinition:
        """
        创建智能体节点
        
        Args:
            node_id: 节点ID
            agent_type: 智能体类型
            description: 描述
            parameters: 参数
            
        Returns:
            NodeDefinition: 节点定义
        """
        # 智能体配置模板
        agent_configs = {
            "DataCollectionAgent": {
                "title": "数据收集智能体",
                "agent_role": "数据收集专家",
                "agent_goal": "从多个数据源收集相关信息",
                "agent_backstory": "你是一个专业的数据收集专家，擅长从互联网、知识库等数据源获取信息。"
            },
            "FilterAgent": {
                "title": "信息过滤智能体",
                "agent_role": "数据质量分析师",
                "agent_goal": "过滤和清洗数据，确保数据质量",
                "agent_backstory": "你是一个专业的数据质量分析师，擅长识别和过滤低质量数据。"
            },
            "SentimentAgent": {
                "title": "情感分析智能体",
                "agent_role": "情感分析专家",
                "agent_goal": "分析文本的情感倾向",
                "agent_backstory": "你是一个专业的情感分析专家，擅长识别文本的情感、情绪和态度。"
            },
            "ReportAgent": {
                "title": "报告生成智能体",
                "agent_role": "报告撰写专家",
                "agent_goal": "生成结构化的分析报告",
                "agent_backstory": "你是一个专业的报告撰写专家，擅长将分析结果整理成清晰的报告。"
            }
        }
        
        # 获取智能体配置
        agent_config = agent_configs.get(agent_type, {
            "title": f"{agent_type}节点",
            "agent_role": "智能体",
            "agent_goal": "执行任务",
            "agent_backstory": "你是一个智能助手。"
        })
        
        # 处理参数引用
        processed_params = self._process_parameters(parameters)
        
        # 创建节点
        return NodeDefinition(
            id=node_id,
            type=agent_type,
            config=NodeConfig(
                title=agent_config["title"],
                description=description,
                agent_role=agent_config["agent_role"],
                agent_goal=agent_config["agent_goal"],
                agent_backstory=agent_config["agent_backstory"],
                params=processed_params
            )
        )
    
    def _process_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理参数，转换引用格式
        
        Args:
            parameters: 原始参数
            
        Returns:
            Dict[str, Any]: 处理后的参数
        """
        processed = {}
        
        for key, value in parameters.items():
            # 如果是数据引用，转换格式
            if key == "data_reference" and isinstance(value, str) and value.startswith("$"):
                processed["data"] = value
            # 如果是过滤器参数
            elif key == "filters" and isinstance(value, dict):
                processed["filters"] = value
            else:
                processed[key] = value
        
        return processed
    
    def get_planning_explanation(self, user_input: str) -> str:
        """
        获取任务规划的解释说明
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: 解释说明文本
        """
        task_plan = self.planning_agent.analyze_intent(user_input)
        return self.planning_agent.explain_plan(task_plan)
    
    def suggest_workflow_improvements(self, workflow: WorkflowDefinition) -> List[str]:
        """
        建议工作流改进方案
        
        Args:
            workflow: 工作流定义
            
        Returns:
            List[str]: 改进建议列表
        """
        suggestions = []
        
        # 检查是否有Start和End节点
        has_start = any(node.type == "Start" for node in workflow.nodes)
        has_end = any(node.type == "End" for node in workflow.nodes)
        
        if not has_start:
            suggestions.append("建议添加Start节点作为工作流的入口")
        if not has_end:
            suggestions.append("建议添加End节点作为工作流的出口")
        
        # 检查智能体节点的顺序
        agent_types = [node.type for node in workflow.nodes if node.type.endswith("Agent")]
        
        # 检查数据收集后是否有过滤
        if "DataCollectionAgent" in agent_types:
            data_collection_index = agent_types.index("DataCollectionAgent")
            after_collection = agent_types[data_collection_index + 1:] if data_collection_index < len(agent_types) - 1 else []
            if "FilterAgent" not in after_collection:
                suggestions.append("建议在数据收集后添加过滤步骤，提高数据质量")
        
        # 检查是否有报告生成
        if "ReportAgent" not in agent_types and len(agent_types) > 1:
            suggestions.append("建议添加报告生成步骤，便于结果展示")
        
        return suggestions
    
    def modify_workflow(
        self,
        workflow: WorkflowDefinition,
        modification_request: str
    ) -> WorkflowDefinition:
        """
        根据修改请求修改工作流
        
        Args:
            workflow: 原始工作流
            modification_request: 修改请求
            
        Returns:
            WorkflowDefinition: 修改后的工作流
        """
        logger.info("修改工作流", request=modification_request[:50])
        
        # 简单的修改逻辑（可以根据需要扩展）
        modification_lower = modification_request.lower()
        
        # 添加节点的请求
        if "添加" in modification_lower or "增加" in modification_lower:
            if "过滤" in modification_lower and "FilterAgent" not in [n.type for n in workflow.nodes]:
                # 添加过滤节点
                filter_node = NodeDefinition(
                    id="filter_added",
                    type="FilterAgent",
                    config=NodeConfig(
                        title="信息过滤智能体",
                        description="过滤数据",
                        agent_role="数据质量分析师",
                        agent_goal="过滤和清洗数据",
                        params={
                            "data": "$data_collector",
                            "filters": {
                                "min_confidence": 0.6,
                                "exclude_duplicates": True
                            }
                        }
                    )
                )
                workflow.nodes.append(filter_node)
        
        # 删除节点的请求
        elif "删除" in modification_lower or "移除" in modification_lower:
            # 简单示例：如果请求中包含节点类型
            for agent_type in ["FilterAgent", "DataCollectionAgent"]:
                if agent_type.lower() in modification_lower:
                    workflow.nodes = [n for n in workflow.nodes if n.type != agent_type]
                    break
        
        return workflow