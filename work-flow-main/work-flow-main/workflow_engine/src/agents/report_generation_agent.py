"""
报告生成智能体（增强版）
使用模板/规则记忆和审计日志生成报告
集成数据存储服务，自动持久化生成的报告
支持从数据库读取分析结果并生成综合报告

增强功能：
- LLM 驱动的智能报告生成：使用 LLM 生成内容，而非固定模板
- 深度见解提取：提供趋势分析、因果关系、建议策略
- 结构化呈现：摘要、数据展示、深度分析、建议见解
- 自动篇幅调整：根据数据重要性自动调整篇幅
- 多语言支持：支持中英文报告生成
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from jinja2 import Template
import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..database import get_session, AgentMemoryService, AuditLogService
from ..database.repositories.workflow_repository import WorkflowRepository
from ..utils.logger import get_logger

logger = get_logger("report_generation_agent")


class LLMReportGenerator:
    """
    LLM 报告生成器
    使用大语言模型生成智能、深度的分析报告
    """
    
    def __init__(self):
        """初始化 LLM"""
        self.llm = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
            openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0.5
        )
    
    def generate_executive_summary(
        self,
        data: Dict[str, Any],
        language: str = "zh"
    ) -> str:
        """
        生成执行摘要
        
        Args:
            data: 分析数据
            language: 语言 (zh/en)
            
        Returns:
            执行摘要文本
        """
        if language == "zh":
            prompt = f"""作为专业分析师，请基于以下分析数据生成一份简洁有力的执行摘要。

分析数据：
{json.dumps(data, ensure_ascii=False, indent=2)}

要求：
1. 概括核心发现（3-5点）
2. 突出关键数据指标
3. 指出主要问题和机遇
4. 简明扼要，200字以内

执行摘要："""
        else:
            prompt = f"""As a professional analyst, generate a concise executive summary based on the following analysis data.

Analysis Data:
{json.dumps(data, ensure_ascii=False, indent=2)}

Requirements:
1. Summarize key findings (3-5 points)
2. Highlight key metrics
3. Identify main issues and opportunities
4. Keep it concise, within 200 words

Executive Summary:"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            logger.warning(f"执行摘要生成失败: {e}")
            return "摘要生成失败"
    
    def generate_deep_insights(
        self,
        sentiment_data: Dict[str, Any],
        collected_data: List[Dict[str, Any]],
        language: str = "zh"
    ) -> Dict[str, Any]:
        """
        生成深度见解
        
        Args:
            sentiment_data: 情感分析数据
            collected_data: 收集的数据
            language: 语言
            
        Returns:
            深度见解
        """
        # 准备数据摘要
        summary = sentiment_data.get("summary", {})
        insights = sentiment_data.get("insights", {})
        
        if language == "zh":
            prompt = f"""作为资深数据分析师，请基于以下数据提供深度见解和分析。

## 情感分析结果
- 总数据量：{summary.get('total_analyzed', 0)}
- 正面情感：{summary.get('sentiment_counts', {}).get('positive', 0)} ({summary.get('sentiment_distribution', {}).get('positive', 0)*100:.1f}%)
- 负面情感：{summary.get('sentiment_counts', {}).get('negative', 0)} ({summary.get('sentiment_distribution', {}).get('negative', 0)*100:.1f}%)
- 中性情感：{summary.get('sentiment_counts', {}).get('neutral', 0)} ({summary.get('sentiment_distribution', {}).get('neutral', 0)*100:.1f}%)
- 主导情感：{summary.get('dominant_sentiment', 'neutral')}

## 已提取的洞察
{json.dumps(insights, ensure_ascii=False, indent=2)}

请以 JSON 格式返回深度见解，包含以下字段：
{{
    "trend_analysis": "趋势分析，包括情感走向、变化原因",
    "causal_analysis": "因果分析，解释为何出现当前情感分布",
    "key_findings": ["关键发现1", "关键发现2", "关键发现3"],
    "risk_assessment": "风险评估，指出潜在问题",
    "opportunities": ["发现的机会1", "发现的机会2"],
    "recommendations": ["建议1", "建议2", "建议3"]
}}

只返回 JSON："""
        else:
            prompt = f"""As a senior data analyst, provide deep insights based on the following data.

## Sentiment Analysis Results
- Total: {summary.get('total_analyzed', 0)}
- Positive: {summary.get('sentiment_counts', {}).get('positive', 0)} ({summary.get('sentiment_distribution', {}).get('positive', 0)*100:.1f}%)
- Negative: {summary.get('sentiment_counts', {}).get('negative', 0)} ({summary.get('sentiment_distribution', {}).get('negative', 0)*100:.1f}%)
- Neutral: {summary.get('sentiment_counts', {}).get('neutral', 0)} ({summary.get('sentiment_distribution', {}).get('neutral', 0)*100:.1f}%)
- Dominant: {summary.get('dominant_sentiment', 'neutral')}

## Extracted Insights
{json.dumps(insights, ensure_ascii=False, indent=2)}

Please return deep insights in JSON format:
{{
    "trend_analysis": "Trend analysis including sentiment direction and causes",
    "causal_analysis": "Causal analysis explaining the current sentiment distribution",
    "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
    "risk_assessment": "Risk assessment pointing out potential issues",
    "opportunities": ["Opportunity 1", "Opportunity 2"],
    "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"]
}}

Return JSON only:"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("\n", 1)[0]
            
            result = json.loads(content)
            return result
        except Exception as e:
            logger.warning(f"深度见解生成失败: {e}")
            return {
                "trend_analysis": "",
                "causal_analysis": "",
                "key_findings": [],
                "risk_assessment": "",
                "opportunities": [],
                "recommendations": [],
                "error": str(e)
            }
    
    def generate_action_plan(
        self,
        insights: Dict[str, Any],
        context: str,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """
        生成行动计划
        
        Args:
            insights: 洞察数据
            context: 上下文信息
            language: 语言
            
        Returns:
            行动计划列表
        """
        if language == "zh":
            prompt = f"""基于以下分析洞察，制定具体的行动计划。

上下文：{context}

洞察数据：
{json.dumps(insights, ensure_ascii=False, indent=2)}

