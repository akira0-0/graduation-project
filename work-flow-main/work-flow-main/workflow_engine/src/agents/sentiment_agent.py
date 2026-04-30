"""
情感分析智能体（增强版）
使用领域知识记忆和案例模式记忆分析情感
支持多种情感分析方法：基于词典、机器学习模型、深度学习模型

增强功能：
- LLM 深度语义理解：使用 LLM 进行上下文感知的情感分析
- 多维度分析：情感强度、情感原因、情感对象
- 智能归类：自动识别主题、观点、关键信息
- 情感趋势预测：基于历史数据预测情感走向

集成数据存储服务，自动持久化分析结果
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re
import math
import os
import json
from collections import Counter
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..database import get_session, AgentMemoryService
from ..utils.logger import get_logger

logger = get_logger("sentiment_agent")


class LLMSentimentAnalyzer:
    """
    LLM 情感分析器
    使用大语言模型进行深度语义理解和情感分析
    """
    
    def __init__(self):
        """初始化 LLM"""
        self.llm = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
            openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0.3
        )
    
    def analyze_sentiment_deep(
        self,
        content: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用 LLM 进行深度情感分析
        
        Args:
            content: 待分析文本
            context: 上下文信息
            
        Returns:
            深度分析结果
        """
        context_prompt = f"\n\n上下文信息：{context}" if context else ""
        
        prompt = f"""你是一个专业的情感分析师。请对以下文本进行深度情感分析。

文本内容：
{content}
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
    "opinions": [
        {{
            "topic": "观点主题",
            "stance": "positive/negative/neutral",
            "confidence": 0.0-1.0
        }}
    ],
    "summary": "情感分析摘要（50字以内）"
}}

只返回 JSON，不要其他说明："""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            # 去除可能的 markdown 代码块标记
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("\n", 1)[0]
            
            result = json.loads(content)
            
            # 确保必要字段存在
            return {
                "sentiment": result.get("sentiment", "neutral"),
                "confidence": result.get("confidence", 0.5),
                "intensity": result.get("intensity", "moderate"),
                "intensity_score": result.get("intensity_score", 0.5),
                "emotions": result.get("emotions", {}),
                "primary_emotion": result.get("primary_emotion", "neutral"),
                "sentiment_targets": result.get("sentiment_targets", []),
                "reasons": result.get("reasons", []),
                "key_phrases": result.get("key_phrases", []),
                "opinions": result.get("opinions", []),
                "summary": result.get("summary", ""),
                "analysis_method": "llm_deep"
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"LLM 返回 JSON 解析失败: {e}")
            return self._fallback_analysis(content, "JSON解析失败")
        except Exception as e:
            logger.warning(f"LLM 深度分析失败: {e}")
            return self._fallback_analysis(content, str(e))
    
    def _fallback_analysis(self, content: str, error: str) -> Dict[str, Any]:
        """备用分析方法"""
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "intensity": "moderate",
            "intensity_score": 0.5,
            "emotions": {},
            "primary_emotion": "neutral",
            "sentiment_targets": [],
            "reasons": [],
            "key_phrases": [],
            "opinions": [],
            "summary": f"分析失败: {error}",
            "analysis_method": "fallback",
            "error": error
        }
    
    def batch_analyze(
        self,
        contents: List[str],
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        批量情感分析
        
        Args:
            contents: 文本列表
            batch_size: 批处理大小
            
        Returns:
            分析结果列表
        """
        results = []
        for content in contents:
            result = self.analyze_sentiment_deep(content)
            results.append(result)
        return results
    
    def analyze_sentiment_trend(
        self,
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析情感趋势
        
        Args:
            historical_data: 历史分析数据
            
        Returns:
            趋势分析结果
        """
        if len(historical_data) < 3:
            return {"trend": "insufficient_data", "prediction": None}
        
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

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("\n", 1)[0]
            
            result = json.loads(content)
            return {
                "trend": result.get("trend", "stable"),
                "trend_confidence": result.get("trend_confidence", 0.5),
                "prediction": result.get("prediction", ""),
                "key_factors": result.get("key_factors", []),
                "recommendation": result.get("recommendation", "")
            }
        except Exception as e:
            logger.warning(f"趋势分析失败: {e}")
            return {"trend": "stable", "error": str(e)}
    
    def extract_key_insights(
        self,
        analyzed_data: List[Dict[str, Any]],
        topic: str
    ) -> Dict[str, Any]:
        """
        提取关键洞察
        
        Args:
            analyzed_data: 已分析的数据
            topic: 分析主题
            
        Returns:
            关键洞察
        """
        # 汇总关键信息
        all_key_phrases = []
        all_reasons = []
        all_opinions = []
        
        for item in analyzed_data:
            if "deep_analysis" in item:
                analysis = item["deep_analysis"]
                all_key_phrases.extend(analysis.get("key_phrases", []))
                all_reasons.extend(analysis.get("reasons", []))
                all_opinions.extend(analysis.get("opinions", []))
        
        # 统计高频词
        phrase_freq = Counter(all_key_phrases).most_common(10)
        reason_freq = Counter(all_reasons).most_common(5)
        
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

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("\n", 1)[0]
            
            result = json.loads(content)
            return {
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
            logger.warning(f"洞察提取失败: {e}")
            return {
                "main_themes": [],
                "pain_points": [],
                "highlights": [],
                "sentiment_drivers": [],
                "actionable_insights": [],
                "summary": f"洞察提取失败: {e}",
                "error": str(e)
            }


class SentimentAnalysisAgent:
    """
    情感分析智能体（增强版）
    
    增强功能：
    - LLM 深度语义理解：使用 LLM 进行上下文感知的情感分析
    - 多维度分析：情感强度、情感原因、情感对象、情绪细分
    - 智能归类：自动识别主题、观点、关键信息
    - 情感趋势预测：基于历史数据预测情感走向
    - 关键洞察提取：自动提取关键洞察和可操作建议
    
    支持领域知识记忆和案例模式记忆
    集成数据存储服务，自动持久化分析结果
    """
    
    def __init__(self, workflow_id: str, auto_save: bool = True, use_llm: bool = True):
        """
        初始化智能体
        
        Args:
            workflow_id: 工作流 ID
            auto_save: 是否自动保存分析结果到数据库（默认True）
            use_llm: 是否使用 LLM 进行深度分析（默认True）
        """
        self.workflow_id = workflow_id
        self.db = get_session()
        self.memory_service = AgentMemoryService(self.db)
        # 延迟导入避免循环依赖
        from ..services.data_storage_service import DataStorageService
        self.storage_service = DataStorageService(workflow_id)
        self.auto_save = auto_save
        self.use_llm = use_llm
        
        # 初始化 LLM 分析器
        if use_llm:
            try:
                self.llm_analyzer = LLMSentimentAnalyzer()
                logger.info("LLM 深度分析功能已启用")
            except Exception as e:
                logger.warning(f"LLM 分析器初始化失败: {e}，将使用基础分析模式")
                self.use_llm = False
                self.llm_analyzer = None
        else:
            self.llm_analyzer = None
        
        # 初始化领域知识和案例模式
        self._initialize_memories()
    
    def _initialize_memories(self):
        """初始化默认的领域知识和案例模式"""
        # 加载领域知识
        domain_knowledge = self.memory_service.get_domain_knowledge(
            self.workflow_id,
            "sentiment_analysis"
        )
        
        # 如果没有领域知识，创建默认的
        if not domain_knowledge:
            self._create_default_domain_knowledge()
        
        # 加载案例模式
        case_patterns = self.memory_service.get_case_patterns(
            self.workflow_id,
            "sentiment_analysis"
        )
        
        # 如果没有案例模式，创建默认的
        if not case_patterns:
            self._create_default_case_patterns()
    
    def _create_default_domain_knowledge(self):
        """创建默认的领域知识"""
        default_knowledge = {
            "positive_keywords": [
                "amazing", "excellent", "love", "best", "great",
                "wonderful", "fantastic", "awesome", "完美", "优秀",
                "喜欢", "棒", "好", "优秀", "出色"
            ],
            "negative_keywords": [
                "terrible", "bad", "hate", "worst", "awful",
                "disappointing", "poor", "terrible", "糟糕", "差",
                "讨厌", "最差", "不好", "失望"
            ],
            "neutral_keywords": [
                "okay", "average", "normal", "acceptable", "还行",
                "一般", "普通", "可以", "还行"
            ],
            "sentiment_weights": {
                "positive": 1.0,
                "negative": -1.0,
                "neutral": 0.0
            }
        }
        
        for key, value in default_knowledge.items():
            self.memory_service.save_memory(
                workflow_id=self.workflow_id,
                agent_type="sentiment_analysis",
                memory_type="domain_knowledge",
                key=key,
                value=value,
                extra_data={"category": "default_knowledge"}
            )
        
        logger.info("创建默认领域知识")
    
    def _create_default_case_patterns(self):
        """创建默认的案例模式"""
        default_patterns = [
            {
                "pattern": "强烈正面情感",
                "features": {
                    "contains_emphasis": True,
                    "contains_exclamation": True,
                    "sentiment_score": 2.0
                },
                "examples": [
                    "Best product ever!!!",
                    "I absolutely love this!",
                    "太棒了！！！"
                ]
            },
            {
                "pattern": "温和正面情感",
                "features": {
                    "contains_emphasis": False,
                    "sentiment_score": 1.0
                },
                "examples": [
                    "Pretty good product",
                    "I like it",
                    "挺好的"
                ]
            },
            {
                "pattern": "强烈负面情感",
                "features": {
                    "contains_emphasis": True,
                    "contains_exclamation": True,
                    "sentiment_score": -2.0
                },
                "examples": [
                    "Terrible experience!!!",
                    "I hate this so much!",
                    "太糟糕了！！！"
                ]
            },
            {
                "pattern": "温和负面情感",
                "features": {
                    "contains_emphasis": False,
                    "sentiment_score": -1.0
                },
                "examples": [
                    "Not as good as expected",
                    "Could be better",
                    "可以更好"
                ]
            }
        ]
        
        for i, pattern in enumerate(default_patterns):
            self.memory_service.save_memory(
                workflow_id=self.workflow_id,
                agent_type="sentiment_analysis",
                memory_type="case_pattern",
                key=f"pattern_{i}",
                value=pattern,
                extra_data={"category": "default_pattern"}
            )
        
        logger.info("创建默认案例模式")
    
    def analyze_sentiment(
        self,
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析评论的情感
        
        Args:
            data: 待分析的数据列表，每项包含 'content' 字段
            
        Returns:
            分析结果，包含每条数据的情感标签和总体统计
        """
        logger.info(f"开始情感分析，共 {len(data)} 条数据")
        
        # 获取领域知识
        domain_knowledge = self.memory_service.get_domain_knowledge(
            self.workflow_id,
            "sentiment_analysis"
        )
        
        # 获取案例模式
        case_patterns = self.memory_service.get_case_patterns(
            self.workflow_id,
            "sentiment_analysis"
        )
        
        # 分析每条数据
        analyzed_data = []
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        for item in data:
            content = item.get("content", "")
            sentiment_info = self._analyze_single_comment(
                content,
                domain_knowledge,
                case_patterns
            )
            
            analyzed_item = item.copy()
            analyzed_item.update(sentiment_info)
            analyzed_data.append(analyzed_item)
            
            # 统计情感
            sentiment = sentiment_info.get("sentiment", "neutral")
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
        
        # 计算总体统计
        total = len(analyzed_data)
        sentiment_distribution = {
            "positive": sentiment_counts["positive"] / total if total > 0 else 0,
            "negative": sentiment_counts["negative"] / total if total > 0 else 0,
            "neutral": sentiment_counts["neutral"] / total if total > 0 else 0
        }
        
        # 识别情感趋势
        trend = self._identify_sentiment_trend(analyzed_data)
        
        result = {
            "analyzed_data": analyzed_data,
            "summary": {
                "total_analyzed": total,
                "sentiment_counts": sentiment_counts,
                "sentiment_distribution": sentiment_distribution,
                "dominant_sentiment": max(
                    sentiment_counts.items(),
                    key=lambda x: x[1]
                )[0] if total > 0 else "neutral"
            },
            "trend": trend,
            "extra_data": {
                "workflow_id": self.workflow_id,
                "analyzed_at": datetime.utcnow().isoformat(),
                "domain_knowledge_used": list(domain_knowledge.keys()),
                "case_patterns_used": len(case_patterns)
            }
        }
        
        # 保存分析结果到记忆
        self._save_analysis_result(result)
        
        # 自动保存分析结果到数据库
        if self.auto_save:
            self._save_to_database(result)
        
        logger.info(f"情感分析完成，正面: {sentiment_counts['positive']}, "
                   f"负面: {sentiment_counts['negative']}, "
                   f"中性: {sentiment_counts['neutral']}")
        
        return result
    
    def analyze_sentiment_deep(
        self,
        data: List[Dict[str, Any]],
        topic: Optional[str] = None,
        extract_insights: bool = True
    ) -> Dict[str, Any]:
        """
        深度情感分析（增强版）
        
        使用 LLM 进行：
        - 深度语义理解
        - 多维度情感分析（情感强度、情感原因、情感对象）
        - 情绪细分（喜悦、悲伤、愤怒、恐惧、惊讶、厌恶）
        - 观点提取和主题识别
        - 关键洞察提取
        
        Args:
            data: 待分析的数据列表
            topic: 分析主题（可选，用于洞察提取）
            extract_insights: 是否提取关键洞察
            
        Returns:
            深度分析结果
        """
        logger.info(f"开始深度情感分析，共 {len(data)} 条数据，LLM增强: {self.use_llm}")
        
        # 首先执行基础分析
        base_result = self.analyze_sentiment(data)
        analyzed_data = base_result["analyzed_data"]
        
        # 如果启用 LLM，执行深度分析
        if self.use_llm and self.llm_analyzer:
            logger.info("执行 LLM 深度语义分析...")
            
            for idx, item in enumerate(analyzed_data):
                content = item.get("content", "")
                if content:
                    try:
                        # 执行深度分析
                        deep_analysis = self.llm_analyzer.analyze_sentiment_deep(
                            content,
                            context=topic
                        )
                        
                        # 合并深度分析结果
                        item["deep_analysis"] = deep_analysis
                        
                        # 如果 LLM 分析成功，更新主要情感标签
                        if deep_analysis.get("analysis_method") == "llm_deep":
                            item["sentiment_llm"] = deep_analysis.get("sentiment")
                            item["confidence"] = deep_analysis.get("confidence", 0.5)
                            item["intensity"] = deep_analysis.get("intensity", "moderate")
                            item["primary_emotion"] = deep_analysis.get("primary_emotion")
                            item["emotions"] = deep_analysis.get("emotions", {})
                            item["sentiment_targets"] = deep_analysis.get("sentiment_targets", [])
                            item["reasons"] = deep_analysis.get("reasons", [])
                            item["key_phrases"] = deep_analysis.get("key_phrases", [])
                            item["opinions"] = deep_analysis.get("opinions", [])
                        
                        # 每处理5条数据打印进度
                        if (idx + 1) % 5 == 0:
                            logger.info(f"已分析 {idx + 1}/{len(analyzed_data)} 条数据")
                            
                    except Exception as e:
                        logger.warning(f"第 {idx + 1} 条数据深度分析失败: {e}")
                        item["deep_analysis_error"] = str(e)
            
            # 提取关键洞察
            if extract_insights:
                logger.info("提取关键洞察...")
                try:
                    insights = self.llm_analyzer.extract_key_insights(analyzed_data, topic or "数据分析")
                    base_result["insights"] = insights
                except Exception as e:
                    logger.warning(f"洞察提取失败: {e}")
                    base_result["insights"] = {"error": str(e)}
            
            # 预测情感趋势
            if len(analyzed_data) >= 5:
                logger.info("预测情感趋势...")
                try:
                    trend_prediction = self.llm_analyzer.analyze_sentiment_trend(analyzed_data)
                    base_result["trend_prediction"] = trend_prediction
                except Exception as e:
                    logger.warning(f"趋势预测失败: {e}")
        
        # 计算增强统计
        if self.use_llm and analyzed_data and "deep_analysis" in analyzed_data[0]:
            # 情感强度统计
            intensity_counts = {"strong": 0, "moderate": 0, "weak": 0}
            emotion_totals = {}
            all_targets = []
            all_reasons = []
            
            for item in analyzed_data:
                if "deep_analysis" in item:
                    deep = item["deep_analysis"]
                    intensity_counts[deep.get("intensity", "moderate")] += 1
                    
                    for emotion, score in deep.get("emotions", {}).items():
                        emotion_totals[emotion] = emotion_totals.get(emotion, 0) + score
                    
                    all_targets.extend(deep.get("sentiment_targets", []))
                    all_reasons.extend(deep.get("reasons", []))
            
            # 计算平均情感得分
            avg_emotions = {k: v / len(analyzed_data) for k, v in emotion_totals.items()}
            
            # 情感对象频率
            target_freq = Counter(all_targets).most_common(10)
            reason_freq = Counter(all_reasons).most_common(10)
            
            base_result["deep_summary"] = {
                "intensity_distribution": intensity_counts,
                "average_emotions": avg_emotions,
                "top_sentiment_targets": target_freq,
                "top_reasons": reason_freq,
                "llm_analysis_enabled": True
            }
        
        base_result["analysis_method"] = "deep" if self.use_llm else "basic"
        
        # 保存分析结果
        if self.auto_save:
            self._save_to_database(base_result)
        
        logger.info(f"深度情感分析完成，方法: {base_result['analysis_method']}")
        return base_result
    
    def analyze_sentiment_with_llm(
        self,
        data: List[Dict[str, Any]],
        topic: Optional[str] = None,
        use_deep_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        使用 LLM 进行情感分析（便捷方法）
        
        Args:
            data: 待分析的数据列表
            topic: 分析主题
            use_deep_analysis: 是否使用深度分析
            
        Returns:
            分析结果
        """
        if use_deep_analysis:
            return self.analyze_sentiment_deep(data, topic, extract_insights=True)
        else:
            return self.analyze_sentiment(data)
    
    def _save_to_database(self, result: Dict[str, Any]):
        """
        保存分析结果到数据库
        
        Args:
            result: 分析结果
        """
        try:
            # 保存分析结果
            self.storage_service.store_analysis_result(
                result=result,
                analysis_type="sentiment",
                agent_type="sentiment_analysis",
                workflow_id=self.workflow_id
            )
            logger.info("情感分析结果已保存到数据库")
        except Exception as e:
            logger.error(f"保存情感分析结果失败: {e}")
    
    def _analyze_single_comment(
        self,
        content: str,
        domain_knowledge: Dict[str, Any],
        case_patterns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析单条评论的情感
        
        Args:
            content: 评论内容
            domain_knowledge: 领域知识
            case_patterns: 案例模式
            
        Returns:
            情感分析结果
        """
        content_lower = content.lower()
        
        # 提取特征
        features = self._extract_features(content)
        
        # 使用领域知识进行初步判断
        positive_keywords = domain_knowledge.get("positive_keywords", [])
        negative_keywords = domain_knowledge.get("negative_keywords", [])
        neutral_keywords = domain_knowledge.get("neutral_keywords", [])
        
        score = 0
        matched_keywords = []
        
        for keyword in positive_keywords:
            if keyword.lower() in content_lower:
                score += 1
                matched_keywords.append((keyword, "positive"))
        
        for keyword in negative_keywords:
            if keyword.lower() in content_lower:
                score -= 1
                matched_keywords.append((keyword, "negative"))
        
        for keyword in neutral_keywords:
            if keyword.lower() in content_lower:
                matched_keywords.append((keyword, "neutral"))
        
        # 匹配案例模式
        matched_pattern = self._match_case_pattern(features, case_patterns)
        
        # 综合判断情感
        if matched_pattern:
            # 如果匹配到案例模式，使用模式的情感
            pattern_score = matched_pattern["features"]["sentiment_score"]
            if abs(pattern_score) > abs(score):
                sentiment = "positive" if pattern_score > 0 else "negative"
            else:
                sentiment = self._determine_sentiment_from_score(score)
        else:
            sentiment = self._determine_sentiment_from_score(score)
        
        return {
            "sentiment": sentiment,
            "sentiment_score": score,
            "matched_keywords": matched_keywords,
            "matched_pattern": matched_pattern["pattern"] if matched_pattern else None,
            "features": features
        }
    
    def _extract_features(self, content: str) -> Dict[str, Any]:
        """
        提取文本特征
        
        Args:
            content: 文本内容
            
        Returns:
            特征字典
        """
        return {
            "length": len(content),
            "contains_emphasis": any(word.isupper() for word in content.split()),
            "contains_exclamation": "!" in content or "！" in content,
            "contains_question": "?" in content or "？" in content,
            "word_count": len(content.split())
        }
    
    def _match_case_pattern(
        self,
        features: Dict[str, Any],
        case_patterns: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        匹配案例模式
        
        Args:
            features: 文本特征
            case_patterns: 案例模式列表
            
        Returns:
            匹配的模式或 None
        """
        for pattern in case_patterns:
            pattern_features = pattern["features"]
            match_score = 0
            
            # 检查特征匹配
            if pattern_features.get("contains_emphasis") == features["contains_emphasis"]:
                match_score += 1
            
            if pattern_features.get("contains_exclamation") == features["contains_exclamation"]:
                match_score += 1
            
            # 如果匹配度足够高，返回该模式
            if match_score >= 1:
                return pattern
        
        return None
    
    def _determine_sentiment_from_score(self, score: int) -> str:
        """
        根据分数确定情感标签
        
        Args:
            score: 情感分数
            
        Returns:
            情感标签
        """
        if score > 0:
            return "positive"
        elif score < 0:
            return "negative"
        else:
            return "neutral"
    
    def _identify_sentiment_trend(
        self,
        analyzed_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        识别情感趋势
        
        Args:
            analyzed_data: 已分析的数据
            
        Returns:
            趋势分析结果
        """
        if len(analyzed_data) < 2:
            return {"trend": "insufficient_data"}
        
        # 按时间排序（如果有时间戳）
        sorted_data = sorted(
            analyzed_data,
            key=lambda x: x.get("timestamp", "")
        )
        
        # 计算前半部分和后半部分的情感分布
        mid = len(sorted_data) // 2
        first_half = sorted_data[:mid]
        second_half = sorted_data[mid:]
        
        first_positive = sum(1 for x in first_half if x.get("sentiment") == "positive")
        second_positive = sum(1 for x in second_half if x.get("sentiment") == "positive")
        
        first_negative = sum(1 for x in first_half if x.get("sentiment") == "negative")
        second_negative = sum(1 for x in second_half if x.get("sentiment") == "negative")
        
        # 判断趋势
        trend = "stable"
        if second_positive > first_positive * 1.2:
            trend = "improving"
        elif second_negative > first_negative * 1.2:
            trend = "declining"
        
        return {
            "trend": trend,
            "first_half": {
                "positive": first_positive,
                "negative": first_negative,
                "total": len(first_half)
            },
            "second_half": {
                "positive": second_positive,
                "negative": second_negative,
                "total": len(second_half)
            }
        }
    
    def _save_analysis_result(self, result: Dict[str, Any]):
        """
        保存分析结果到记忆
        
        Args:
            result: 分析结果
        """
        self.memory_service.save_memory(
            workflow_id=self.workflow_id,
            agent_type="sentiment_analysis",
            memory_type="domain_knowledge",
            key=f"analysis_result_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            value=result,
            extra_data={"category": "analysis_result"}
        )
    
    def learn_from_case(
        self,
        case_data: Dict[str, Any]
    ):
        """
        从案例中学习
        
        Args:
            case_data: 案例数据，包含 content 和 expected_sentiment
        """
        content = case_data.get("content", "")
        expected_sentiment = case_data.get("expected_sentiment")
        
        # 提取特征
        features = self._extract_features(content)
        
        # 创建新的案例模式
        new_pattern = {
            "pattern": f"用户反馈模式 - {expected_sentiment}",
            "features": features,
            "examples": [content]
        }
        
        # 保存到记忆
        self.memory_service.save_memory(
            workflow_id=self.workflow_id,
            agent_type="sentiment_analysis",
            memory_type="case_pattern",
            key=f"user_pattern_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            value=new_pattern,
            extra_data={"source": "user_feedback"}
        )
        
        logger.info(f"从用户反馈学习新模式: {expected_sentiment}")
    
    def get_stored_results(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取已存储的分析结果
        
        Args:
            limit: 返回的最大数量
            
        Returns:
            分析结果列表
        """
        return self.storage_service.get_analysis_results(
            workflow_id=self.workflow_id,
            analysis_type="sentiment"
        )[:limit]
    
    def _analyze_with_textblob(self, content: str) -> Dict[str, Any]:
        """
        使用 TextBlob 进行情感分析（英文）
        
        Args:
            content: 文本内容
            
        Returns:
            情感分析结果
        """
        try:
            from textblob import TextBlob
            
            blob = TextBlob(content)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # 转换为情感标签
            if polarity > 0.1:
                sentiment = "positive"
            elif polarity < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            return {
                "sentiment": sentiment,
                "polarity": polarity,
                "subjectivity": subjectivity,
                "method": "textblob"
            }
            
        except ImportError:
            logger.warning("textblob 库未安装，跳过 TextBlob 分析")
            return {}
        except Exception as e:
            logger.warning(f"TextBlob 分析失败: {e}")
            return {}
    
    def _analyze_with_jieba_sentiment(self, content: str) -> Dict[str, Any]:
        """
        使用 jieba + 情感词典进行中文情感分析
        
        Args:
            content: 文本内容
            
        Returns:
            情感分析结果
        """
        try:
            import jieba
            import jieba.analyse
            
            # 分词
            words = jieba.cut(content)
            words_list = list(words)
            
            # 获取领域知识中的情感词
            domain_knowledge = self.memory_service.get_domain_knowledge(
                self.workflow_id,
                "sentiment_analysis"
            )
            
            positive_words = set(domain_knowledge.get("positive_keywords", []))
            negative_words = set(domain_knowledge.get("negative_keywords", []))
            
            # 计算情感分数
            positive_count = sum(1 for word in words_list if word in positive_words)
            negative_count = sum(1 for word in words_list if word in negative_words)
            
            total_words = len(words_list)
            if total_words == 0:
                return {
                    "sentiment": "neutral",
                    "positive_ratio": 0,
                    "negative_ratio": 0,
                    "method": "jieba"
                }
            
            positive_ratio = positive_count / total_words
            negative_ratio = negative_count / total_words
            
            # 判断情感
            if positive_ratio > negative_ratio + 0.05:
                sentiment = "positive"
                score = positive_ratio
            elif negative_ratio > positive_ratio + 0.05:
                sentiment = "negative"
                score = -negative_ratio
            else:
                sentiment = "neutral"
                score = 0
            
            return {
                "sentiment": sentiment,
                "score": score,
                "positive_ratio": positive_ratio,
                "negative_ratio": negative_ratio,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "method": "jieba"
            }
            
        except ImportError:
            logger.warning("jieba 库未安装，跳过 jieba 分析")
            return {}
        except Exception as e:
            logger.warning(f"jieba 分析失败: {e}")
            return {}
    
    def _analyze_with_transformer(self, content: str) -> Dict[str, Any]:
        """
        使用 Transformer 模型进行情感分析
        
        Args:
            content: 文本内容
            
        Returns:
            情感分析结果
        """
        try:
            from transformers import pipeline
            
            # 使用多语言情感分析模型
            classifier = pipeline(
                "sentiment-analysis",
                model="nlptown/bert-base-multilingual-uncased-sentiment",
                device=-1  # 使用 CPU
            )
            
            result = classifier(content[:512])  # BERT 模型限制长度
            
            # 解析结果
            label = result[0]["label"]
            score = result[0]["score"]
            
            # 转换标签（模型输出为 1-5 星级）
            if label in ["4 stars", "5 stars"]:
                sentiment = "positive"
            elif label in ["1 star", "2 stars"]:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            return {
                "sentiment": sentiment,
                "confidence": score,
                "raw_label": label,
                "method": "transformer"
            }
            
        except ImportError:
            logger.warning("transformers 库未安装，跳过 Transformer 分析")
            return {}
        except Exception as e:
            logger.warning(f"Transformer 分析失败: {e}")
            return {}
    
    def _ensemble_sentiment_analysis(
        self,
        content: str,
        methods: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        集成多种情感分析方法
        
        Args:
            content: 文本内容
            methods: 使用的分析方法列表
            
        Returns:
            集成分析结果
        """
        if methods is None:
            methods = ["lexicon", "textblob", "jieba"]
        
        results = {}
        sentiment_votes = []
        
        # 1. 基于词典的分析（始终执行）
        domain_knowledge = self.memory_service.get_domain_knowledge(
            self.workflow_id,
            "sentiment_analysis"
        )
        case_patterns = self.memory_service.get_case_patterns(
            self.workflow_id,
            "sentiment_analysis"
        )
        lexicon_result = self._analyze_single_comment(content, domain_knowledge, case_patterns)
        results["lexicon"] = lexicon_result
        sentiment_votes.append(lexicon_result["sentiment"])
        
        # 2. TextBlob 分析（英文）
        if "textblob" in methods:
            textblob_result = self._analyze_with_textblob(content)
            if textblob_result:
                results["textblob"] = textblob_result
                sentiment_votes.append(textblob_result["sentiment"])
        
        # 3. jieba 分析（中文）
        if "jieba" in methods:
            jieba_result = self._analyze_with_jieba_sentiment(content)
            if jieba_result:
                results["jieba"] = jieba_result
                sentiment_votes.append(jieba_result["sentiment"])
        
        # 4. Transformer 分析（可选，需要大量计算资源）
        if "transformer" in methods:
            transformer_result = self._analyze_with_transformer(content)
            if transformer_result:
                results["transformer"] = transformer_result
                sentiment_votes.append(transformer_result["sentiment"])
        
        # 投票决定最终情感
        sentiment_counter = Counter(sentiment_votes)
        final_sentiment = sentiment_counter.most_common(1)[0][0]
        
        # 计算置信度
        confidence = sentiment_counter[final_sentiment] / len(sentiment_votes)
        
        return {
            "sentiment": final_sentiment,
            "confidence": confidence,
            "method_results": results,
            "method_count": len(sentiment_votes),
            "agreement": sentiment_counter.most_common()
        }
    
    def analyze_sentiment_advanced(
        self,
        data: List[Dict[str, Any]],
        use_ensemble: bool = False,
        methods: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        高级情感分析（支持集成方法）
        
        Args:
            data: 待分析的数据列表
            use_ensemble: 是否使用集成方法
            methods: 使用的分析方法列表
            
        Returns:
            分析结果
        """
        logger.info(f"开始高级情感分析，共 {len(data)} 条数据，集成方法: {use_ensemble}")
        
        analyzed_data = []
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        for idx, item in enumerate(data):
            content = item.get("content", "")
            
            if not content:
                logger.warning(f"第 {idx + 1} 条数据没有内容，跳过")
                continue
            
            # 选择分析方法
            if use_ensemble:
                analysis_result = self._ensemble_sentiment_analysis(content, methods)
            else:
                # 获取领域知识和案例模式
                domain_knowledge = self.memory_service.get_domain_knowledge(
                    self.workflow_id,
                    "sentiment_analysis"
                )
                case_patterns = self.memory_service.get_case_patterns(
                    self.workflow_id,
                    "sentiment_analysis"
                )
                analysis_result = self._analyze_single_comment(content, domain_knowledge, case_patterns)
            
            analyzed_item = item.copy()
            analyzed_item.update(analysis_result)
            analyzed_data.append(analyzed_item)
            
            # 统计情感
            sentiment = analysis_result.get("sentiment", "neutral")
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
        
        # 计算总体统计
        total = len(analyzed_data)
        sentiment_distribution = {
            "positive": sentiment_counts["positive"] / total if total > 0 else 0,
            "negative": sentiment_counts["negative"] / total if total > 0 else 0,
            "neutral": sentiment_counts["neutral"] / total if total > 0 else 0
        }
        
        # 识别情感趋势
        trend = self._identify_sentiment_trend(analyzed_data)
        
        result = {
            "analyzed_data": analyzed_data,
            "summary": {
                "total_analyzed": total,
                "sentiment_counts": sentiment_counts,
                "sentiment_distribution": sentiment_distribution,
                "dominant_sentiment": max(
                    sentiment_counts.items(),
                    key=lambda x: x[1]
                )[0] if total > 0 else "neutral"
            },
            "trend": trend,
            "analysis_config": {
                "use_ensemble": use_ensemble,
                "methods": methods if use_ensemble else ["lexicon"]
            },
            "extra_data": {
                "workflow_id": self.workflow_id,
                "analyzed_at": datetime.utcnow().isoformat()
            }
        }
        
        logger.info(f"高级情感分析完成，正面: {sentiment_counts['positive']}, "
                   f"负面: {sentiment_counts['negative']}, "
                   f"中性: {sentiment_counts['neutral']}")
        
        return result
    
    def detect_emotion(self, content: str) -> Dict[str, Any]:
        """
        情感检测（更细粒度的情感分析）
        
        Args:
            content: 文本内容
            
        Returns:
            情感检测结果
        """
        # 扩展的情感词典
        emotion_keywords = {
            "joy": ["开心", "高兴", "快乐", "幸福", "joy", "happy", "excited", "wonderful", "棒", "好"],
            "sadness": ["伤心", "难过", "悲伤", "失望", "sad", "depressed", "disappointed", "不好", "差"],
            "anger": ["生气", "愤怒", "火大", "恼火", "angry", "mad", "frustrated", "烦"],
            "fear": ["害怕", "担心", "恐惧", "忧虑", "afraid", "scared", "worried", "怕"],
            "surprise": ["惊讶", "意外", "震惊", "吃惊", "surprised", "amazing", "wow"],
            "disgust": ["厌恶", "讨厌", "恶心", "反感", "disgusting", "hate"]
        }
        
        content_lower = content.lower()
        emotion_scores = {}
        
        for emotion, keywords in emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                emotion_scores[emotion] = score
        
        # 归一化
        total_score = sum(emotion_scores.values())
        if total_score > 0:
            emotion_scores = {
                emotion: score / total_score
                for emotion, score in emotion_scores.items()
            }
        
        # 找出主要情感
        primary_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0] if emotion_scores else "neutral"
        
        return {
            "primary_emotion": primary_emotion,
            "emotion_scores": emotion_scores,
            "emotion_intensity": max(emotion_scores.values()) if emotion_scores else 0
        }
    
    def extract_aspects(self, content: str) -> List[Dict[str, Any]]:
        """
        方面级情感分析（Aspect-Based Sentiment Analysis）
        提取文本中的方面及其情感
        
        Args:
            content: 文本内容
            
        Returns:
            方面列表及其情感
        """
        try:
            import jieba
            import jieba.posseg as pseg
            
            # 分词和词性标注
            words = pseg.cut(content)
            
            # 提取名词和形容词
            nouns = [word.word for word in words if word.flag.startswith('n')]
            adjectives = [word.word for word in words if word.flag.startswith('a')]
            
            # 简单的方面-情感配对
            aspects = []
            domain_knowledge = self.memory_service.get_domain_knowledge(
                self.workflow_id,
                "sentiment_analysis"
            )
            
            positive_keywords = set(domain_knowledge.get("positive_keywords", []))
            negative_keywords = set(domain_knowledge.get("negative_keywords", []))
            
            for noun in nouns:
                # 查找附近的形容词
                aspect_sentiment = "neutral"
                for adj in adjectives:
                    if adj in positive_keywords:
                        aspect_sentiment = "positive"
                        break
                    elif adj in negative_keywords:
                        aspect_sentiment = "negative"
                        break
                
                aspects.append({
                    "aspect": noun,
                    "sentiment": aspect_sentiment,
                    "adjectives": [adj for adj in adjectives if adj in positive_keywords or adj in negative_keywords]
                })
            
            return aspects[:5]  # 限制返回数量
            
        except ImportError:
            logger.warning("jieba 库未安装，跳过方面级分析")
            return []
        except Exception as e:
            logger.warning(f"方面级分析失败: {e}")
            return []
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()