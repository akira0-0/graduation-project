"""
LLM 规划器
负责将用户的自然语言意图转换为 Workflow DSL (JSON)
支持智能体节点编排，优先使用专门的智能体节点而非 Code 节点
"""
import json
import re
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..core.schema import WorkflowDefinition
from ..config import get_llm_settings


class WorkflowJSONProcessingError(Exception):
    """LLM 输出的工作流 JSON 处理异常"""

    def __init__(self, message: str, stage: str = "unknown"):
        super().__init__(message)
        self.stage = stage


def _normalize_json_quotes(raw_text: str) -> str:
    """规范化全角/智能引号为标准引号（保守处理）"""
    quote_map = str.maketrans({
        "“": "\"",
        "”": "\"",
        "„": "\"",
        "‟": "\"",
        "＂": "\"",
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
        "＇": "'",
    })
    return raw_text.translate(quote_map)


def _remove_trailing_commas(raw_text: str) -> str:
    """去除对象/数组结尾前的尾逗号"""
    previous = raw_text
    while True:
        current = re.sub(r",\s*([}\]])", r"\1", previous)
        if current == previous:
            return current
        previous = current


def _extract_json_body(raw_text: str) -> str:
    """从 markdown 代码块或文本中提取 JSON 主体"""
    text = raw_text.strip()
    if not text:
        raise WorkflowJSONProcessingError("LLM 返回为空", stage="extract_json")

    code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    for block in code_blocks:
        candidate = block.strip()
        if "{" in candidate and "}" in candidate:
            return candidate

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1].strip()

    raise WorkflowJSONProcessingError("未找到可提取的 JSON 主体", stage="extract_json")


def validate_workflow_structure(workflow_data: Dict[str, Any]) -> None:
    """校验工作流核心结构完整性与 Schema 有效性"""
    if not isinstance(workflow_data, dict):
        raise WorkflowJSONProcessingError("工作流 JSON 根节点必须是对象", stage="structure_validation")

    for field in ("nodes", "edges"):
        if field not in workflow_data:
            raise WorkflowJSONProcessingError(f"缺少核心字段: {field}", stage="structure_validation")

    nodes = workflow_data.get("nodes")
    edges = workflow_data.get("edges")

    if not isinstance(nodes, list) or len(nodes) == 0:
        raise WorkflowJSONProcessingError("字段 nodes 必须为非空数组", stage="structure_validation")
    if not isinstance(edges, list) or len(edges) == 0:
        raise WorkflowJSONProcessingError("字段 edges 必须为非空数组", stage="structure_validation")

    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise WorkflowJSONProcessingError(f"nodes[{idx}] 必须是对象", stage="structure_validation")
        for field in ("id", "type", "config"):
            if field not in node:
                raise WorkflowJSONProcessingError(
                    f"nodes[{idx}] 缺少字段: {field}",
                    stage="structure_validation"
                )

    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise WorkflowJSONProcessingError(f"edges[{idx}] 必须是对象", stage="structure_validation")
        for field in ("source", "target"):
            if field not in edge:
                raise WorkflowJSONProcessingError(
                    f"edges[{idx}] 缺少字段: {field}",
                    stage="structure_validation"
                )

    try:
        WorkflowDefinition(**workflow_data)
    except Exception as exc:
        raise WorkflowJSONProcessingError(
            f"工作流 Schema 校验失败: {exc}",
            stage="structure_validation"
        ) from exc


def parse_workflow_json_output(raw_content: Any) -> Dict[str, Any]:
    """LLM 工作流输出处理链路：提取 -> 修复 -> 解析 -> 结构校验"""
    if isinstance(raw_content, list):
        parts = []
        for item in raw_content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        raw_text = "".join(parts)
    else:
        raw_text = str(raw_content)

    json_candidate = _extract_json_body(raw_text)

    parsed = None
    parse_error = None

    parse_candidates = [
        json_candidate,
        _remove_trailing_commas(_normalize_json_quotes(json_candidate))
    ]

    for candidate in parse_candidates:
        try:
            parsed = json.loads(candidate)
            break
        except json.JSONDecodeError as exc:
            parse_error = exc

    if parsed is None:
        raise WorkflowJSONProcessingError(
            f"JSON 解析失败，已尝试有限自动修复: {parse_error}",
            stage="parse_json"
        ) from parse_error

    validate_workflow_structure(parsed)
    return parsed


