# -*- coding: utf-8 -*-
"""
相关性过滤器
根据用户查询筛选出语义相关的内容
"""
import re
import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..llm.engine import LLMEngine


class RelevanceLevel(Enum):
    """相关性级别"""
    HIGH = "high"           # 高度相关
    MEDIUM = "medium"       # 中等相关
    LOW = "low"             # 低相关
    IRRELEVANT = "irrelevant"  # 不相关


@dataclass
class RelevanceResult:
    """相关性判断结果"""
    content: str
    relevance: RelevanceLevel
    score: float  # 0-1
    reason: str = ""
    keywords_matched: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "relevance": self.relevance.value,
            "score": self.score,
            "reason": self.reason,
            "keywords_matched": self.keywords_matched,
        }


class QueryParser:
    """
    查询解析器
    从自然语言查询中提取核心意图和关键词
    """
    
    # 疑问词模式
    QUESTION_PATTERNS = [
        r'有什么(.+)',
        r'怎么(.+)',
        r'如何(.+)',
        r'哪里(.+)',
        r'什么(.+)',
        r'哪些(.+)',
        r'推荐(.+)',
        r'(.+)怎么样',
        r'(.+)好不好',
        r'(.+)值得(.+)吗',
    ]
    
    # 意图映射
    INTENT_KEYWORDS = {
        "旅游": ["好玩", "景点", "旅游", "游玩", "打卡", "攻略", "行程", "路线", "门票", "住宿", "酒店", "民宿"],
        "美食": ["好吃", "美食", "餐厅", "小吃", "特产", "饭店", "推荐吃"],
        "购物": ["买", "购物", "特产", "纪念品", "商场"],
        "交通": ["怎么去", "交通", "机票", "火车", "大巴", "自驾"],
        "住宿": ["住", "酒店", "民宿", "客栈", "住宿"],
    }
    
    def parse(self, query: str) -> Dict[str, Any]:
        """
        解析查询意图
        
        Args:
            query: 用户查询，如 "丽江有什么好玩的"
            
        Returns:
            {
                "core_entity": "丽江",  # 核心实体
                "intent": "旅游",       # 意图类别
                "keywords": ["丽江", "好玩", "景点", ...],  # 扩展关键词
                "original_query": "丽江有什么好玩的"
            }
        """
        result = {
            "original_query": query,
            "core_entity": "",
            "intent": "general",
            "keywords": [],
            "expanded_keywords": [],
        }
        
        # 提取核心实体（通常是地名、产品名等）
        # 简单方法：提取疑问词之前的部分
        for pattern in self.QUESTION_PATTERNS:
            match = re.search(pattern, query)
            if match:
                # 疑问词之前的部分通常是核心实体
                prefix = query[:match.start()].strip()
                if prefix:
                    result["core_entity"] = prefix
                break
        
        # 如果没找到，尝试其他方法
        if not result["core_entity"]:
            # 提取可能的地名（简单方法：取前几个字）
            words = query.replace("有什么", "").replace("怎么", "").replace("如何", "")
            words = words.replace("好玩的", "").replace("好吃的", "").strip()
            if words:
                result["core_entity"] = words[:10]  # 取前10个字符
        
        # 检测意图
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in query:
                    result["intent"] = intent
                    result["keywords"].extend(keywords)
                    break
        
        # 添加核心实体到关键词
        if result["core_entity"]:
            result["keywords"].insert(0, result["core_entity"])
        
        # 去重
        result["keywords"] = list(dict.fromkeys(result["keywords"]))
        
        return result


