# -*- coding: utf-8 -*-
# ⚠️  [REDUNDANT - 待审查是否删除]
# 原因：FilterPipeline 是项目初期的两层过滤方案（规则引擎 + LLM 直判），
#       现已被新的三层系统（SmartRuleMatcher L2 + SmartDataFilter L3）取代。
#       当前仅剩 /api/filter（单条）和 /api/filter/batch（批量）两个老接口在使用，
#       这两个接口本身也是遗留接口（见 api.py 中的 deprecated 标记）。
#       删除条件：确认 /api/filter 和 /api/filter/batch 不再被任何客户端调用后可安全删除。
"""
过滤管道
整合规则引擎、LLM引擎和协同决策
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

from .config import settings
from .core import RuleEngine, DecisionEngine, FilterCache
from .llm import LLMEngine
from .rules import RuleManager, FilterResult, BatchFilterResult


class FilterPipeline:
    """
    过滤管道
    
    整合规则过滤、LLM语义过滤和协同决策
    
    流程:
    1. 检查缓存
    2. 规则引擎过滤
    3. 判断是否需要LLM
    4. LLM过滤（可选）
    5. 协同决策
    6. 更新缓存
    """
    
    def __init__(
        self,
        use_llm: bool = True,
        use_cache: bool = True,
        llm_for_suspicious_only: bool = True,
    ):
        """
        初始化过滤管道
        
        Args:
            use_llm: 是否启用LLM过滤
            use_cache: 是否启用缓存
            llm_for_suspicious_only: 是否仅对疑似项使用LLM
        """
        # 规则管理器和引擎
        self.rule_manager = RuleManager(settings.DATABASE_PATH)
        self.rule_engine = RuleEngine(self.rule_manager)
        
        # 决策引擎
        self.decision_engine = DecisionEngine()
        
        # 缓存
        self.use_cache = use_cache
        self._cache = FilterCache() if use_cache else None
        
        # LLM配置
        self.use_llm = use_llm
        self.llm_for_suspicious_only = llm_for_suspicious_only
        self._llm_engine: Optional[LLMEngine] = None
    
    @property
    def llm_engine(self) -> LLMEngine:
        """懒加载LLM引擎"""
        if self._llm_engine is None:
            self._llm_engine = LLMEngine()
        return self._llm_engine
    
    def reload_rules(self):
        """重新加载规则"""
        self.rule_engine.reload()
    
    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()
    
    def filter_text(
        self,
        text: str,
        use_llm: bool = None,
        context: str = None,
    ) -> FilterResult:
        """
        过滤单条文本
        
        Args:
            text: 文本内容
            use_llm: 是否使用LLM（覆盖默认设置）
            context: 上下文信息
        
        Returns:
            FilterResult
        """
        if not text or not text.strip():
            return FilterResult(
                content=text,
                is_spam=False,
                confidence=0.0,
                source="empty",
            )
        
        use_llm = use_llm if use_llm is not None else self.use_llm
        
        # 1. 检查缓存
        if self._cache:
            cached = self._cache.get(text)
            if cached:
                return cached
        
        # 2. 规则引擎过滤
        rule_result = self.rule_engine.filter(text)
        
        # 3. 判断是否需要LLM
        llm_result = None
        should_call_llm = False
        
        if use_llm and self.llm_engine.is_available():
            if self.llm_for_suspicious_only:
                # 仅对疑似项调用LLM
                should_call_llm = self.decision_engine.should_use_llm(rule_result)
            else:
                # 总是调用LLM
                should_call_llm = True
        
        # 4. LLM过滤
        if should_call_llm:
            rule_hints = [m.rule_name for m in rule_result.matched_rules] if rule_result.is_matched else None
            llm_result = self.llm_engine.filter(text, context=context, rule_hints=rule_hints)
        
        # 5. 协同决策
        decision = self.decision_engine.decide(rule_result, llm_result)
        
        # 6. 构建结果
        result = FilterResult(
            content=text,
            is_spam=decision["is_spam"],
            confidence=decision["confidence"],
            matched_rules=decision.get("matched_rules", []),
            llm_reason=decision.get("llm_reason"),
            category=decision.get("category"),
            source=decision.get("source", "rule"),
        )
        
        # 7. 更新缓存
        if self._cache:
            self._cache.set(text, result)
        
        return result
    
    async def filter_text_async(
        self,
        text: str,
        use_llm: bool = None,
        context: str = None,
    ) -> FilterResult:
        """异步过滤单条文本"""
        if not text or not text.strip():
            return FilterResult(content=text, is_spam=False, confidence=0.0, source="empty")
        
        use_llm = use_llm if use_llm is not None else self.use_llm
        
        # 检查缓存
        if self._cache:
            cached = self._cache.get(text)
            if cached:
                return cached
        
        # 规则引擎过滤
        rule_result = self.rule_engine.filter(text)
        
        # LLM过滤
        llm_result = None
        if use_llm and self.llm_engine.is_available():
            should_call_llm = (
                not self.llm_for_suspicious_only or
                self.decision_engine.should_use_llm(rule_result)
            )
            if should_call_llm:
                rule_hints = [m.rule_name for m in rule_result.matched_rules] if rule_result.is_matched else None
                llm_result = await self.llm_engine.filter_async(text, context=context, rule_hints=rule_hints)
        
        # 协同决策
        decision = self.decision_engine.decide(rule_result, llm_result)
        
        result = FilterResult(
            content=text,
            is_spam=decision["is_spam"],
            confidence=decision["confidence"],
            matched_rules=decision.get("matched_rules", []),
            llm_reason=decision.get("llm_reason"),
            category=decision.get("category"),
            source=decision.get("source", "rule"),
        )
        
        if self._cache:
            self._cache.set(text, result)
        
        return result
    
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
        stats = BatchFilterResult()
        stats.total = len(items)
        
        for item in items:
            text = item.get(content_field, "")
            result = self.filter_text(text, use_llm=use_llm)
            
            # 统计
            if result.is_spam:
                if result.confidence >= settings.SPAM_THRESHOLD:
                    stats.spam_count += 1
                else:
                    stats.suspicious_count += 1
            else:
                stats.clean_count += 1
            
            if result.category:
                stats.categories[result.category] = stats.categories.get(result.category, 0) + 1
            
            # 合并原始数据和过滤结果
            filtered_item = {
                **item,
                "filter_result": result.to_dict()
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
        过滤并分组
        
        Returns:
            {"spam": [...], "clean": [...], "suspicious": [...]}
        """
        filtered = self.filter_batch(items, content_field, use_llm)
        
        result = {
            "spam": [],
            "clean": [],
            "suspicious": [],
        }
        
        for item in filtered:
            fr = item.get("filter_result", {})
            if fr.get("is_spam"):
                if fr.get("confidence", 0) >= settings.SPAM_THRESHOLD:
                    result["spam"].append(item)
                else:
                    result["suspicious"].append(item)
            else:
                result["clean"].append(item)
        
        return result
    
    def save_results(
        self,
        results: List[Dict],
        output_path: str = None,
        format: str = "json",
    ) -> str:
        """
        保存过滤结果
        
        Args:
            results: 过滤结果列表
            output_path: 输出路径
            format: 输出格式 (json/csv)
            
        Returns:
            输出文件路径
        """
        if output_path is None:
            output_dir = Path(settings.OUTPUT_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"filter_results_{timestamp}.{format}")
        
        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        elif format == "csv":
            import csv
            if results:
                # 展平filter_result
                flat_results = []
                for item in results:
                    flat = {k: v for k, v in item.items() if k != "filter_result"}
                    fr = item.get("filter_result", {})
                    for k, v in fr.items():
                        flat[f"filter_{k}"] = v
                    flat_results.append(flat)
                
                with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=flat_results[0].keys())
                    writer.writeheader()
                    writer.writerows(flat_results)
        
        return output_path
    
    def get_stats(self) -> Dict[str, Any]:
        """获取管道统计信息"""
        stats = {
            "rule_engine": self.rule_engine.get_stats(),
            "llm_available": self.llm_engine.is_available() if self.use_llm else False,
        }
        
        if self._cache:
            stats["cache"] = self._cache.get_stats()
        
        return stats
    
    def reload_rules(self):
        """重新加载规则"""
        self.rule_engine.reload()
