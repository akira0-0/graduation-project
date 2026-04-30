"""
报告生成智能体节点（增强版）
继承 BaseNode，集成 ReportGenerationAgent 的功能

增强功能：
- LLM 驱动的智能报告生成：使用 LLM 生成内容，而非固定模板
- 深度见解提取：提供趋势分析、因果关系、建议策略
- 结构化呈现：摘要、数据展示、深度分析、建议见解
- 自动篇幅调整：根据数据重要性自动调整篇幅
- 多语言支持：支持中英文报告生成
"""
from typing import Any, Dict
from datetime import datetime
from .base import BaseNode
from ..core.schema import NodeDefinition, WorkflowState
from ..agents.report_generation_agent import ReportGenerationAgent
from ..utils.logger import get_logger

logger = get_logger("report_agent_node")


class ReportAgentNode(BaseNode):
    """报告生成智能体节点（增强版）"""
    
    def _build_fallback_report_content(
        self,
        report_type: str,
        report_data: Dict[str, Any],
        error_message: str = ""
    ) -> str:
        """构建最少可读内容兜底报告，确保 report_content 非空"""
        topic = report_data.get("topic") or "未提供主题"
        generated_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        total_analyzed = report_data.get("total_analyzed", 0)

        lines = [
            f"# {report_type} 报告（降级）",
            "",
            f"- 生成时间: {generated_time}",
            f"- 主题: {topic}",
            f"- 数据条数: {total_analyzed}",
            "",
            "## 说明",
            "本次执行进入降级模式：主流程保持 completed，报告内容为兜底输出。",
        ]
        if error_message:
            lines.extend(["", "## 错误摘要", error_message])

        return "\n".join(lines)
    
    def __init__(self, node_def: NodeDefinition):
        """
        初始化报告生成智能体节点
        
        Args:
            node_def: 节点定义
        """
        super().__init__(node_def)
        self.agent = None
        
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        执行报告生成（增强版）
        
        支持两种模式：
        1. LLM 智能报告（默认）：使用 LLM 生成深度分析报告
        2. 模板报告：使用预设模板生成报告
        
        Args:
            state: 工作流状态
            
        Returns:
            生成的报告
        """
        logger.info(f"执行报告生成智能体节点: {self.node_id}")
        
        try:
            # 获取参数
            report_type = self.get_input_value(state, "report_type") or "sentiment_analysis"
            template_name = self.get_input_value(state, "template") or "default"
            format_type = self.get_input_value(state, "format") or "markdown"
            
            # 增强参数
            use_llm_report = self.get_input_value(state, "use_llm_report")
            if use_llm_report is None:
                use_llm_report = True  # 默认使用 LLM 报告
            
            language = self.get_input_value(state, "language") or "zh"
            report_style = self.get_input_value(state, "report_style") or "professional"
            topic = self.get_input_value(state, "topic") or "数据分析报告"
            
            # 获取数据源引用 - 从 params 中直接获取
            data_sources_config = self.config.params.get("data_sources", [])
            
            # 收集数据
            data = {}
            
            # 如果指定了数据源引用
            if isinstance(data_sources_config, list):
                for source_ref in data_sources_config:
                    if isinstance(source_ref, str) and source_ref.startswith("$"):
                        # 引用前序节点，如 "$data_collector"
                        node_id = source_ref[1:]  # 移除 $ 前缀
                        # 从 node_outputs 中获取
                        if node_id in state.node_outputs:
                            data[node_id] = state.node_outputs[node_id]
                            logger.info(f"从节点 {node_id} 获取数据")
                        else:
                            logger.warning(f"未找到节点 {node_id} 的输出")
                    elif isinstance(source_ref, str):
                        # 直接是节点 ID
                        if source_ref in state.node_outputs:
                            data[source_ref] = state.node_outputs[source_ref]
            else:
                # 自动收集所有前序节点的输出
                for node_id, output in state.node_outputs.items():
                    if node_id != self.node_id:  # 排除自己的输出
                        data[node_id] = output
            
            logger.info(f"收集了 {len(data)} 个数据源，LLM报告: {use_llm_report}")
            
            # 准备报告数据
            report_data = self._prepare_report_data(data, report_type)
            
            # 从状态中获取 workflow_id（仅使用数据库主键ID）
            workflow_id = state.workflow_id
            
            # 初始化智能体（启用 LLM 增强功能）
            self.agent = ReportGenerationAgent(
                workflow_id=workflow_id,
                use_llm=use_llm_report
            )
            
            # 根据模式选择报告生成方式
            if use_llm_report:
                if report_type == "sentiment_analysis":
                    logger.info("使用 LLM 智能报告生成模式（情感分析）")
                    
                    # 提取情感分析数据和收集数据
                    sentiment_data = report_data.get("analysis_result", report_data)
                    collected_data = report_data.get("collected_data", [])
                    
                    # 如果有原始数据，提取 collected_data
                    for node_id, node_output in data.items():
                        if "collected_data" in node_output:
                            collected_data = node_output["collected_data"]
                            break
                    
                    report_result = self.agent.generate_llm_report(
                        topic=topic,
                        sentiment_data=sentiment_data,
                        collected_data=collected_data,
                        language=language,
                        report_style=report_style
                    )
                else:
                    # 非情感分析类型的 LLM 报告，使用通用 LLM 报告生成
                    logger.info(f"使用 LLM 通用报告生成模式（报告类型: {report_type}）")
                    report_result = self._generate_llm_generic_report(
                        topic=topic,
                        report_type=report_type,
                        report_data=report_data,
                        data=data,
                        language=language,
                        report_style=report_style
                    )
            else:
                logger.info("使用模板报告生成模式")
                report_result = self.agent.generate_report(
                    report_type=report_type,
                    data=report_data
                )

            # 兼容不同返回格式，统一抽取文本内容
            if isinstance(report_result, dict):
                report_text = str(report_result.get("content", "") or "").strip()
            else:
                report_text = str(report_result or "").strip()

            # 最少可读内容兜底：即使降级/部分失败也保证非空
            result_status = "success"
            if not report_text:
                report_text = self._build_fallback_report_content(
                    report_type=report_type,
                    report_data=report_data,
                    error_message="报告渲染结果为空，已自动使用兜底内容。"
                )
                result_status = "degraded"

            # 返回结果
            return {
                "status": result_status,
                "report_type": report_result.get("report_type", report_type) if isinstance(report_result, dict) else report_type,
                "template": template_name,
                "format": format_type,
                "report_content": report_text,
                "report_result": report_result if isinstance(report_result, dict) else None,
                "generation_method": report_result.get("extra_data", {}).get("generation_method", "template") if isinstance(report_result, dict) else "template",
                "language": language,
                "report_style": report_style,
                "message": f"成功生成{report_type}类型报告（{'LLM智能' if use_llm_report else '模板'}模式）"
            }
            
        except Exception as e:
            logger.error(f"报告生成失败: {e}", exc_info=True)
            fallback_report = self._build_fallback_report_content(
                report_type=report_type if 'report_type' in locals() else "sentiment_analysis",
                report_data=report_data if 'report_data' in locals() else {},
                error_message=str(e)
            )
            return {
                "status": "degraded",
                "error": str(e),
                "report_content": fallback_report
            }
    
    def _prepare_report_data(self, data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
        """
        准备报告数据（增强版）
        
        支持从深度分析结果中提取数据
        
        Args:
            data: 收集的数据
            report_type: 报告类型
            
        Returns:
            准备好的报告数据
        """
        report_data = {
            "title": "分析报告",
            "generated_time": "",
            "topic": "数据分析",
            "sources": [],
            "total_analyzed": 0
        }
        
        # 根据报告类型准备数据
        if report_type == "sentiment_analysis":
            # 合并所有情感分析结果
            sentiment_data = {}
            collected_data = []
            deep_summary = {}
            insights = {}
            trend_prediction = {}
            
            for node_id, output in data.items():
                # 获取情感分析结果
                if "analysis_result" in output:
                    sentiment_data = output["analysis_result"]
                    # 提取深度分析结果
                    deep_summary = output.get("deep_summary", {})
                    insights = output.get("insights", {})
                    trend_prediction = output.get("trend_prediction", {})
                
                # 获取收集的数据
                if "collected_data" in output:
                    collected_data = output["collected_data"]
            
            # 从 summary 中提取数据
            summary = sentiment_data.get("summary", {})
            sentiment_counts = summary.get("sentiment_counts", {})
            sentiment_distribution = summary.get("sentiment_distribution", {})
            
            # 计算百分比
            total_analyzed = summary.get("total_analyzed", 0)
            
            report_data.update({
                "topic": sentiment_data.get("topic", "用户反馈"),
                "total_analyzed": total_analyzed,
                "positive_count": sentiment_counts.get("positive", 0),
                "negative_count": sentiment_counts.get("negative", 0),
                "neutral_count": sentiment_counts.get("neutral", 0),
                "dominant_sentiment": summary.get("dominant_sentiment", "neutral"),
                "trend": sentiment_data.get("trend", "stable"),
                "positive_percentage": round(sentiment_distribution.get("positive", 0) * 100, 1),
                "negative_percentage": round(sentiment_distribution.get("negative", 0) * 100, 1),
                "neutral_percentage": round(sentiment_distribution.get("neutral", 0) * 100, 1),
                "positive_examples": sentiment_data.get("positive_examples", []),
                "negative_examples": sentiment_data.get("negative_examples", []),
                "neutral_examples": sentiment_data.get("neutral_examples", []),
                "summary": summary,
                "sources": ["互联网搜索", "知识库"],
                # 增强数据
                "analysis_result": sentiment_data,
                "collected_data": collected_data,
                "deep_summary": deep_summary,
                "insights": insights,
                "trend_prediction": trend_prediction,
                "analysis_method": sentiment_data.get("analysis_method", "basic")
            })
        
        elif report_type == "data_collection":
            # 合并所有数据收集结果
            collected_data = []
            data_collector_output = {}
            for node_id, output in data.items():
                if "collected_data" in output:
                    collected_data = output["collected_data"]
                    data_collector_output = output
                    break
            
            # 提取数据来源
            sources = data_collector_output.get("sources", ["互联网搜索", "知识库"])
            if isinstance(sources, list):
                sources_str = ", ".join(sources)
            else:
                sources_str = str(sources)
            
            # 提取质量统计
            quality_stats = data_collector_output.get("quality_stats", {})
            
            report_data.update({
                "topic": data_collector_output.get("topic", "数据收集报告"),
                "total_analyzed": len(collected_data),
                "sources": sources_str,
                "data_count": len(collected_data),
                "collected_data": collected_data[:5],  # 只保留前5条作为样本
                "quality_stats": quality_stats,
                "target_achieved": data_collector_output.get("target_achieved", False),
                "collection_method": data_collector_output.get("collection_method", "traditional")
            })
        
        return report_data
    
    def _generate_llm_generic_report(
        self,
        topic: str,
        report_type: str,
        report_data: Dict[str, Any],
        data: Dict[str, Any],
        language: str = "zh",
        report_style: str = "professional"
    ) -> Dict[str, Any]:
        """
        使用 LLM 生成通用报告（支持多种报告类型）
        
        这是降级策略的核心：当报告类型不是 sentiment_analysis 时，
        使用 LLM 动态生成报告模板，确保可以生成有效报告。
        
        Args:
            topic: 报告主题
            report_type: 报告类型（如 travel_guide, data_collection 等）
            report_data: 准备好的报告数据
            data: 原始节点输出数据
            language: 语言 (zh/en)
            report_style: 报告风格
            
        Returns:
            生成的报告结果字典
        """
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        import os
        
        logger.info(f"使用 LLM 生成通用报告: topic={topic}, type={report_type}")
        
        try:
            # 初始化 LLM
            llm = ChatOpenAI(
                model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
                openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
                openai_api_key=os.environ.get("OPENAI_API_KEY"),
                temperature=0.7
            )
            
            # 提取数据摘要
            data_summary = self._extract_data_summary(data, report_type)
            
            # 构建报告类型特定的提示
            type_prompts = {
                "travel_guide": {
                    "zh": "旅游攻略报告",
                    "en": "Travel Guide Report"
                },
                "data_collection": {
                    "zh": "数据收集报告",
                    "en": "Data Collection Report"
                }
            }
            
            type_name = type_prompts.get(report_type, {}).get(language, report_type)
            
            if language == "zh":
                prompt = f"""请基于以下数据生成一份专业的{type_name}。