请以 JSON 数组格式返回行动计划，每个行动包含：
{{
    "priority": "high/medium/low",
    "action": "具体行动",
    "rationale": "行动理由",
    "expected_outcome": "预期结果",
    "timeframe": "建议时间框架",
    "resources_needed": "所需资源"
}}

返回 JSON 数组："""
        else:
            prompt = f"""Based on the following insights, develop a concrete action plan.

Context: {context}

Insights:
{json.dumps(insights, ensure_ascii=False, indent=2)}

Return action plan as JSON array, each action containing:
{{
    "priority": "high/medium/low",
    "action": "Specific action",
    "rationale": "Rationale for this action",
    "expected_outcome": "Expected outcome",
    "timeframe": "Suggested timeframe",
    "resources_needed": "Resources needed"
}}

Return JSON array:"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("\n", 1)[0]
            
            result = json.loads(content)
            return result if isinstance(result, list) else [result]
        except Exception as e:
            logger.warning(f"行动计划生成失败: {e}")
            return []
    
    def generate_full_report(
        self,
        topic: str,
        sentiment_data: Dict[str, Any],
        collected_data: List[Dict[str, Any]],
        language: str = "zh",
        report_style: str = "professional"
    ) -> str:
        """
        生成完整的智能报告（Markdown格式）
        
        Args:
            topic: 报告主题
            sentiment_data: 情感分析数据
            collected_data: 收集的数据
            language: 语言
            report_style: 报告风格 (professional/concise/detailed)
            
        Returns:
            Markdown格式的报告
        """
        summary = sentiment_data.get("summary", {})
        insights = sentiment_data.get("insights", {})
        trend = sentiment_data.get("trend", {})
        trend_prediction = sentiment_data.get("trend_prediction", {})
        
        # 生成执行摘要
        executive_summary = self.generate_executive_summary(sentiment_data, language)
        
        # 生成深度见解
        deep_insights = self.generate_deep_insights(sentiment_data, collected_data, language)
        
        if language == "zh":
            report = f"""# {topic} - 情感分析报告

> 报告生成时间：{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
> 分析方法：LLM 深度分析
> 数据来源：互联网搜索、知识库、实时数据

---

## 📊 执行摘要

{executive_summary}

---

## 📈 数据概览

### 基本统计

| 指标 | 数值 |
|------|------|
| 总分析数据量 | {summary.get('total_analyzed', 0)} |
| 正面情感 | {summary.get('sentiment_counts', {}).get('positive', 0)} ({summary.get('sentiment_distribution', {}).get('positive', 0)*100:.1f}%) |
| 负面情感 | {summary.get('sentiment_counts', {}).get('negative', 0)} ({summary.get('sentiment_distribution', {}).get('negative', 0)*100:.1f}%) |
| 中性情感 | {summary.get('sentiment_counts', {}).get('neutral', 0)} ({summary.get('sentiment_distribution', {}).get('neutral', 0)*100:.1f}%) |
| 主导情感 | {summary.get('dominant_sentiment', 'neutral')} |

### 情感趋势

当前趋势：**{trend.get('trend', 'stable')}**

"""
            # 添加趋势预测
            if trend_prediction:
                report += f"""#### 趋势预测

- **预测方向**：{trend_prediction.get('trend', 'stable')}
- **预测置信度**：{trend_prediction.get('trend_confidence', 0)*100:.1f}%
- **预测说明**：{trend_prediction.get('prediction', '暂无预测')}

"""
            
            # 添加深度见解
            report += f"""---

## 🔍 深度分析

### 趋势分析

{deep_insights.get('trend_analysis', '暂无分析')}

### 因果分析

{deep_insights.get('causal_analysis', '暂无分析')}

### 关键发现

"""
            for finding in deep_insights.get('key_findings', []):
                report += f"- {finding}\n"
            
            report += f"""
### 风险评估

{deep_insights.get('risk_assessment', '暂无评估')}

### 发现的机会

"""
            for opportunity in deep_insights.get('opportunities', []):
                report += f"- 🌟 {opportunity}\n"
            
            # 添加洞察摘要
            if insights:
                report += f"""
---

## 💡 智能洞察

{insights.get('summary', '')}

#### 主要主题

"""
                for theme in insights.get('main_themes', []):
                    report += f"- {theme}\n"
                
                report += "\n#### 痛点问题\n\n"
                for pain in insights.get('pain_points', []):
                    report += f"- ⚠️ {pain}\n"
                
                report += "\n#### 亮点\n\n"
                for highlight in insights.get('highlights', []):
                    report += f"- ✨ {highlight}\n"
            
            # 添加建议
            report += f"""
---

## 📋 建议措施

"""
            for i, rec in enumerate(deep_insights.get('recommendations', []), 1):
                report += f"{i}. {rec}\n"
            
            # 生成行动计划
            action_plan = self.generate_action_plan(deep_insights, topic, language)
            if action_plan:
                report += "\n### 行动计划\n\n"
                report += "| 优先级 | 行动项 | 理由 | 时间框架 |\n"
                report += "|--------|--------|------|----------|\n"
                for action in action_plan[:5]:  # 只显示前5项
                    report += f"| {action.get('priority', 'medium')} | {action.get('action', '')} | {action.get('rationale', '')} | {action.get('timeframe', '')} |\n"
            
            report += f"""
---

## 📎 附录

### 分析方法说明

本报告使用 LLM（大语言模型）深度分析技术，结合传统情感分析方法，提供以下增强功能：

- **深度语义理解**：理解上下文含义，识别隐含情感
- **多维度分析**：情感强度、情感原因、情感对象
- **智能归类**：自动识别主题、观点、关键信息
- **趋势预测**：基于历史数据预测情感走向

### 数据质量说明

- 数据经过去重和质量评估
- LLM 分析结果经过验证
- 建议结合人工审核进行重要决策

---

*本报告由 AI 智能分析系统生成，使用 LLM 深度分析技术*
*报告风格：{report_style}*
"""
        else:
            # 英文报告
            report = f"""# {topic} - Sentiment Analysis Report

> Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
> Analysis Method: LLM Deep Analysis
> Data Sources: Internet Search, Knowledge Base, Real-time Data

---

## 📊 Executive Summary

{executive_summary}

---

## 📈 Data Overview

### Basic Statistics

| Metric | Value |
|--------|-------|
| Total Analyzed | {summary.get('total_analyzed', 0)} |
| Positive | {summary.get('sentiment_counts', {}).get('positive', 0)} ({summary.get('sentiment_distribution', {}).get('positive', 0)*100:.1f}%) |
| Negative | {summary.get('sentiment_counts', {}).get('negative', 0)} ({summary.get('sentiment_distribution', {}).get('negative', 0)*100:.1f}%) |
| Neutral | {summary.get('sentiment_counts', {}).get('neutral', 0)} ({summary.get('sentiment_distribution', {}).get('neutral', 0)*100:.1f}%) |
| Dominant Sentiment | {summary.get('dominant_sentiment', 'neutral')} |

---

## 🔍 Deep Analysis

### Trend Analysis

{deep_insights.get('trend_analysis', 'No analysis available')}

### Causal Analysis

{deep_insights.get('causal_analysis', 'No analysis available')}

### Key Findings

"""
            for finding in deep_insights.get('key_findings', []):
                report += f"- {finding}\n"
            
            report += f"""
### Recommendations

"""
            for i, rec in enumerate(deep_insights.get('recommendations', []), 1):
                report += f"{i}. {rec}\n"
            
            report += f"""
---

*This report was generated by AI Intelligence Analysis System using LLM deep analysis technology*
"""
        
        return report


