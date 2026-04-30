"""
情感分析智能体工具集
为 ReAct Agent 提供可调用的工具函数

工具列表：
- analyze_text_sentiment: 单条文本情感分析
- batch_analyze_sentiment: 批量情感分析
- extract_insights: 关键洞察提取
- predict_trend: 情感趋势预测
- query_domain_knowledge: 查询领域知识
- update_memory: 更新智能体记忆
"""
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from ..utils.logger import get_logger

logger = get_logger("sentiment_tools")


@tool
def analyze_text_sentiment(
    text: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    分析单条文本的情感倾向。
    
    使用 LLM 进行深度语义理解，返回情感标签、置信度、情感强度、
    情绪细分、关键短语等信息。
    
    Args:
        text: 待分析的文本内容
        context: 可选的上下文信息，有助于更准确分析
    
    Returns:
        包含以下字段的字典：
        - sentiment: 情感标签 (positive/negative/neutral)
        - confidence: 置信度 (0.0-1.0)
        - intensity: 情感强度 (strong/moderate/weak)
        - emotions: 情绪细分分布
        - key_phrases: 关键短语列表
        - summary: 分析摘要
    """
    import os
    import json
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    
    logger.info(f"分析文本情感: {text[:50]}...")
    
    try:
        llm = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
            openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0.3
        )
        
        context_prompt = f"\n\n上下文信息：{context}" if context else ""
        
        prompt = f"""你是一个专业的情感分析师。请对以下文本进行深度情感分析。

文本内容：
{text}
{context_prompt}

请以 JSON 格式返回分析结果，包含以下字段：
{{
    "sentiment": "positive/negative/neutral",
    "confidence": 0.0-1.0,
    "intensity": "strong/moderate/weak",
    "intensity_score": 0.0-1.0,
    "emotions": {{
        "joy": 0.0-1.0,
        "sadness": 0.0-1.0,
        "anger": 0.0-1.0,
        "fear": 0.0-1.0,
        "surprise": 0.0-1.0,
        "disgust": 0.0-1.0
    }},
    "primary_emotion": "主要情感",
    "sentiment_targets": ["情感指向的对象"],
    "reasons": ["产生该情感的原因"],
    "key_phrases": ["关键短语"],
    "summary": "情感分析摘要（50字以内）"
}}

只返回 JSON，不要其他说明："""

        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # 处理可能的 markdown 代码块
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.rsplit("\n", 1)[0]
        
        result = json.loads(content)
        
        return {
            "success": True,
            "sentiment": result.get("sentiment", "neutral"),
            "confidence": result.get("confidence", 0.5),
            "intensity": result.get("intensity", "moderate"),
            "intensity_score": result.get("intensity_score", 0.5),
            "emotions": result.get("emotions", {}),
            "primary_emotion": result.get("primary_emotion", "neutral"),
            "sentiment_targets": result.get("sentiment_targets", []),
            "reasons": result.get("reasons", []),
            "key_phrases": result.get("key_phrases", []),
            "summary": result.get("summary", ""),
            "analysis_method": "llm_tool"
        }
        
    except Exception as e:
        logger.error(f"情感分析失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "sentiment": "neutral",
            "confidence": 0.0,
            "summary": f"分析失败: {str(e)}"
        }


@tool
def batch_analyze_sentiment(
    texts: List[str],
    batch_size: int = 5
) -> Dict[str, Any]:
    """
    批量分析多条文本的情感倾向。
    
    对文本列表进行情感分析，返回每条文本的分析结果和汇总统计。
    适用于处理大量评论、帖子等数据。
    
    Args:
        texts: 待分析的文本列表
        batch_size: 批处理大小，默认为 5
    
    Returns:
        包含以下字段的字典：
        - results: 每条文本的分析结果列表
        - statistics: 情感分布统计
        - total_count: 总文本数
        - success_count: 成功分析数
    """
    import os
    import json
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    
    logger.info(f"批量分析情感: {len(texts)} 条文本")
    
    try:
        llm = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
            openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0.3
        )
        
        results = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for text in texts:
            try:
                prompt = f"""分析以下文本的情感。只返回JSON格式：
{{"sentiment": "positive/negative/neutral", "confidence": 0.0-1.0, "key_phrases": []}}

文本：{text}

只返回JSON："""
                
                response = llm.invoke([HumanMessage(content=prompt)])
                content = response.content.strip()
                
                if content.startswith("```"):
                    content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content.rsplit("\n", 1)[0]
                
                result = json.loads(content)
                
                sentiment = result.get("sentiment", "neutral")
                if sentiment == "positive":
                    positive_count += 1
                elif sentiment == "negative":
                    negative_count += 1
                else:
                    neutral_count += 1
                
                results.append({
                    "text": text[:100],
                    "sentiment": sentiment,
                    "confidence": result.get("confidence", 0.5),
                    "key_phrases": result.get("key_phrases", []),
                    "success": True
                })
                
            except Exception as e:
                results.append({
                    "text": text[:100],
                    "sentiment": "neutral",
                    "confidence": 0.0,
                    "error": str(e),
                    "success": False
                })
                neutral_count += 1
        
        return {
            "success": True,
            "results": results,
            "statistics": {
                "total": len(texts),
                "positive": positive_count,
                "negative": negative_count,
                "neutral": neutral_count,
                "positive_ratio": positive_count / len(texts) if texts else 0,
                "negative_ratio": negative_count / len(texts) if texts else 0,
                "neutral_ratio": neutral_count / len(texts) if texts else 0
            },
            "total_count": len(texts),
            "success_count": sum(1 for r in results if r.get("success"))
        }
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "total_count": len(texts),
            "success_count": 0
        }


@tool
def extract_insights(
    analyzed_data: List[Dict[str, Any]],
    topic: str
) -> Dict[str, Any]:
    """
    从情感分析数据中提取关键洞察。
    
    分析情感分析结果，提取主要主题、痛点问题、亮点和可操作建议。
    
    Args:
        analyzed_data: 已分析的数据列表，每条数据应包含情感分析结果
        topic: 分析主题，用于聚焦洞察方向
    
    Returns:
        包含以下字段的字典：
        - main_themes: 主要主题列表
        - pain_points: 痛点问题列表
        - highlights: 亮点列表
        - sentiment_drivers: 情感驱动因素
        - actionable_insights: 可操作建议
        - summary: 洞察摘要
    """
    import os
    import json
    from collections import Counter
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    
    logger.info(f"提取洞察: 主题={topic}, 数据量={len(analyzed_data)}")
    
    try:
        # 汇总关键信息
        all_key_phrases = []
        all_reasons = []
        all_opinions = []
        
        for item in analyzed_data:
            # 兼容不同的数据格式
            analysis = item.get("deep_analysis", item.get("analysis", item))
            all_key_phrases.extend(analysis.get("key_phrases", []))
            all_reasons.extend(analysis.get("reasons", []))
            all_opinions.extend(analysis.get("opinions", []))
        
        # 统计高频词
        phrase_freq = Counter(all_key_phrases).most_common(10)
        reason_freq = Counter(all_reasons).most_common(5)
        
        llm = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
            openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0.3
        )
        
        prompt = f"""基于以下情感分析数据，提取关键洞察。

主题：{topic}

高频关键短语：{json.dumps(phrase_freq, ensure_ascii=False)}
高频情感原因：{json.dumps(reason_freq, ensure_ascii=False)}
观点分布：{json.dumps(all_opinions[:10], ensure_ascii=False)}

请以 JSON 格式返回洞察：
{{
    "main_themes": ["主要主题"],
    "pain_points": ["痛点问题"],
    "highlights": ["亮点"],
    "sentiment_drivers": ["情感驱动因素"],
    "actionable_insights": ["可操作的建议"],
    "summary": "整体洞察摘要"
}}

只返回 JSON："""

        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.rsplit("\n", 1)[0]
        
        result = json.loads(content)
        
        return {
            "success": True,
            "main_themes": result.get("main_themes", []),
            "pain_points": result.get("pain_points", []),
            "highlights": result.get("highlights", []),
            "sentiment_drivers": result.get("sentiment_drivers", []),
            "actionable_insights": result.get("actionable_insights", []),
            "summary": result.get("summary", ""),
            "phrase_frequency": phrase_freq,
            "reason_frequency": reason_freq
        }
        
    except Exception as e:
        logger.error(f"洞察提取失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "main_themes": [],
            "pain_points": [],
            "highlights": [],
            "sentiment_drivers": [],
            "actionable_insights": [],
            "summary": f"洞察提取失败: {str(e)}"
        }


@tool
def predict_trend(
    historical_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    基于历史数据预测情感趋势。
    
    分析历史情感数据，预测未来情感走向，给出趋势分析和建议。
    
    Args:
        historical_data: 历史分析数据列表，每条数据应包含情感分析结果
    
    Returns:
        包含以下字段的字典：
        - trend: 趋势方向 (improving/declining/stable)
        - trend_confidence: 趋势置信度 (0.0-1.0)
        - prediction: 预测描述
        - key_factors: 影响趋势的关键因素
        - recommendation: 建议措施
    """
    import os
    import json
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    
    logger.info(f"预测情感趋势: 数据量={len(historical_data)}")
    
    if len(historical_data) < 3:
        return {
            "success": False,
            "trend": "insufficient_data",
            "trend_confidence": 0.0,
            "prediction": "数据量不足，至少需要3条历史数据",
            "key_factors": [],
            "recommendation": "收集更多数据后进行分析"
        }
    
    try:
        llm = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
            openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0.3
        )
        
        prompt = f"""基于以下历史情感分析数据，预测情感趋势。

历史数据：
{json.dumps(historical_data[-10:], ensure_ascii=False, indent=2)}

请以 JSON 格式返回趋势分析：
{{
    "trend": "improving/declining/stable",
    "trend_confidence": 0.0-1.0,
    "prediction": "未来情感走向预测",
    "key_factors": ["影响趋势的关键因素"],
    "recommendation": "建议措施"
}}

只返回 JSON："""

        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.rsplit("\n", 1)[0]
        
        result = json.loads(content)
        
        return {
            "success": True,
            "trend": result.get("trend", "stable"),
            "trend_confidence": result.get("trend_confidence", 0.5),
            "prediction": result.get("prediction", ""),
            "key_factors": result.get("key_factors", []),
            "recommendation": result.get("recommendation", "")
        }
        
    except Exception as e:
        logger.error(f"趋势预测失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "trend": "stable",
            "trend_confidence": 0.0,
            "prediction": f"预测失败: {str(e)}",
            "key_factors": [],
            "recommendation": ""
        }


