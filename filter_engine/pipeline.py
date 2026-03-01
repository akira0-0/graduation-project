# -*- coding: utf-8 -*-
"""过滤管道 - 整合规则引擎和LLM引擎"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from .config import settings
from .core import RuleEngine, LLMEngine, DecisionEngine
from .rules import RuleManager, FilterResult


class FilterPipeline:
    """过滤管道"""
    
    def __init__(self, use_llm: bool = True):
        self.rule_manager = RuleManager(settings.DATABASE_PATH)
        self.rule_engine = RuleEngine(self.rule_manager)
        self.decision_engine = DecisionEngine()
        
        self.use_llm = use_llm
        self._llm_engine = None
    
    @property
    def llm_engine(self) -> LLMEngine:
        """懒加载LLM引擎"""
        if self._llm_engine is None:
            self._llm_engine = LLMEngine()
        return self._llm_engine
    
    def filter_text(self, text: str, use_llm: bool = None) -> FilterResult:
        """
        过滤单条文本
        
        Args:
            text: 文本内容
            use_llm: 是否使用LLM（默认使用初始化时的设置）
        
        Returns:
            FilterResult
        """
        use_llm = use_llm if use_llm is not None else self.use_llm
        
        # 规则引擎过滤
        rule_result = self.rule_engine.filter(text)
        
        # LLM过滤（可选）
        llm_result = None
        if use_llm and settings.LLM_API_KEY:
            llm_result = self.llm_engine.filter(text)
        
        # 协同决策
        decision = self.decision_engine.decide(rule_result, llm_result)
        
        return FilterResult(
            id="",
            content=text,
            is_spam=decision["is_spam"],
            confidence=decision["confidence"],
            matched_rules=decision["matched_rules"],
            llm_reason=decision.get("llm_reason"),
            category=decision.get("category"),
        )
    
    def filter_batch(
        self,
        items: List[Dict],
        content_field: str = "content",
        use_llm: bool = None,
    ) -> List[Dict]:
        """
        批量过滤
        
        Args:
            items: 数据列表，每项需包含content_field指定的字段
            content_field: 内容字段名
            use_llm: 是否使用LLM
        
        Returns:
            带过滤结果的数据列表
        """
        use_llm = use_llm if use_llm is not None else self.use_llm
        results = []
        
        for item in items:
            text = item.get(content_field, "")
            result = self.filter_text(text, use_llm=use_llm)
            
            # 合并原始数据和过滤结果
            filtered_item = {
                **item,
                "filter_result": {
                    "is_spam": result.is_spam,
                    "confidence": result.confidence,
                    "matched_rules": result.matched_rules,
                    "llm_reason": result.llm_reason,
                    "category": result.category,
                }
            }
            results.append(filtered_item)
        
        return results
    
    def filter_and_split(
        self,
        items: List[Dict],
        content_field: str = "content",
        use_llm: bool = None,
    ) -> Dict[str, List[Dict]]:
        """
        过滤并分离垃圾/正常数据
        
        Returns:
            {
                "clean": [...],  # 正常数据
                "spam": [...],   # 垃圾数据
                "stats": {...}   # 统计信息
            }
        """
        filtered = self.filter_batch(items, content_field, use_llm)
        
        clean = []
        spam = []
        
        for item in filtered:
            if item["filter_result"]["is_spam"]:
                spam.append(item)
            else:
                clean.append(item)
        
        return {
            "clean": clean,
            "spam": spam,
            "stats": {
                "total": len(items),
                "clean_count": len(clean),
                "spam_count": len(spam),
                "spam_rate": round(len(spam) / len(items) * 100, 2) if items else 0,
            }
        }
    
    def save_results(
        self,
        results: Dict,
        output_path: str = None,
    ) -> str:
        """保存过滤结果到JSON文件"""
        if output_path is None:
            Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            output_path = f"{settings.OUTPUT_DIR}/filtered_{date_str}.json"
        
        output = {
            "metadata": {
                "filtered_at": datetime.now().isoformat(),
                "stats": results.get("stats", {}),
            },
            "clean": results.get("clean", []),
            "spam": results.get("spam", []),
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    def reload_rules(self):
        """重新加载规则"""
        self.rule_engine.reload()