class LLMPlanner:
    """
    LLM 规划器
    负责将用户的自然语言意图转换为 Workflow DSL (JSON)
    支持多种节点类型，包括专门的智能体节点
    """
    
    def __init__(self, model_name: str = None):
        # 使用统一配置管理
        llm_settings = get_llm_settings(model_name=model_name)
        self.llm = ChatOpenAI(**llm_settings.to_langchain_kwargs())
        
    def plan(self, user_intent: str) -> WorkflowDefinition:
        """
        根据用户意图生成工作流定义
        """
        # 定义 Prompt - 支持智能体节点
        system_prompt = """
        You are an expert Workflow Architect. Your goal is to design a workflow based on the user's intent.
        
        Output MUST be a valid JSON object that strictly follows this schema:
        
        {{
          "name": "Workflow Name",
          "description": "Short description",
          "nodes": [
             {{
               "id": "unique_id",
               "type": "Start | End | DataCollectionAgent | SentimentAgent | ReportAgent | FilterAgent | LLM | Code | Condition | Loop",
               "config": {{
                 "title": "Display Title",
                 "description": "Node description",
                 // Agent Configuration (REQUIRED for agent nodes, LLM and Code nodes):
                 "agent_role": "Role Name (e.g., 'Data Analyst')",
                 "agent_goal": "Goal description",
                 "agent_backstory": "Backstory description",
                 
                 "params": {{
                    // Node-specific parameters (see below for each node type)
                 }}
               }}
             }}
          ],
          "edges": [
             {{ "source": "node_id_1", "target": "node_id_2" }}
          ],
          "variables": {{ "global_var": "default_value" }}
        }}

        **CRITICAL: PREFER AGENT NODES OVER CODE NODES!**
        When designing workflows for data collection, analysis, or reporting tasks,
        YOU MUST use the specialized Agent Nodes instead of Code nodes.

        AVAILABLE NODE TYPES:

        1. **Basic Nodes:**
           - Start: Entry point, no params required
           - End: Exit point, no params required
           - Condition: Conditional branching
           - Loop: Iterative execution

        2. **Agent Nodes (PREFERRED for data tasks):**
           - DataCollectionAgent: Collects data from multiple sources
             * params: {{ "topic": "search topic", "sources": ["internet"], "max_results": 10, "time_range": "week" }}
             * Output: {{ "collected_data": [...], "total_count": N }}
           
           - FilterAgent: Filters data based on criteria
             * params: {{ "data": "$upstream_node_id", "filters": {{ "exclude_duplicates": true }}, "limit": 100 }}
             * Output: {{ "filtered_data": [...], "filtered_count": N }}
           
           - SentimentAgent: Analyzes sentiment of text data
             * params: {{ "data": "$upstream_node_id", "analysis_type": "sentiment", "language": "zh" }}
             * Output: {{ "analysis_result": {{...}} }}
           
           - ReportAgent: Generates comprehensive reports
             * params: {{ "report_type": "sentiment_analysis", "data_sources": ["$node_id_1", "$node_id_2"], "format": "markdown" }}
             * Output: {{ "report_content": "..." }}

        3. **Generic Nodes (use ONLY when Agent Nodes don't fit):**
           - LLM: Large language model for text generation
             * params: {{ "model": "deepseek-chat", "prompt": "template with {{{{variables}}}}", "inputs": {{ "var": "$node_id.content" }} }}
           
           - Code: Python code execution (LAST RESORT)
             * params: {{ "code": "def main():\\n    return result", "inputs": {{ "var": "$node_id.content" }} }}

        WORKFLOW DESIGN RULES:

        1. **Always start with a "Start" node and end with an "End" node**

        2. **Use Agent Nodes for their designated purposes:**
           - Data collection task → Use DataCollectionAgent
           - Data filtering task → Use FilterAgent
           - Sentiment analysis task → Use SentimentAgent
           - Report generation task → Use ReportAgent

        3. **Data Flow:**
           - Use "$node_id" to reference upstream node outputs (e.g., "$data_collector")
           - Each agent node MUST have agent_role, agent_goal, and agent_backstory

        4. **Agent Configuration (REQUIRED FOR ALL AGENT NODES):**
           - agent_role: The job title (e.g., "Data Collection Specialist")
           - agent_goal: What this agent aims to achieve
           - agent_backstory: A brief persona description

        5. **Graph Structure:**
           - Ensure the graph is a connected DAG (Directed Acyclic Graph)
           - No circular dependencies

        **EXAMPLE WORKFLOW FOR PUBLIC OPINION ANALYSIS:**

        {{
          "name": "Public Opinion Analysis Workflow",
          "description": "Complete public opinion analysis pipeline",
          "nodes": [
            {{ "id": "start", "type": "Start", "config": {{ "title": "开始", "params": {{}} }} }},
            {{ "id": "data_collector", "type": "DataCollectionAgent", "config": {{
              "title": "Data Collection",
              "agent_role": "Data Collection Specialist",
              "agent_goal": "Collect relevant public opinion data from multiple sources",
              "agent_backstory": "Expert in data gathering and web scraping",
              "params": {{ "topic": "search topic", "sources": ["internet"], "max_results": 10, "time_range": "week" }}
            }} }},
            {{ "id": "data_filter", "type": "FilterAgent", "config": {{
              "title": "Data Filtering",
              "agent_role": "Data Quality Analyst",
              "agent_goal": "Filter and clean data to ensure quality",
              "agent_backstory": "Expert in data validation and quality assurance",
              "params": {{ "data": "$data_collector", "filters": {{ "exclude_duplicates": true }} }}
            }} }},
            {{ "id": "sentiment_analyzer", "type": "SentimentAgent", "config": {{
              "title": "Sentiment Analysis",
              "agent_role": "Sentiment Analysis Expert",
              "agent_goal": "Analyze sentiment and emotional tone of collected data",
              "agent_backstory": "Specialist in NLP and sentiment analysis",
              "params": {{ "data": "$data_filter", "analysis_type": "sentiment", "language": "zh" }}
            }} }},
            {{ "id": "report_generator", "type": "ReportAgent", "config": {{
              "title": "Report Generation",
              "agent_role": "Report Generation Specialist",
              "agent_goal": "Generate comprehensive and insightful reports",
              "agent_backstory": "Professional in data visualization and report writing",
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

        Generate a complete workflow JSON that fulfills the user's requirements.
        REMEMBER: Use Agent Nodes (DataCollectionAgent, FilterAgent, SentimentAgent, ReportAgent) instead of Code nodes whenever possible!
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{intent}")
        ])
        
        # 链式调用
        chain = prompt | self.llm
        
        print(f"Planning workflow for: '{user_intent}'...")
        try:
            response = chain.invoke({"intent": user_intent})
            content = response.content if hasattr(response, "content") else str(response)
            result = parse_workflow_json_output(content)
            # 转换为 Pydantic 对象以验证 Schema
            return WorkflowDefinition(**result)
        except WorkflowJSONProcessingError as e:
            print(f"Planning failed at {e.stage}: {e}")
            raise
        except Exception as e:
            print(f"Planning failed: {e}")
            raise e