# 报告主题
{topic}

# 收集的数据摘要
{data_summary}

# 报告要求
1. 结构清晰，包含标题、摘要、正文、建议等部分
2. 内容专业、实用，具有参考价值
3. 使用 Markdown 格式
4. 突出关键信息和重点建议
5. 报告风格：{report_style}

请生成完整的报告内容："""
            else:
                prompt = f"""Please generate a professional {type_name} based on the following data.

# Topic
{topic}

# Data Summary
{data_summary}

# Requirements
1. Clear structure with title, summary, body, and recommendations
2. Professional and practical content
3. Use Markdown format
4. Highlight key information and recommendations
5. Report style: {report_style}

Please generate the full report:"""
            
            # 调用 LLM 生成报告
            response = llm.invoke([HumanMessage(content=prompt)])
            report_content = response.content.strip()
            
            # 确保报告内容非空
            if not report_content or len(report_content.strip()) < 50:
                logger.warning(f"LLM 生成的报告内容过短，使用兜底模板")
                report_content = self._build_fallback_report_content(
                    report_type=report_type,
                    report_data=report_data,
                    error_message="LLM 生成的报告内容不足"
                )
            
            logger.info(f"LLM 通用报告生成成功，报告长度: {len(report_content)}")
            
            return {
                "report_type": f"llm_{report_type}",
                "content": report_content,
                "extra_data": {
                    "generation_method": "llm_generic",
                    "language": language,
                    "report_style": report_style,
                    "original_type": report_type
                }
            }
            
        except Exception as e:
            logger.error(f"LLM 通用报告生成失败: {e}", exc_info=True)
            # 降级到基础模板
            logger.info("降级到基础模板报告")
            return self.agent.generate_report(
                report_type=report_type,
                data=report_data
            )
    
    def _extract_data_summary(self, data: Dict[str, Any], report_type: str) -> str:
        """
        从节点输出数据中提取摘要信息，用于 LLM 提示
        
        Args:
            data: 原始节点输出数据
            report_type: 报告类型
            
        Returns:
            数据摘要字符串
        """
        import json
        
        summary_parts = []
        
        for node_id, node_output in data.items():
            if isinstance(node_output, dict):
                # 提取关键信息
                node_summary = {"node_id": node_id}
                
                # 收集数据
                if "collected_data" in node_output:
                    collected = node_output["collected_data"]
                    if isinstance(collected, list):
                        node_summary["data_count"] = len(collected)
                        if collected:
                            # 提取前几条数据的摘要
                            sample_data = collected[:3]
                            node_summary["sample_data"] = [
                                {k: v for k, v in item.items() if k in ["title", "name", "content", "summary", "description"]}
                                if isinstance(item, dict)
                                else str(item)[:200]
                                for item in sample_data
                            ]
                
                # 过滤后的数据
                if "filtered_data" in node_output:
                    filtered = node_output["filtered_data"]
                    if isinstance(filtered, list):
                        node_summary["filtered_count"] = len(filtered)
                
                # 行程规划
                if "itinerary" in node_output or "plan" in node_output:
                    node_summary["planned_content"] = node_output.get("itinerary") or node_output.get("plan")
                
                # 其他重要字段
                for key in ["topic", "status", "message", "result"]:
                    if key in node_output:
                        node_summary[key] = node_output[key]
                
                summary_parts.append(json.dumps(node_summary, ensure_ascii=False, indent=2))
        
        if not summary_parts:
            return "暂无收集到的数据"
        
        return "\n\n---\n\n".join(summary_parts)