class RelevanceFilter:
    """
    相关性过滤器
    
    结合关键词匹配和LLM语义理解，筛选与查询相关的内容
    """
    
    def __init__(self, use_llm: bool = True):
        self.query_parser = QueryParser()
        self.use_llm = use_llm
        self._llm_engine: Optional[LLMEngine] = None
    
    @property
    def llm_engine(self) -> LLMEngine:
        if self._llm_engine is None:
            self._llm_engine = LLMEngine()
        return self._llm_engine
    
    def filter_by_relevance(
        self,
        query: str,
        texts: List[str],
        min_relevance: RelevanceLevel = RelevanceLevel.MEDIUM,
        use_llm_for_uncertain: bool = True,
    ) -> Dict[str, Any]:
        """
        根据相关性过滤文本
        
        Args:
            query: 用户查询，如 "丽江有什么好玩的"
            texts: 待筛选的文本列表
            min_relevance: 最低相关性要求
            use_llm_for_uncertain: 对不确定的文本是否使用LLM判断
            
        Returns:
            {
                "query_analysis": 查询解析结果,
                "results": [RelevanceResult, ...],
                "relevant": [高相关文本],
                "irrelevant": [不相关文本],
                "stats": 统计信息
            }
        """
        # 1. 解析查询
        query_analysis = self.query_parser.parse(query)
        keywords = query_analysis["keywords"]
        core_entity = query_analysis["core_entity"]
        
        results = []
        relevant_texts = []
        irrelevant_texts = []
        
        # 2. 对每条文本进行相关性判断
        for text in texts:
            result = self._judge_relevance(
                text=text,
                core_entity=core_entity,
                keywords=keywords,
                query=query,
                use_llm=use_llm_for_uncertain,
            )
            results.append(result)
            
            # 根据相关性分类
            relevance_order = {
                RelevanceLevel.HIGH: 3,
                RelevanceLevel.MEDIUM: 2,
                RelevanceLevel.LOW: 1,
                RelevanceLevel.IRRELEVANT: 0,
            }
            min_order = relevance_order[min_relevance]
            
            if relevance_order[result.relevance] >= min_order:
                relevant_texts.append(result)
            else:
                irrelevant_texts.append(result)
        
        # 3. 按相关性分数排序
        relevant_texts.sort(key=lambda x: x.score, reverse=True)
        
        return {
            "query_analysis": query_analysis,
            "results": [r.to_dict() for r in results],
            "relevant": [r.to_dict() for r in relevant_texts],
            "irrelevant": [r.to_dict() for r in irrelevant_texts],
            "stats": {
                "total": len(texts),
                "relevant_count": len(relevant_texts),
                "irrelevant_count": len(irrelevant_texts),
                "high_relevance": sum(1 for r in results if r.relevance == RelevanceLevel.HIGH),
                "medium_relevance": sum(1 for r in results if r.relevance == RelevanceLevel.MEDIUM),
                "low_relevance": sum(1 for r in results if r.relevance == RelevanceLevel.LOW),
            }
        }
    
    def _judge_relevance(
        self,
        text: str,
        core_entity: str,
        keywords: List[str],
        query: str,
        use_llm: bool = True,
    ) -> RelevanceResult:
        """判断单条文本的相关性"""
        if not text or not text.strip():
            return RelevanceResult(
                content=text,
                relevance=RelevanceLevel.IRRELEVANT,
                score=0.0,
                reason="空内容"
            )
        
        text_lower = text.lower()
        matched_keywords = []
        
        # 1. 关键词匹配评分
        keyword_score = 0.0
        
        # 核心实体匹配（权重最高）
        if core_entity and core_entity.lower() in text_lower:
            keyword_score += 0.5
            matched_keywords.append(core_entity)
        
        # 其他关键词匹配
        for kw in keywords:
            if kw.lower() in text_lower and kw != core_entity:
                keyword_score += 0.1
                matched_keywords.append(kw)
        
        # 限制最高分
        keyword_score = min(keyword_score, 1.0)
        
        # 2. 快速判断
        # 如果核心实体都没匹配，基本不相关
        if core_entity and core_entity.lower() not in text_lower:
            # 但如果匹配了很多其他关键词，可能还是相关的
            if keyword_score < 0.3:
                return RelevanceResult(
                    content=text,
                    relevance=RelevanceLevel.IRRELEVANT,
                    score=keyword_score,
                    reason=f"未包含核心关键词'{core_entity}'",
                    keywords_matched=matched_keywords,
                )
        
        # 3. 高置信度情况直接返回
        if keyword_score >= 0.6:
            return RelevanceResult(
                content=text,
                relevance=RelevanceLevel.HIGH,
                score=keyword_score,
                reason=f"匹配关键词: {', '.join(matched_keywords)}",
                keywords_matched=matched_keywords,
            )
        
        # 4. 中等置信度，可选使用LLM
        if keyword_score >= 0.3:
            if use_llm and self.use_llm and self.llm_engine.is_available():
                llm_result = self._llm_judge_relevance(text, query, core_entity)
                if llm_result:
                    return llm_result
            
            return RelevanceResult(
                content=text,
                relevance=RelevanceLevel.MEDIUM,
                score=keyword_score,
                reason=f"部分匹配: {', '.join(matched_keywords)}",
                keywords_matched=matched_keywords,
            )
        
        # 5. 低分但有一些匹配
        if matched_keywords:
            return RelevanceResult(
                content=text,
                relevance=RelevanceLevel.LOW,
                score=keyword_score,
                reason=f"弱匹配: {', '.join(matched_keywords)}",
                keywords_matched=matched_keywords,
            )
        
        # 6. 完全不匹配
        return RelevanceResult(
            content=text,
            relevance=RelevanceLevel.IRRELEVANT,
            score=0.0,
            reason="无关键词匹配",
            keywords_matched=[],
        )
    
    def _llm_judge_relevance(
        self,
        text: str,
        query: str,
        core_entity: str,
    ) -> Optional[RelevanceResult]:
        """使用LLM判断相关性"""
        try:
            prompt = f"""判断以下内容与用户查询的相关性。

用户查询: {query}
核心主题: {core_entity}

待判断内容:
{text[:500]}

请用JSON格式回答:
{{
    "relevance": "high/medium/low/irrelevant",
    "score": 0.0-1.0,
    "reason": "简要说明原因"
}}

只返回JSON，不要其他内容。"""

            response = self.llm_engine._call_llm(prompt)
            
            if response:
                # 解析JSON
                json_match = re.search(r'\{[^}]+\}', response)
                if json_match:
                    data = json.loads(json_match.group())
                    relevance_map = {
                        "high": RelevanceLevel.HIGH,
                        "medium": RelevanceLevel.MEDIUM,
                        "low": RelevanceLevel.LOW,
                        "irrelevant": RelevanceLevel.IRRELEVANT,
                    }
                    return RelevanceResult(
                        content=text,
                        relevance=relevance_map.get(data.get("relevance", "low"), RelevanceLevel.LOW),
                        score=float(data.get("score", 0.5)),
                        reason=data.get("reason", "LLM判断"),
                    )
        except Exception as e:
            pass
        
        return None


