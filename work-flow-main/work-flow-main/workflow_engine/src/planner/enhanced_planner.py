"""
增强版 LLM 规划器
支持舆论分析工作流自动生成和智能体协作编排
"""
from typing import Optional, Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..core.schema import WorkflowDefinition, NodeDefinition, EdgeDefinition, NodeConfig
from ..config import get_llm_settings
from .llm_planner import parse_workflow_json_output, WorkflowJSONProcessingError


class EnhancedLLMPlanner:
    """
    增强版 LLM 规划器
    负责将用户的自然语言意图转换为智能体协作工作流
    """
    
    def __init__(self, model_name: str = None):
        # 使用统一配置管理
        llm_settings = get_llm_settings(model_name=model_name)
        self.llm = ChatOpenAI(**llm_settings.to_langchain_kwargs())
    
    def plan_public_opinion_workflow(self, topic: str, requirements: Optional[str] = None) -> WorkflowDefinition:
        """
        生成舆论分析工作流
        
        Args:
            topic: 分析主题（如"DeepSeek用户反馈"、"某产品舆情"等）
            requirements: 额外需求描述
            
        Returns:
            工作流定义
        """
        user_intent = f"创建一个关于'{topic}'的舆论分析工作流"
        if requirements:
            user_intent += f"，需求：{requirements}"
        
        return self.plan(user_intent, workflow_type="public_opinion_analysis")
    
    def plan(self, user_intent: str, workflow_type: Optional[str] = None) -> WorkflowDefinition:
        """
        根据用户意图生成工作流定义
        
        Args:
            user_intent: 用户意图描述
            workflow_type: 工作流类型（可选，如 'public_opinion_analysis'）
            
        Returns:
            工作流定义
        """
        # 根据工作流类型选择不同的提示词
        if workflow_type == "public_opinion_analysis":
            system_prompt = self._get_public_opinion_prompt()
        else:
            system_prompt = self._get_general_prompt()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{intent}")
        ])
        
        # 链式调用
        chain = prompt | self.llm
        
        print(f"规划工作流: '{user_intent}'...")
        try:
            response = chain.invoke({"intent": user_intent})
            content = response.content if hasattr(response, "content") else str(response)
            result = parse_workflow_json_output(content)
            # 转换为 Pydantic 对象以验证 Schema
            return self._convert_to_workflow(result)
        except WorkflowJSONProcessingError as e:
            print(f"规划失败（{e.stage}）: {e}")
            raise
        except Exception as e:
            print(f"规划失败: {e}")
            raise
    
    def _get_public_opinion_prompt(self) -> str:
        """获取舆论分析工作流的提示词"""
        return """
You are an expert Workflow Architect specializing in public opinion analysis workflows. Your goal is to design a workflow that collects, analyzes, and reports on public opinion data.

Output MUST be a valid JSON object that strictly follows this schema:

{{
  "name": "Public Opinion Analysis Workflow",
  "description": "Short description",
  "nodes": [
    {{
      "id": "unique_id",
      "type": "Start | End | DataCollectionAgent | SentimentAgent | ReportAgent | FilterAgent | LLM | Code | Condition | Loop",
      "config": {{
        "title": "Display Title",
        "description": "Node description",
        "agent_role": "Role Name (for agent nodes)",
        "agent_goal": "Goal description",
        "agent_backstory": "Backstory description",
        "params": {{
          // Node-specific parameters
        }}
      }}
    }}
  ],
  "edges": [
    {{ "source": "node_id_1", "target": "node_id_2" }}
  ],
  "variables": {{ "global_var": "default_value" }}
}}

**CRITICAL REQUIREMENTS:**

1. **YOU MUST USE AGENT NODES FOR PUBLIC OPINION ANALYSIS WORKFLOWS - NOT Code or LLM nodes!**
   - Use `DataCollectionAgent` for data collection (NOT Code nodes)
   - Use `FilterAgent` for data filtering (NOT Code nodes)
   - Use `SentimentAgent` for sentiment analysis (NOT Code nodes)
   - Use `ReportAgent` for report generation (NOT LLM nodes)

AVAILABLE AGENT NODES (YOU MUST USE THESE):

1. **DataCollectionAgent** - Collects data from multiple sources
   - params: {{
        "topic": "search topic",
        "sources": ["internet"],
        "max_results": 10,
        "time_range": "day | week | month"
      }}
   - Output: List of collected data items

2. **SentimentAgent** - Analyzes sentiment of text data
   - params: {{
        "data": "$upstream_node_id",
        "use_memory": true,
        "analysis_type": "sentiment | emotion | tone",
        "language": "zh | en"
      }}
   - Output: Sentiment analysis results

3. **FilterAgent** - Filters data based on criteria
   - params: {{
        "data": "$upstream_node_id",
        "filters": {{
          "keywords": ["keyword1", "keyword2"],
          "min_confidence": 0.7,
          "exclude_duplicates": true
        }},
        "sort_by": "relevance",
        "limit": 100
      }}
   - Output: Filtered data list

4. **ReportAgent** - Generates comprehensive reports
   - params: {{
        "report_type": "sentiment_analysis | data_collection | comprehensive",
        "template": "default | detailed | summary",
        "data_sources": ["$node_id_1", "$node_id_2"],
        "format": "markdown | html | json"
      }}
   - Output: Formatted report string

WORKFLOW DESIGN RULES:

1. **Always start with a "Start" node and end with an "End" node**

2. **REQUIRED Public Opinion Analysis Flow (USE THIS EXACT STRUCTURE):**
   Start → DataCollectionAgent → FilterAgent → SentimentAgent → ReportAgent → End

3. **Data Flow:**
   - Use "$node_id" (NOT "$node_id.output") to reference upstream node outputs
   - Each agent node MUST have agent_role, agent_goal, and agent_backstory

4. **Agent Configuration (REQUIRED FOR ALL AGENT NODES):**
   - DataCollectionAgent:
     * agent_role: "Data Collection Specialist"
     * agent_goal: "Collect relevant public opinion data from multiple sources"
     * agent_backstory: "Expert in data gathering and web scraping"
   
   - SentimentAgent:
     * agent_role: "Sentiment Analysis Expert"
     * agent_goal: "Analyze sentiment and emotional tone of collected data"
     * agent_backstory: "Specialist in NLP and sentiment analysis with domain knowledge"
   
   - FilterAgent:
     * agent_role: "Data Quality Analyst"
     * agent_goal: "Filter and clean data to ensure quality"
     * agent_backstory: "Expert in data validation and quality assurance"
   
   - ReportAgent:
     * agent_role: "Report Generation Specialist"
     * agent_goal: "Generate comprehensive and insightful reports"
     * agent_backstory: "Professional in data visualization and report writing"

5. **Node Parameters:**
   - Ensure each agent has appropriate params based on its type
   - Data references use "$node_id" format (e.g., "$data_collector" references the data_collector node)
   - Set realistic default values

6. **Graph Structure:**
   - Ensure the graph is a connected DAG (Directed Acyclic Graph)
   - No circular dependencies
   - Clear linear or branching flow

**EXAMPLE OUTPUT (Follow this pattern):**

{{
  "name": "Public Opinion Analysis Workflow",
  "description": "Complete public opinion analysis pipeline",
  "nodes": [
    {{ "id": "start", "type": "Start", "config": {{ "title": "开始", "params": {{}} }} }},
    {{ "id": "data_collector", "type": "DataCollectionAgent", "config": {{
      "title": "Data Collection",
      "agent_role": "Data Collection Specialist",
      "agent_goal": "Collect relevant data",
      "agent_backstory": "Expert in data gathering",
      "params": {{ "topic": "search topic", "sources": ["internet"], "max_results": 10, "time_range": "week" }}
    }} }},
    {{ "id": "data_filter", "type": "FilterAgent", "config": {{
      "title": "Data Filtering",
      "agent_role": "Data Quality Analyst",
      "agent_goal": "Filter and clean data",
      "agent_backstory": "Expert in data validation",
      "params": {{ "data": "$data_collector", "filters": {{ "exclude_duplicates": true }} }}
    }} }},
    {{ "id": "sentiment_analyzer", "type": "SentimentAgent", "config": {{
      "title": "Sentiment Analysis",
      "agent_role": "Sentiment Analysis Expert",
      "agent_goal": "Analyze sentiment",
      "agent_backstory": "NLP specialist",
      "params": {{ "data": "$data_filter", "analysis_type": "sentiment", "language": "zh" }}
    }} }},
    {{ "id": "report_generator", "type": "ReportAgent", "config": {{
      "title": "Report Generation",
      "agent_role": "Report Specialist",
      "agent_goal": "Generate analysis report",
      "agent_backstory": "Professional report writer",
      "params": {{ "report_type": "sentiment_analysis", "data_sources": ["$data_collector", "$sentiment_analyzer"] }}
    }} }},
    {{ "id": "end", "type": "End", "config": {{ "title": "结束", "params": {{}} }} }}
  ],
  "edges": [
    {{ "source": "start", "target": "data_collector" }},
    {{ "source": "data_collector", "target": "data_filter" }},
    {{ "source": "data_filter", "target": "sentiment_analyzer" }},
    {{ "source": "sentiment_analyzer", "target": "report_generator" }},
    {{ "source": "report_generator", "target": "end" }}
  ]
}}

User Intent: {intent}

Generate a complete workflow JSON that fulfills the user's requirements for public opinion analysis.
REMEMBER: You MUST use DataCollectionAgent, FilterAgent, SentimentAgent, and ReportAgent - NOT Code or LLM nodes!
"""
    
    def _get_general_prompt(self) -> str:
        """获取通用工作流的提示词"""
        return """
You are an expert Workflow Architect. Your goal is to design a workflow based on the user's intent.

Output MUST be a valid JSON object that strictly follows this schema:

{
  "name": "Workflow Name",
  "description": "Short description",
  "nodes": [
    {
      "id": "unique_id",
      "type": "Start | End | LLM | Code | Condition | Loop | DataCollectionAgent | SentimentAgent | ReportAgent | FilterAgent",
      "config": {
        "title": "Display Title",
        "agent_role": "Role Name (for agent nodes)",
        "agent_goal": "Goal description",
        "agent_backstory": "Backstory description",
        "params": {
          // Node-specific parameters
        }
      }
    }
  ],
  "edges": [
    { "source": "node_id_1", "target": "node_id_2" }
  ],
  "variables": { "global_var": "default_value" }
}

AVAILABLE NODE TYPES:

1. **Basic Nodes:**
   - Start: Entry point
   - End: Exit point
   - LLM: Large language model node
   - Code: Python code execution
   - Condition: Conditional branching
   - Loop: Iterative execution

2. **Agent Nodes:**
   - DataCollectionAgent: Collects data from sources
   - SentimentAgent: Analyzes sentiment
   - ReportAgent: Generates reports
   - FilterAgent: Filters data

RULES:
1. Always start with "Start" node and end with "End" node
2. Use "$node_id.output" to reference upstream outputs
3. Each agent node needs agent_role, agent_goal, and agent_backstory
4. Ensure the graph is connected (DAG)
5. Provide realistic default parameters

User Intent: {intent}
"""
    
    def _convert_to_workflow(self, result: Dict[str, Any]) -> WorkflowDefinition:
        """
        将JSON结果转换为WorkflowDefinition对象
        
        Args:
            result: JSON格式的字典
            
        Returns:
            WorkflowDefinition对象
        """
        # 转换节点
        nodes = []
        for node_dict in result.get("nodes", []):
            config = NodeConfig(
                title=node_dict.get("config", {}).get("title", "Unnamed Node"),
                description=node_dict.get("config", {}).get("description"),
                agent_role=node_dict.get("config", {}).get("agent_role"),
                agent_goal=node_dict.get("config", {}).get("agent_goal"),
                agent_backstory=node_dict.get("config", {}).get("agent_backstory"),
                params=node_dict.get("config", {}).get("params", {})
            )
            
            node = NodeDefinition(
                id=node_dict["id"],
                type=node_dict["type"],
                config=config
            )
            nodes.append(node)
        
        # 转换边
        edges = []
        for edge_dict in result.get("edges", []):
            edge = EdgeDefinition(
                source=edge_dict["source"],
                target=edge_dict["target"],
                condition=edge_dict.get("condition")
            )
            edges.append(edge)
        
        # 创建工作流定义
        workflow = WorkflowDefinition(
            name=result.get("name", "Unnamed Workflow"),
            description=result.get("description"),
            nodes=nodes,
            edges=edges,
            variables=result.get("variables", {})
        )
        
        return workflow
    
    def get_agent_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        获取预设智能体模板
        
        Returns:
            智能体模板字典
        """
        return {
            "DataCollectionAgent": {
                "title": "数据收集智能体",
                "description": "从多个数据源收集信息",
                "agent_role": "数据收集专家",
                "agent_goal": "从多个数据源收集相关信息",
                "agent_backstory": "精通数据采集和网络爬虫技术",
                "params": {
                    "topic": "",
                    "sources": ["twitter", "news", "social_media"],
                    "max_results": 10,
                    "time_range": "week"
                }
            },
            "SentimentAgent": {
                "title": "情感分析智能体",
                "description": "分析文本情感倾向",
                "agent_role": "情感分析专家",
                "agent_goal": "分析文本的情感倾向和情绪",
                "agent_backstory": "专注于NLP和情感分析领域，具备丰富的领域知识",
                "params": {
                    "data": "",
                    "use_memory": True,
                    "analysis_type": "sentiment",
                    "language": "zh"
                }
            },
            "FilterAgent": {
                "title": "信息过滤智能体",
                "description": "根据条件过滤数据",
                "agent_role": "数据质量分析师",
                "agent_goal": "过滤和清洗数据，确保数据质量",
                "agent_backstory": "专家级数据验证和质量保证专家",
                "params": {
                    "data": "",
                    "filters": {
                        "keywords": [],
                        "min_confidence": 0.7,
                        "exclude_duplicates": True
                    }
                }
            },
            "ReportAgent": {
                "title": "报告生成智能体",
                "description": "生成专业分析报告",
                "agent_role": "报告生成专家",
                "agent_goal": "生成全面且有洞察力的分析报告",
                "agent_backstory": "专业的数据可视化和报告撰写专家",
                "params": {
                    "report_type": "sentiment_analysis",
                    "template": "default",
                    "data_sources": [],
                    "format": "markdown"
                }
            }
        }