@tool
def query_domain_knowledge(
    query: str,
    workflow_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    查询领域知识和历史案例模式。
    
    从智能体记忆系统中检索相关的领域知识和案例模式，
    帮助做出更准确的分析决策。
    
    Args:
        query: 查询内容，如关键词或问题描述
        workflow_id: 可选的工作流 ID，用于检索特定工作流的记忆
    
    Returns:
        包含以下字段的字典：
        - domain_knowledge: 匹配的领域知识
        - case_patterns: 匹配的案例模式
        - relevant_memories: 相关记忆
    """
    from ..database import get_session, AgentMemoryService
    
    logger.info(f"查询领域知识: query={query[:50]}...")
    
    try:
        db = get_session()
        memory_service = AgentMemoryService(db)
        
        # 如果没有 workflow_id，使用默认值
        wf_id = workflow_id or "default"
        
        # 查询领域知识
        domain_knowledge = memory_service.get_domain_knowledge(
            wf_id,
            "sentiment_analysis"
        )
        
        # 查询案例模式
        case_patterns = memory_service.get_case_patterns(
            wf_id,
            "sentiment_analysis"
        )
        
        # 根据查询关键词过滤相关内容
        relevant_knowledge = []
        if domain_knowledge:
            for key, value in domain_knowledge.items():
                if query.lower() in str(key).lower() or query.lower() in str(value).lower():
                    relevant_knowledge.append({
                        "key": key,
                        "value": value
                    })
        
        db.close()
        
        return {
            "success": True,
            "domain_knowledge": domain_knowledge or {},
            "case_patterns": case_patterns or [],
            "relevant_memories": relevant_knowledge,
            "query": query
        }
        
    except Exception as e:
        logger.error(f"查询领域知识失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "domain_knowledge": {},
            "case_patterns": [],
            "relevant_memories": []
        }


@tool
def update_memory(
    key: str,
    value: Any,
    memory_type: str = "domain_knowledge",
    workflow_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    更新智能体的领域知识或案例模式记忆。
    
    将新的知识或经验存储到记忆系统中，供未来分析使用。
    
    Args:
        key: 记忆的键名，如情感关键词、模式名称等
        value: 记忆的值，可以是字符串、列表或字典
        memory_type: 记忆类型，可选 "domain_knowledge" 或 "case_patterns"
        workflow_id: 可选的工作流 ID
    
    Returns:
        包含以下字段的字典：
        - success: 是否更新成功
        - message: 操作结果描述
    """
    from ..database import get_session, AgentMemoryService
    
    logger.info(f"更新记忆: key={key}, type={memory_type}")
    
    try:
        db = get_session()
        memory_service = AgentMemoryService(db)
        
        wf_id = workflow_id or "default"
        
        memory_service.save_memory(
            workflow_id=wf_id,
            agent_type="sentiment_analysis",
            memory_type=memory_type,
            key=key,
            value=value
        )
        
        db.commit()
        db.close()
        
        return {
            "success": True,
            "message": f"成功更新记忆: {key}",
            "memory_type": memory_type,
            "key": key
        }
        
    except Exception as e:
        logger.error(f"更新记忆失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"更新记忆失败: {str(e)}"
        }


# 导出所有工具
SENTIMENT_TOOLS = [
    analyze_text_sentiment,
    batch_analyze_sentiment,
    extract_insights,
    predict_trend,
    query_domain_knowledge,
    update_memory
]