class SmartDataFilter:
    """
    智能数据筛选器
    
    结合垃圾过滤 + 相关性筛选，实现完整的数据清洗流程
    """
    
    def __init__(self, use_llm: bool = True):
        self.relevance_filter = RelevanceFilter(use_llm=use_llm)
        self.use_llm = use_llm
        
        # 延迟导入避免循环依赖
        self._spam_pipeline = None
    
    @property
    def spam_pipeline(self):
        if self._spam_pipeline is None:
            from .dynamic_pipeline import DynamicFilterPipeline
            self._spam_pipeline = DynamicFilterPipeline(use_llm=self.use_llm)
        return self._spam_pipeline
    
    def smart_filter(
        self,
        query: str,
        texts: List[str],
        filter_spam: bool = True,
        filter_relevance: bool = True,
        min_relevance: RelevanceLevel = RelevanceLevel.MEDIUM,
    ) -> Dict[str, Any]:
        """
        智能筛选数据
        
        流程:
        1. 过滤垃圾/广告内容
        2. 筛选与查询相关的内容
        3. 按相关性排序
        
        Args:
            query: 用户查询，如 "丽江有什么好玩的"
            texts: 待筛选文本
            filter_spam: 是否过滤垃圾内容
            filter_relevance: 是否筛选相关性
            min_relevance: 最低相关性要求
            
        Returns:
            {
                "query": 原始查询,
                "query_analysis": 查询解析,
                "final_results": 最终筛选结果(按相关性排序),
                "spam_filtered": 被过滤的垃圾内容,
                "irrelevant_filtered": 被过滤的不相关内容,
                "stats": 统计信息
            }
        """
        results = {
            "query": query,
            "query_analysis": None,
            "final_results": [],
            "spam_filtered": [],
            "irrelevant_filtered": [],
            "stats": {
                "total_input": len(texts),
                "spam_count": 0,
                "irrelevant_count": 0,
                "final_count": 0,
            }
        }
        
        current_texts = texts
        
        # Step 1: 过滤垃圾内容
        if filter_spam:
            spam_result = self.spam_pipeline.filter_with_query(
                query=f"过滤垃圾广告内容",  # 使用通用的垃圾过滤查询
                texts=current_texts,
                auto_generate_rules=False,
            )
            
            clean_texts = []
            for i, r in enumerate(spam_result["results"]):
                if r["is_spam"]:
                    results["spam_filtered"].append({
                        "content": current_texts[i],
                        "reason": r.get("matched_rules", []),
                    })
                else:
                    clean_texts.append(current_texts[i])
            
            results["stats"]["spam_count"] = len(results["spam_filtered"])
            current_texts = clean_texts
        
        # Step 2: 筛选相关内容
        if filter_relevance and current_texts:
            relevance_result = self.relevance_filter.filter_by_relevance(
                query=query,
                texts=current_texts,
                min_relevance=min_relevance,
            )
            
            results["query_analysis"] = relevance_result["query_analysis"]
            results["final_results"] = relevance_result["relevant"]
            results["irrelevant_filtered"] = relevance_result["irrelevant"]
            results["stats"]["irrelevant_count"] = len(results["irrelevant_filtered"])
        else:
            # 不筛选相关性，直接返回
            results["final_results"] = [{"content": t, "relevance": "unknown", "score": 0} for t in current_texts]
        
        results["stats"]["final_count"] = len(results["final_results"])
        
        return results