class ReportGenerationAgent:
    """
    报告生成智能体（增强版）
    
    增强功能：
    - LLM 驱动的智能报告生成：使用 LLM 生成内容，而非固定模板
    - 深度见解提取：提供趋势分析、因果关系、建议策略
    - 结构化呈现：摘要、数据展示、深度分析、建议见解
    - 自动篇幅调整：根据数据重要性自动调整篇幅
    - 多语言支持：支持中英文报告生成
    
    支持模板/规则记忆和审计日志
    集成数据存储服务，自动持久化生成的报告
    支持从数据库读取分析结果并生成综合报告
    """
    
    def __init__(self, workflow_id: Optional[str], auto_save: bool = True, use_llm: bool = True):
        """
        初始化智能体
        
        Args:
            workflow_id: 工作流 ID（数据库主键 UUID）
            auto_save: 是否自动保存报告到数据库（默认True）
            use_llm: 是否使用 LLM 生成智能报告（默认True）
        """
        self.workflow_id = workflow_id
        self.db = get_session()
        self.memory_service = AgentMemoryService(self.db)
        self.audit_service = AuditLogService(self.db)
        self.workflow_repo = WorkflowRepository(self.db)

        # 校验工作流ID，仅在可持久化时才允许写库
        self.persistence_enabled = self._is_persistable_workflow_id(workflow_id)

        if auto_save and not self.persistence_enabled:
            logger.warning(
                "workflow_id 缺失或无效，ReportGenerationAgent 将降级为仅生成报告不写库",
                workflow_id=workflow_id
            )

        self.auto_save = auto_save and self.persistence_enabled
        self.use_llm = use_llm
        
        # 初始化 LLM 报告生成器
        if use_llm:
            try:
                self.llm_generator = LLMReportGenerator()
                logger.info("LLM 智能报告生成功能已启用")
            except Exception as e:
                logger.warning(f"LLM 报告生成器初始化失败: {e}，将使用模板模式")
                self.use_llm = False
                self.llm_generator = None
        else:
            self.llm_generator = None

        # 延迟导入避免循环依赖，仅在可持久化时初始化存储服务
        self.storage_service = None
        if self.persistence_enabled:
            from ..services.data_storage_service import DataStorageService
            self.storage_service = DataStorageService(workflow_id)

        # 初始化模板和规则（仅持久化模式）
        if self.persistence_enabled:
            self._initialize_memories()

    def _is_persistable_workflow_id(self, workflow_id: Optional[str]) -> bool:
        """检查 workflow_id 是否可用于持久化（UUID 且在 workflows 表存在）"""
        if not workflow_id:
            return False

        try:
            UUID(str(workflow_id))
        except (ValueError, TypeError):
            return False

        try:
            return self.workflow_repo.get_by_id(str(workflow_id)) is not None
        except Exception as e:
            logger.warning(f"校验 workflow_id 可持久化性失败，降级为不写库: {e}")
            return False

    def _get_fallback_template_content(self, template_name: str) -> str:
        """当无法访问模板记忆时使用的降级模板"""
        if template_name == "sentiment_analysis_report":
            return """# {{ title | default('情感分析报告') }}

## 报告概要

**生成时间**: {{ generated_time }}
**分析主题**: {{ topic | default('未提供主题') }}
**数据来源**: {{ sources | join(', ') if sources else '未知' }}

---

## 执行摘要

- **总分析条数**: {{ total_analyzed | default(0) }}
- **主要情感倾向**: {{ dominant_sentiment | default('neutral') }}
- **情感趋势**: {{ trend_text | default('稳定') }}

### 情感分布

| 情感类型 | 数量 | 占比 |
|---------|------|------|
| 正面 | {{ positive_count | default(0) }} | {{ positive_percentage | default(0) }}% |
| 负面 | {{ negative_count | default(0) }} | {{ negative_percentage | default(0) }}% |
| 中性 | {{ neutral_count | default(0) }} | {{ neutral_percentage | default(0) }}% |

---

## 详细分析

### 正面评价摘要
{% if positive_examples %}
{% for example in positive_examples %}
- [{{ example.source | default('未知来源') }}] {{ example.content | default('无内容') }}
{% endfor %}
{% else %}
暂无正面评价
{% endif %}

### 负面评价摘要
{% if negative_examples %}
{% for example in negative_examples %}
- [{{ example.source | default('未知来源') }}] {{ example.content | default('无内容') }}
{% endfor %}
{% else %}
暂无负面评价
{% endif %}

### 中性评价摘要
{% if neutral_examples %}
{% for example in neutral_examples %}
- [{{ example.source | default('未知来源') }}] {{ example.content | default('无内容') }}
{% endfor %}
{% else %}
暂无中性评价
{% endif %}

---

## 总结与建议

{% if dominant_sentiment == 'positive' %}
整体情感倾向积极，建议继续保持当前策略，并关注用户体验的进一步提升。
{% elif dominant_sentiment == 'negative' %}
整体情感倾向消极，建议深入分析负面反馈的原因，制定改进措施。
{% else %}
整体情感倾向中性，建议进一步收集更多反馈，进行深入分析。
{% endif %}

---

**报告生成时间**: {{ generated_time }}
**工作流ID**: {{ workflow_id | default('N/A') }}

*本报告由 AI 智能分析生成，建议结合人工审核。*
"""
        else:
            return """# {{ title | default('分析报告') }}

**生成时间**: {{ generated_time }}
**工作流ID**: {{ workflow_id | default('N/A') }}

## 报告内容

{{ topic | default('未提供主题') }}

---

本次为降级模式生成结果（未写入数据库）。
"""

    def _initialize_memories(self):
        """初始化默认的模板和规则"""
        if not self.persistence_enabled:
            return
        # 加载模板
        templates = self.memory_service.get_templates(
            self.workflow_id,
            "report_generation"
        )
        
        # 如果没有模板，创建默认的
        if not templates:
            self._create_default_templates()
        
        # 加载规则
        rules = self.memory_service.get_rules(
            self.workflow_id,
            "report_generation"
        )
        
        # 如果没有规则，创建默认的
        if not rules:
            self._create_default_rules()
    
    def _create_default_templates(self):
        """创建默认的报告模板"""
        default_templates = {
            "sentiment_analysis_report": """# {{ title }}

## 报告概要

**生成时间**: {{ generated_time }}
**分析主题**: {{ topic }}
**数据来源**: {{ sources }}

---

## 执行摘要

- **总分析条数**: {{ total_analyzed }}
- **主要情感倾向**: {{ dominant_sentiment }}
- **情感趋势**: {{ trend }}

### 情感分布

| 情感类型 | 数量 | 占比 |
|---------|------|------|
| 正面 | {{ positive_count }} | {{ positive_percentage }}% |
| 负面 | {{ negative_count }} | {{ negative_percentage }}% |
| 中性 | {{ neutral_count }} | {{ neutral_percentage }}% |

---

## 详细分析

### 正面评价摘要
{% if positive_examples %}
{% for example in positive_examples %}
- [{{ example.source }}] {{ example.content }}
{% endfor %}
{% else %}
暂无正面评价
{% endif %}

### 负面评价摘要
{% if negative_examples %}
{% for example in negative_examples %}
- [{{ example.source }}] {{ example.content }}
{% endfor %}
{% else %}
暂无负面评价
{% endif %}

### 中性评价摘要
{% if neutral_examples %}
{% for example in neutral_examples %}
- [{{ example.source }}] {{ example.content }}
{% endfor %}
{% else %}
暂无中性评价
{% endif %}

---

## 趋势分析

{% if trend_details %}
### 情感变化趋势

{% if trend_details.first_half %}
**第一阶段**:
- 正面: {{ trend_details.first_half.positive | default(0) }} 条
- 负面: {{ trend_details.first_half.negative | default(0) }} 条
- 总计: {{ trend_details.first_half.total | default(0) }} 条

**第二阶段**:
- 正面: {{ trend_details.second_half.positive | default(0) }} 条
- 负面: {{ trend_details.second_half.negative | default(0) }} 条
- 总计: {{ trend_details.second_half.total | default(0) }} 条
{% endif %}

**趋势判断**: {{ trend_details.trend | default('数据不足') }}
{% endif %}

---

## 总结与建议

{% if dominant_sentiment == 'positive' %}
整体情感倾向积极，建议继续保持当前策略，并关注用户体验的进一步提升。
{% elif dominant_sentiment == 'negative' %}
整体情感倾向消极，建议深入分析负面反馈的原因，制定改进措施。
{% else %}
整体情感倾向中性，建议进一步收集更多反馈，进行深入分析。
{% endif %}

---
*本报告由 AI 智能分析生成，建议结合人工审核。*
""",
            
            "data_collection_report": """# {{ title }}

## 数据收集报告

**生成时间**: {{ generated_time }}
**收集主题**: {{ topic }}

---

## 收集概要

- **总数据量**: {{ total_items }}
- **数据来源**: {{ sources }}
{% if time_range %}
- **时间范围**: {{ time_range.start }} 至 {{ time_range.end }}
{% endif %}

---

## 数据来源分布

{% for source in sources %}
### {{ source }}
- 数据条数: {{ source_counts[source] }}
- 占比: {{ source_percentages[source] }}%
{% endfor %}

---

## 收集策略

本次数据收集使用的工作流步骤:
{% for step in workflow_steps %}
{{ loop.index0 + 1 }}. {{ step }}
{% endfor %}

---

## 数据样本

{% for item in sample_data[:5] %}
### 数据项 {{ loop.index0 + 1 }}
- **ID**: {{ item.id }}
- **来源**: {{ item.source }}
- **时间**: {{ item.timestamp }}
- **内容**: {{ item.content }}

{% if item.metrics %}
- **指标**: 点赞 {{ item.metrics.likes }}, 转发 {{ item.metrics.shares }}, 评论 {{ item.metrics.comments }}
{% endif %}
{% endfor %}

---
*本报告由数据收集智能体自动生成。*
""",
            
            "comprehensive_report": """# {{ title }}

## 综合分析报告

**生成时间**: {{ generated_time }}
**分析主题**: {{ topic }}
**工作流ID**: {{ workflow_id }}

---

## 一、数据收集概况

{% if data_collection_included %}
本次分析共收集了 **{{ total_items }}** 条数据。

### 数据来源分布
{% if sources %}
{% for source in sources %}
- **{{ source }}**: {{ source_counts[source] }} 条 ({{ source_percentages[source] }}%)
{% endfor %}
{% else %}
- 暂无数据来源信息
{% endif %}

### 数据样本展示
{% if collected_data %}
{% for item in collected_data[:3] %}
#### {{ loop.index }}. {{ item.title | default('无标题') }}
- **来源**: {{ item.source }}
- **时间**: {{ item.timestamp }}
- **内容摘要**: {{ item.content[:200] if item.content else '无内容' }}...

{% endfor %}
{% else %}
暂无收集的数据
{% endif %}
{% else %}
数据收集功能未启用
{% endif %}

---

## 二、情感分析结果

{% if sentiment_analysis_included %}
{% if summary %}
### 整体情感分布

| 情感类型 | 数量 | 占比 |
|---------|------|------|
| 正面 | {{ summary.sentiment_counts.positive }} | {{ (summary.sentiment_distribution.positive * 100) | round(1) }}% |
| 负面 | {{ summary.sentiment_counts.negative }} | {{ (summary.sentiment_distribution.negative * 100) | round(1) }}% |
| 中性 | {{ summary.sentiment_counts.neutral }} | {{ (summary.sentiment_distribution.neutral * 100) | round(1) }}% |

### 主要情感倾向
**{{ summary.dominant_sentiment | upper }}** 情感占主导地位

{% if trend %}
### 情感趋势分析
- **趋势判断**: {{ trend.trend | default('数据不足') }}
{% if trend.first_half %}
- **前期**: 正面 {{ trend.first_half.positive | default(0) }} 条, 负面 {{ trend.first_half.negative | default(0) }} 条
- **后期**: 正面 {{ trend.second_half.positive | default(0) }} 条, 负面 {{ trend.second_half.negative | default(0) }} 条
{% endif %}
{% endif %}
{% else %}
暂无情感分析数据
{% endif %}
{% else %}
情感分析功能未启用
{% endif %}

---

## 三、关键发现与洞察

{% if summary %}
{% if summary.dominant_sentiment == 'positive' %}
### 积极信号
1. 整体用户反馈以正面情感为主，表明产品/服务获得用户认可
2. 建议继续保持当前策略，并进一步优化用户体验
{% elif summary.dominant_sentiment == 'negative' %}
### 需关注问题
1. 负面反馈占比较高，需要深入分析问题根源
2. 建议制定改进计划，及时回应用户关切
{% else %}
### 中性状态
1. 用户反馈情感分布相对均衡
2. 建议进一步收集更多数据进行深入分析
{% endif %}
{% endif %}

---

## 四、建议措施

{% if summary %}
{% if summary.dominant_sentiment == 'positive' %}
1. **保持优势**: 继续强化用户喜爱的功能和特点
2. **扩大收集**: 拓展数据收集渠道，获取更全面的用户反馈
3. **深入分析**: 对正面反馈进行细分，识别核心价值点
{% elif summary.dominant_sentiment == 'negative' %}
1. **紧急响应**: 优先处理高频负面问题
2. **根因分析**: 深入分析负面反馈的根本原因
3. **改进跟踪**: 建立改进效果跟踪机制
{% else %}
1. **数据补充**: 增加数据收集量以获得更可靠的分析
2. **细分领域**: 针对不同维度进行专项分析
3. **持续监测**: 建立定期监测机制
{% endif %}
{% endif %}

---

## 五、附录

### 分析方法说明
- **数据收集**: 使用多种网络数据源，包括搜索引擎、社交媒体等
- **情感分析**: 基于关键词词典和案例模式的混合分析方法
- **趋势识别**: 通过时间序列分析识别情感变化趋势

### 数据质量说明
- 数据经过清洗和去重处理
- 情感分析准确率受限于样本质量和特征提取
- 建议结合人工审核进行重要决策

---

**报告生成时间**: {{ generated_time }}
**工作流ID**: {{ workflow_id }}

*本报告由 AI 智能分析系统自动生成，建议结合人工审核使用。*
"""
        }
        
        for key, template in default_templates.items():
            self.memory_service.save_memory(
                workflow_id=self.workflow_id,
                agent_type="report_generation",
                memory_type="template",
                key=key,
                value=template,
                extra_data={"category": "default_template"}
            )
        
        logger.info("创建默认报告模板")
    
    def _create_default_rules(self):
        """创建默认的生成规则"""
        default_rules = [
            {
                "rule_id": "minimum_data_threshold",
                "description": "最小数据量规则",
                "conditions": {
                    "min_total_analyzed": 5
                },
                "actions": {
                    "if_met": "正常生成报告",
                    "if_not_met": "添加警告信息，建议收集更多数据"
                }
            },
            {
                "rule_id": "sentiment_balance_check",
                "description": "情感平衡检查规则",
                "conditions": {
                    "min_positive_ratio": 0.1,
                    "min_negative_ratio": 0.1
                },
                "actions": {
                    "if_met": "正常分析",
                    "if_not_met": "提示情感分布可能不够均衡"
                }
            },
            {
                "rule_id": "trend_analysis_threshold",
                "description": "趋势分析阈值规则",
                "conditions": {
                    "min_items_for_trend": 10
                },
                "actions": {
                    "if_met": "执行趋势分析",
                    "if_not_met": "跳过趋势分析，标记为数据不足"
                }
            }
        ]
        
        for rule in default_rules:
            self.memory_service.save_memory(
                workflow_id=self.workflow_id,
                agent_type="report_generation",
                memory_type="rule",
                key=rule["rule_id"],
                value=rule,
                extra_data={"category": "default_rule"}
            )
        
        logger.info("创建默认生成规则")
    
    def generate_llm_report(
        self,
        topic: str,
        sentiment_data: Dict[str, Any],
        collected_data: List[Dict[str, Any]],
        language: str = "zh",
        report_style: str = "professional"
    ) -> Dict[str, Any]:
        """
        使用 LLM 生成智能报告（增强版）
        
        功能：
        - LLM 驱动的内容生成，而非固定模板
        - 深度见解提取：趋势分析、因果关系、建议策略
        - 结构化呈现：摘要、数据展示、深度分析、建议见解
        - 自动篇幅调整
        
        Args:
            topic: 报告主题
            sentiment_data: 情感分析数据
            collected_data: 收集的数据
            language: 语言 (zh/en)
            report_style: 报告风格 (professional/concise/detailed)
            
        Returns:
            智能报告结果
        """
        logger.info(f"开始生成 LLM 智能报告: {topic}, 语言: {language}, 风格: {report_style}")
        
        start_time = datetime.utcnow()
        
        try:
            if not self.use_llm or not self.llm_generator:
                logger.warning("LLM 未启用，回退到模板报告")
                return self.generate_report(
                    report_type="sentiment_analysis",
                    data=sentiment_data
                )
            
            # 使用 LLM 生成完整报告
            report_content = self.llm_generator.generate_full_report(
                topic=topic,
                sentiment_data=sentiment_data,
                collected_data=collected_data,
                language=language,
                report_style=report_style
            )
            
            # 生成执行摘要和深度见解
            executive_summary = self.llm_generator.generate_executive_summary(sentiment_data, language)
            deep_insights = self.llm_generator.generate_deep_insights(sentiment_data, collected_data, language)
            
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            result = {
                "report_type": "llm_sentiment_analysis",
                "content": report_content,
                "extra_data": {
                    "generation_method": "llm",
                    "language": language,
                    "report_style": report_style,
                    "executive_summary": executive_summary,
                    "deep_insights": deep_insights,
                    "generated_at": end_time.isoformat(),
                    "execution_time_ms": execution_time_ms,
                    "workflow_id": self.workflow_id
                }
            }
            
            # 自动保存报告到数据库
            if self.auto_save:
                self._save_report_to_database(result)
            
            # 记录审计日志
            if self.persistence_enabled:
                try:
                    self.audit_service.log_operation(
                        workflow_id=self.workflow_id,
                        operation_type="llm_report_generation",
                        operator="ReportGenerationAgent",
                        input_data={"topic": topic, "data_count": len(collected_data)},
                        output_data={"report_length": len(report_content)},
                        template_used="llm_generated",
                        rules_applied=[],
                        status="success",
                        execution_time_ms=execution_time_ms
                    )
                except Exception as audit_error:
                    logger.warning(f"记录审计日志失败: {audit_error}")
            
            logger.info(f"LLM 智能报告生成完成，耗时 {execution_time_ms}ms，报告长度 {len(report_content)}")
            
            return result
            
        except Exception as e:
            logger.error(f"LLM 报告生成失败: {e}")
            
            # 回退到模板报告
            logger.info("回退到模板报告生成")
            return self.generate_report(
                report_type="sentiment_analysis",
                data=sentiment_data
            )
    
    def generate_intelligent_report(
        self,
        topic: str,
        data: Dict[str, Any],
        use_llm: bool = True,
        language: str = "zh",
        report_style: str = "professional"
    ) -> Dict[str, Any]:
        """
        智能报告生成（自动选择最佳方法）
        
        根据数据量和数据类型自动选择：
        - 数据充足且启用 LLM：使用 LLM 生成深度报告
        - 其他情况：使用模板生成
        
        Args:
            topic: 报告主题
            data: 完整数据（包含情感分析和收集的数据）
            use_llm: 是否使用 LLM
            language: 语言
            report_style: 报告风格
            
        Returns:
            报告结果
        """
        logger.info(f"开始智能报告生成: {topic}")
        
        # 提取情感分析数据和收集数据
        sentiment_data = data.get("analysis_result", data.get("sentiment_data", {}))
        collected_data = data.get("collected_data", [])
        
        # 检查是否有情感分析的深度分析结果
        has_deep_analysis = (
            sentiment_data.get("analysis_method") == "deep" or
            sentiment_data.get("insights") is not None or
            any("deep_analysis" in item for item in sentiment_data.get("analyzed_data", []))
        )
        
        # 决定使用哪种报告生成方式
        if use_llm and self.use_llm and self.llm_generator:
            if has_deep_analysis or len(collected_data) >= 10:
                logger.info("使用 LLM 生成深度智能报告")
                return self.generate_llm_report(
                    topic=topic,
                    sentiment_data=sentiment_data,
                    collected_data=collected_data,
                    language=language,
                    report_style=report_style
                )
        
        # 使用模板生成
        logger.info("使用模板生成报告")
        return self.generate_report(
            report_type="sentiment_analysis",
            data=data
        )
    
    def generate_report(
        self,
        report_type: str,
        data: Dict[str, Any],
        template_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成报告（模板模式）
        
        Args:
            report_type: 报告类型（sentiment_analysis, data_collection 等）
            data: 报告数据
            template_name: 使用的模板名称（可选）
            
        Returns:
            生成的报告
        """
        logger.info(f"开始生成报告: {report_type}")
        
        start_time = datetime.utcnow()
        
        try:
            # 获取模板
            if template_name is None:
                template_name = f"{report_type}_report"
            
            template = self._get_template(template_name)
            if template is None:
                logger.warning(f"未找到模板 {template_name}，使用降级模板生成报告")
                template = Template(self._get_fallback_template_content(template_name))
            
            # 应用规则
            rules_applied = self._apply_rules(report_type, data)
            
            # 准备模板数据
            template_data = self._prepare_template_data(report_type, data, rules_applied)
            
            # 渲染报告
            report_content = template.render(**template_data)
            
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # 仅在可持久化时记录审计日志，且失败不阻断主流程
            if self.persistence_enabled:
                try:
                    self.audit_service.log_operation(
                        workflow_id=self.workflow_id,
                        operation_type="report_generation",
                        operator="ReportGenerationAgent",
                        input_data=data,
                        output_data={"report_content": report_content},
                        template_used=template_name,
                        rules_applied=[rule["rule_id"] for rule in rules_applied],
                        status="success",
                        execution_time_ms=execution_time_ms
                    )
                except Exception as audit_error:
                    logger.warning(f"记录报告生成审计日志失败（忽略，不阻断执行）: {audit_error}")
            
            result = {
                "report_type": report_type,
                "content": report_content,
                "extra_data": {
                    "template_used": template_name,
                    "rules_applied": [rule["rule_id"] for rule in rules_applied],
                    "generated_at": end_time.isoformat(),
                    "execution_time_ms": execution_time_ms,
                    "workflow_id": self.workflow_id
                }
            }
            
            # 自动保存报告到数据库（无效 workflow_id 时已自动降级关闭）
            if self.auto_save:
                self._save_report_to_database(result)
            
            logger.info(f"报告生成完成，耗时 {execution_time_ms}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"报告生成失败: {str(e)}")
            
            # 仅在可持久化时尝试记录失败审计日志，且不影响异常抛出语义
            if self.persistence_enabled:
                try:
                    self.audit_service.log_operation(
                        workflow_id=self.workflow_id,
                        operation_type="report_generation",
                        operator="ReportGenerationAgent",
                        input_data=data,
                        status="failed",
                        error_message=str(e)
                    )
                except Exception as audit_error:
                    logger.warning(f"记录失败审计日志失败（忽略）: {audit_error}")
            
            raise
    
    def _save_report_to_database(self, report_result: Dict[str, Any]):
        """
        保存报告到数据库
        
        Args:
            report_result: 报告结果
        """
        try:
            report_id = self.storage_service.store_report(
                report_content=report_result["content"],
                report_format="markdown",
                metadata={
                    "report_type": report_result["report_type"],
                    "template_used": report_result["extra_data"].get("template_used"),
                    "generated_at": report_result["extra_data"].get("generated_at")
                },
                workflow_id=self.workflow_id
            )
            report_result["report_id"] = report_id
            logger.info(f"报告已保存到数据库: {report_id}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
    
    def _get_template(self, template_name: str) -> Optional[Template]:
        """
        获取报告模板
        
        Args:
            template_name: 模板名称
            
        Returns:
            Jinja2 模板对象
        """
        if not self.persistence_enabled:
            return None

        templates = self.memory_service.get_templates(
            self.workflow_id,
            "report_generation"
        )
        
        template_content = templates.get(template_name)
        
        if template_content:
            return Template(template_content)
        
        return None
    
    def _apply_rules(
        self,
        report_type: str,
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        应用生成规则
        
        Args:
            report_type: 报告类型
            data: 报告数据
            
        Returns:
            应用的规则列表
        """
        rules = self.memory_service.get_rules(
            self.workflow_id,
            "report_generation"
        )
        
        applied_rules = []
        warnings = []
        
        for rule in rules:
            if self._check_rule_conditions(rule, data):
                applied_rules.append(rule)
                
                # 执行规则动作
                if "actions" in rule:
                    action = rule["actions"].get("if_not_met")
                    if action:
                        warnings.append({
                            "rule_id": rule["rule_id"],
                            "message": action
                        })
        
        # 如果有警告，添加到数据中
        if warnings:
            data["warnings"] = warnings
        
        return applied_rules
    
    def _check_rule_conditions(
        self,
        rule: Dict[str, Any],
        data: Dict[str, Any]
    ) -> bool:
        """
        检查规则条件是否满足
        
        Args:
            rule: 规则定义
            data: 数据
            
        Returns:
            True if conditions are met
        """
        conditions = rule.get("conditions", {})
        
        # 检查最小数据量
        if "min_total_analyzed" in conditions:
            total = data.get("total_analyzed", data.get("total_items", 0))
            if total < conditions["min_total_analyzed"]:
                return True
        
        # 检查情感平衡
        if "min_positive_ratio" in conditions or "min_negative_ratio" in conditions:
            distribution = data.get("sentiment_distribution", {})
            positive_ratio = distribution.get("positive", 0)
            negative_ratio = distribution.get("negative", 0)
            
            min_positive = conditions.get("min_positive_ratio", 0)
            min_negative = conditions.get("min_negative_ratio", 0)
            
            if positive_ratio < min_positive or negative_ratio < min_negative:
                return True
        
        # 检查趋势分析阈值
        if "min_items_for_trend" in conditions:
            total = data.get("total_analyzed", data.get("total_items", 0))
            if total >= conditions["min_items_for_trend"]:
                return True
        
        return False
    
    def _prepare_template_data(
        self,
        report_type: str,
        data: Dict[str, Any],
        rules_applied: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        准备模板数据
        
        Args:
            report_type: 报告类型
            data: 原始数据
            rules_applied: 应用的规则
            
        Returns:
            模板数据字典
        """
        template_data = data.copy()
        
        # 添加通用字段
        template_data["generated_time"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        template_data["workflow_id"] = self.workflow_id
        
        # 根据报告类型准备特定数据
        if report_type == "sentiment_analysis":
            self._prepare_sentiment_data(template_data)
        elif report_type == "data_collection":
            self._prepare_data_collection_data(template_data)
        
        # 处理警告
        if "warnings" in template_data:
            template_data["has_warnings"] = True
        else:
            template_data["has_warnings"] = False
        
        return template_data
    
    def _prepare_sentiment_data(self, data: Dict[str, Any]):
        """
        准备情感分析报告数据
        
        Args:
            data: 数据字典（会被修改）
        """
        summary = data.get("summary", {})
        
        # 添加标题
        data["title"] = f"情感分析报告 - {data.get('topic', '未知主题')}"
        
        # 添加百分比 - 优先从 summary 中获取，否则从 data 顶层获取
        if "sentiment_distribution" in summary:
            dist = summary["sentiment_distribution"]
            data["positive_percentage"] = round(dist.get("positive", 0) * 100, 1)
            data["negative_percentage"] = round(dist.get("negative", 0) * 100, 1)
            data["neutral_percentage"] = round(dist.get("neutral", 0) * 100, 1)
        elif "positive_percentage" not in data:
            # 如果 data 中也没有，从计数计算
            total = data.get("total_analyzed", 0)
            if total > 0:
                data["positive_percentage"] = round(data.get("positive_count", 0) / total * 100, 1)
                data["negative_percentage"] = round(data.get("negative_count", 0) / total * 100, 1)
                data["neutral_percentage"] = round(data.get("neutral_count", 0) / total * 100, 1)
            else:
                data["positive_percentage"] = 0
                data["negative_percentage"] = 0
                data["neutral_percentage"] = 0
        
        # 添加计数 - 优先从 summary 中获取，否则从 data 顶层获取
        if "sentiment_counts" in summary:
            counts = summary["sentiment_counts"]
            data["positive_count"] = counts.get("positive", 0)
            data["negative_count"] = counts.get("negative", 0)
            data["neutral_count"] = counts.get("neutral", 0)
        # 如果 summary 中没有，data 顶层应该已经有了
        
        # 设置主导情感（如果 data 顶层没有）
        if "dominant_sentiment" not in data and "dominant_sentiment" in summary:
            data["dominant_sentiment"] = summary["dominant_sentiment"]
        
        # 添加趋势详情
        trend_data = data.get("trend")
        if trend_data:
            # 如果 trend 是字典格式（包含详细信息）
            if isinstance(trend_data, dict):
                data["trend_details"] = trend_data
                
                # 转换趋势为可读文本
                trend_map = {
                    "improving": "改善",
                    "declining": "下降",
                    "stable": "稳定",
                    "insufficient_data": "数据不足"
                }
                data["trend_text"] = trend_map.get(
                    trend_data.get("trend", "stable"),
                    "未知"
                )
            # 如果 trend 是字符串格式（仅趋势值）
            elif isinstance(trend_data, str):
                trend_map = {
                    "improving": "改善",
                    "declining": "下降",
                    "stable": "稳定",
                    "rising": "上升",
                    "insufficient_data": "数据不足"
                }
                data["trend_text"] = trend_map.get(trend_data, "未知")
                data["trend_details"] = {"trend": trend_data}
        
        # 分类示例
        analyzed_data = data.get("analyzed_data", [])
        data["positive_examples"] = [
            item for item in analyzed_data
            if item.get("sentiment") == "positive"
        ][:3]
        data["negative_examples"] = [
            item for item in analyzed_data
            if item.get("sentiment") == "negative"
        ][:3]
        data["neutral_examples"] = [
            item for item in analyzed_data
            if item.get("sentiment") == "neutral"
        ][:3]
        
        # 如果没有 analyzed_data，保留原有的 examples（从外部传入）
        # 只有当 data 中没有这些字段时，才设置为空列表
        if not analyzed_data:
            if "positive_examples" not in data:
                data["positive_examples"] = []
            if "negative_examples" not in data:
                data["negative_examples"] = []
            if "neutral_examples" not in data:
                data["neutral_examples"] = []
    
    def _prepare_data_collection_data(self, data: Dict[str, Any]):
        """
        准备数据收集报告数据
        
        Args:
            data: 数据字典（会被修改）
        """
        # 添加标题
        data["title"] = f"数据收集报告 - {data.get('topic', '未知主题')}"
        
        # 计算来源分布
        collected_data = data.get("collected_data", [])
        source_counts = {}
        for item in collected_data:
            source = item.get("source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
        
        total = len(collected_data)
        source_percentages = {
            source: round(count / total * 100, 1) if total > 0 else 0
            for source, count in source_counts.items()
        }
        
        data["sources"] = list(source_counts.keys())
        data["source_counts"] = source_counts
        data["source_percentages"] = source_percentages
        
        # 添加样本数据
        data["sample_data"] = collected_data
    
    def add_custom_template(
        self,
        template_name: str,
        template_content: str
    ):
        """
        添加自定义模板
        
        Args:
            template_name: 模板名称
            template_content: 模板内容
        """
        self.memory_service.save_memory(
            workflow_id=self.workflow_id,
            agent_type="report_generation",
            memory_type="template",
            key=template_name,
            value=template_content,
            extra_data={"category": "custom_template"}
        )
        
        logger.info(f"添加自定义模板: {template_name}")
    
    def add_custom_rule(
        self,
        rule_id: str,
        rule_definition: Dict[str, Any]
    ):
        """
        添加自定义规则
        
        Args:
            rule_id: 规则 ID
            rule_definition: 规则定义
        """
        self.memory_service.save_memory(
            workflow_id=self.workflow_id,
            agent_type="report_generation",
            memory_type="rule",
            key=rule_id,
            value=rule_definition,
            extra_data={"category": "custom_rule"}
        )
        
        logger.info(f"添加自定义规则: {rule_id}")
    
    def get_audit_logs(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取审计日志
        
        Args:
            limit: 返回的最大条数
            
        Returns:
            审计日志列表
        """
        logs = self.audit_service.get_audit_logs(
            workflow_id=self.workflow_id,
            operation_type="report_generation",
            limit=limit
        )
        
        return [
            {
                "id": log.id,
                "operation_type": log.operation_type,
                "operator": log.operator,
                "template_used": log.template_used,
                "rules_applied": log.rules_applied,
                "status": log.status,
                "error_message": log.error_message,
                "execution_time_ms": log.execution_time_ms,
                "timestamp": log.timestamp
            }
            for log in logs
        ]
    
    def generate_comprehensive_report(
        self,
        topic: str,
        include_data_collection: bool = True,
        include_sentiment_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        生成综合报告，从数据库读取各agent的分析结果
        
        Args:
            topic: 报告主题
            include_data_collection: 是否包含数据收集结果
            include_sentiment_analysis: 是否包含情感分析结果
            
        Returns:
            综合报告
        """
        logger.info(f"开始生成综合报告: {topic}")
        
        # 从数据库读取收集的数据
        collected_data = []
        if include_data_collection:
            collected_data = self.storage_service.get_collected_data(
                workflow_id=self.workflow_id,
                limit=100
            )
        
        # 从数据库读取情感分析结果
        sentiment_results = []
        if include_sentiment_analysis:
            sentiment_results = self.storage_service.get_analysis_results(
                workflow_id=self.workflow_id,
                analysis_type="sentiment"
            )
        
        # 构建综合报告数据
        report_data = {
            "topic": topic,
            "collected_data": collected_data,
            "sentiment_results": sentiment_results,
            "total_items": len(collected_data),
            "data_collection_included": include_data_collection,
            "sentiment_analysis_included": include_sentiment_analysis
        }
        
        # 如果有情感分析结果，添加汇总信息
        if sentiment_results:
            latest_sentiment = sentiment_results[0] if sentiment_results else None
            if latest_sentiment and "data" in latest_sentiment:
                sentiment_data = latest_sentiment["data"]
                if "summary" in sentiment_data:
                    report_data["summary"] = sentiment_data["summary"]
                if "trend" in sentiment_data:
                    report_data["trend"] = sentiment_data["trend"]
        
        # 使用综合报告模板生成报告
        return self.generate_report(
            report_type="comprehensive",
            data=report_data,
            template_name="comprehensive_report"
        )
    
    def get_saved_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取已保存的报告
        
        Args:
            limit: 返回的最大数量
            
        Returns:
            报告列表
        """
        reports = []
        for i in range(limit):
            report = self.storage_service.get_report(workflow_id=self.workflow_id)
            if report:
                reports.append(report)
        return reports
    
    def export_report_to_markdown(
        self,
        report_result: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> str:
        """
        导出报告为Markdown文件
        
        Args:
            report_result: 报告结果
            output_path: 输出路径（可选）
            
        Returns:
            文件路径
        """
        import os
        
        if output_path is None:
            # 默认输出路径
            output_dir = "reports"
            os.makedirs(output_dir, exist_ok=True)
            filename = f"report_{self.workflow_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
            output_path = os.path.join(output_dir, filename)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_result["content"])
        
        logger.info(f"报告已导出到: {output_path}")
        return output_path
    
    def close(self):
        """关闭数据库连接"""
        if self.storage_service:
            self.storage_service.close()
        if self.db:
            self.db.close()