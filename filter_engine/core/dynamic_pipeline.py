# -*- coding: utf-8 -*-
# ⚠️  [REDUNDANT - 待审查是否删除]
# 原因：DynamicFilterPipeline 是第一代"动态规则"方案（基于 QueryAnalyzer + RuleSelector 的关键词匹配），
#       已被 SmartRuleMatcher（llm/smart_matcher.py）完全取代。
#       SmartRuleMatcher 用 LLM 理解场景并从 Supabase 动态加载规则，能力更强。
#       当前剩余引用：
#         1. /api/filter/dynamic 端点（遗留接口，已标 deprecated）
#         2. relevance_filter.py 中的垃圾过滤（但 auto_filter 以 llm_only=True 跳过此路径）
#       删除条件：删除 /api/filter/dynamic 端点，并将 relevance_filter.py 的垃圾过滤路径改写后可安全删除。
#       连带删除：query_analyzer.py, rule_selector.py, decision.py, cache.py, rule_generator.py
"""
增强版过滤管道
集成LLM动态规则选择功能
"""
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

from .query_analyzer import QueryAnalyzer, QueryIntent, FilterScenario, FilterSeverity
from .rule_selector import RuleSelector, RuleSelectionResult
from .rule_engine import RuleEngine
from .decision import DecisionEngine
from .cache import FilterCache
from ..llm.engine import LLMEngine
from ..llm.rule_generator import RuleGenerator, GapAnalysis, GeneratedRule
from ..rules.manager import RuleManager
from ..rules.models import FilterResult
from ..config import settings


@dataclass
class DynamicFilterConfig:
    """动态过滤配置"""
    enable_dynamic_rules: bool = True          # 是否启用动态规则选择
    enable_rule_generation: bool = True        # 是否启用规则自动生成
    auto_save_generated_rules: bool = False    # 是否自动保存生成的规则
    min_confidence_to_save: float = 0.8        # 保存规则的最低置信度
    max_rules_per_session: int = 5             # 每次会话最多生成规则数
    analyze_unfiltered: bool = True            # 是否分析未过滤内容


@dataclass
class DynamicFilterStats:
    """动态过滤统计"""
    total_processed: int = 0
    filtered_count: int = 0
    rules_generated: int = 0
    rules_saved: int = 0
    dynamic_rules_used: int = 0
    scenarios_detected: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "total_processed": self.total_processed,
            "filtered_count": self.filtered_count,
            "rules_generated": self.rules_generated,
            "rules_saved": self.rules_saved,
            "dynamic_rules_used": self.dynamic_rules_used,
            "scenarios_detected": self.scenarios_detected,
        }


class DynamicFilterPipeline:
    """
    增强版过滤管道
    
    支持:
    1. 根据用户查询动态选择规则
    2. 分析规则缺口并自动生成新规则
    3. 场景感知的规则应用
    4. LLM辅助规则优化
    
    使用示例:
    ```python
    pipeline = DynamicFilterPipeline(db_path="rules.db")
    
    # 带查询的过滤
    results = pipeline.filter_with_query(
        query="过滤电商评论中的广告和刷单内容",
        texts=["好评返现加微信xxx", "这个商品质量很好"],
    )
    
    # 自动生成规则
    generated = pipeline.generate_missing_rules(
        query="过滤微信引流广告",
        sample_texts=["加VX: abc123", "微信联系我"],
    )
    ```
    """
    
    def __init__(
        self,
        db_path: str = None,
        use_llm: bool = True,
        use_cache: bool = True,
        config: DynamicFilterConfig = None,
    ):
        """
        初始化增强版管道
        
        Args:
            db_path: 规则数据库路径
            use_llm: 是否启用LLM
            use_cache: 是否启用缓存
            config: 动态过滤配置
        """
        # 基础组件
        self.db_path = db_path or settings.DATABASE_PATH
        self.rule_manager = RuleManager(self.db_path)
        self.rule_engine = RuleEngine(self.rule_manager)
        self.decision_engine = DecisionEngine()
        
        # 动态规则组件
        self.query_analyzer = QueryAnalyzer()
        self.rule_selector = RuleSelector(self.rule_manager)
        
        # LLM组件
        self.use_llm = use_llm
        self._llm_engine: Optional[LLMEngine] = None
        self._rule_generator: Optional[RuleGenerator] = None
        
        # 缓存
        self.use_cache = use_cache
        self._cache = FilterCache() if use_cache else None
        
        # 配置
        self.config = config or DynamicFilterConfig()
        
        # 统计
        self.stats = DynamicFilterStats()
        
        # 当前会话状态
        self._current_intent: Optional[QueryIntent] = None
        self._current_rules: Optional[RuleSelectionResult] = None
        self._session_generated_rules: List[GeneratedRule] = []
    
    @property
    def llm_engine(self) -> LLMEngine:
        """懒加载LLM引擎"""
        if self._llm_engine is None:
            self._llm_engine = LLMEngine()
        return self._llm_engine
    
    @property
    def rule_generator(self) -> RuleGenerator:
        """懒加载规则生成器"""
        if self._rule_generator is None:
            self._rule_generator = RuleGenerator(
                llm_engine=self.llm_engine,
                rule_manager=self.rule_manager
            )
        return self._rule_generator
    
    def analyze_query(
        self,
        query: str,
        context: Dict[str, Any] = None,
        explicit_scenario: str = None,
        explicit_severity: str = None,
    ) -> QueryIntent:
        """
        分析查询意图
        
        Args:
            query: 用户查询
            context: 上下文信息
            explicit_scenario: 显式指定场景
            explicit_severity: 显式指定严格程度
            
        Returns:
            QueryIntent: 查询意图
        """
        intent = self.query_analyzer.analyze(
            query=query,
            context=context,
            explicit_scenario=explicit_scenario,
            explicit_severity=explicit_severity,
        )
        
        # 更新统计
        scenario_name = intent.scenario.value
        self.stats.scenarios_detected[scenario_name] = \
            self.stats.scenarios_detected.get(scenario_name, 0) + 1
        
        self._current_intent = intent
        return intent
    
    def select_rules(self, intent: QueryIntent = None) -> RuleSelectionResult:
        """
        根据意图选择规则
        
        Args:
            intent: 查询意图（如果为None则使用当前会话意图）
            
        Returns:
            RuleSelectionResult: 规则选择结果
        """
        intent = intent or self._current_intent
        
        if intent is None:
            # 默认意图
            intent = QueryIntent()
        
        result = self.rule_selector.select(intent)
        
        # 更新统计
        self.stats.dynamic_rules_used += len(result.scenario_rules) + len(result.extra_rules)
        
        self._current_rules = result
        return result
    
    def filter_with_query(
        self,
        query: str,
        texts: List[str],
        context: Dict[str, Any] = None,
        auto_generate_rules: bool = None,
    ) -> Dict[str, Any]:
        """
        带查询的过滤
        
        这是主要的过滤入口，会：
        1. 分析查询意图
        2. 动态选择规则
        3. 执行过滤
        4. （可选）分析缺口并生成规则
        
        Args:
            query: 用户查询描述
            texts: 待过滤文本列表
            context: 上下文信息
            auto_generate_rules: 是否自动生成缺失规则
            
        Returns:
            Dict: {
                "intent": 查询意图,
                "selected_rules": 选中的规则,
                "results": 过滤结果列表,
                "generated_rules": 生成的规则（如果有）,
                "stats": 统计信息,
            }
        """
        auto_generate = auto_generate_rules if auto_generate_rules is not None \
            else self.config.enable_rule_generation
        
        # 1. 分析查询意图
        intent = self.analyze_query(query, context)
        
        # 2. 选择规则
        selected_rules = self.select_rules(intent)
        
        # 3. 使用选中的规则创建临时规则引擎
        if self.config.enable_dynamic_rules and selected_rules.all_rules:
            temp_rule_engine = self._create_temp_rule_engine(selected_rules)
        else:
            temp_rule_engine = self.rule_engine
        
        # 4. 执行过滤
        results = []
        filter_results_raw = []
        
        for text in texts:
            result = self._filter_single_text(text, temp_rule_engine, intent)
            results.append(result)
            filter_results_raw.append(result.to_dict())
            
            # 更新统计
            self.stats.total_processed += 1
            if result.is_spam:
                self.stats.filtered_count += 1
        
        # 5. 分析缺口并生成规则
        generated_rules = []
        if auto_generate and self.use_llm:
            generated_rules = self._analyze_and_generate_rules(
                query=query,
                texts=texts,
                filter_results=filter_results_raw,
                intent=intent,
                selected_rules=selected_rules,
            )
        
        return {
            "intent": intent.to_dict(),
            "selected_rules": selected_rules.to_dict(),
            "results": [r.to_dict() for r in results],
            "generated_rules": [r.to_dict() for r in generated_rules],
            "stats": {
                "total": len(texts),
                "filtered": sum(1 for r in results if r.is_spam),
                "clean": sum(1 for r in results if not r.is_spam),
            },
        }
    
    def _create_temp_rule_engine(self, selected_rules: RuleSelectionResult) -> RuleEngine:
        """创建使用选中规则的临时规则引擎"""
        # 创建一个使用特定规则的临时规则引擎
        # 注意：这里需要创建一个临时的 RuleManager 来包装选中的规则
        from ..rules import RuleManager
        
        # 创建临时规则管理器的子类，重写 list() 方法返回选中的规则
        class _TempRuleManager(RuleManager):
            def __init__(self, rules: List):
                # 不调用父类 __init__，避免数据库初始化
                self._temp_rules = rules
            
            def list(self, enabled_only=False, **kwargs):
                # 直接返回预选的规则列表
                return self._temp_rules
        
        temp_manager = _TempRuleManager(selected_rules.all_rules)
        temp_engine = RuleEngine(temp_manager)
        
        return temp_engine
    
    def _filter_single_text(
        self,
        text: str,
        rule_engine: RuleEngine,
        intent: QueryIntent,
    ) -> FilterResult:
        """过滤单条文本"""
        if not text or not text.strip():
            return FilterResult(
                content=text,
                is_spam=False,
                confidence=0.0,
                source="empty",
            )
        
        # 检查缓存
        if self._cache:
            cached = self._cache.get(text)
            if cached:
                return cached
        
        # 规则引擎过滤
        rule_result = rule_engine.filter(text)
        
        # LLM过滤（如果启用且规则引擎标记为可疑）
        llm_result = None
        if self.use_llm and self.llm_engine.is_available():
            should_call_llm = self.decision_engine.should_use_llm(rule_result)
            if should_call_llm:
                rule_hints = [m.rule_name for m in rule_result.matched_rules] if rule_result.is_matched else None
                context_str = json.dumps(intent.to_dict(), ensure_ascii=False) if intent else None
                llm_result = self.llm_engine.filter(text, context=context_str, rule_hints=rule_hints)
        
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
        
        # 更新缓存
        if self._cache:
            self._cache.set(text, result)
        
        return result
    
    def _analyze_and_generate_rules(
        self,
        query: str,
        texts: List[str],
        filter_results: List[Dict],
        intent: QueryIntent,
        selected_rules: RuleSelectionResult,
    ) -> List[GeneratedRule]:
        """分析缺口并生成规则"""
        # 检查是否达到会话限制
        if len(self._session_generated_rules) >= self.config.max_rules_per_session:
            return []
        
        # 分析规则缺口
        gap = self.rule_generator.analyze_gap(
            texts=texts,
            filter_results=filter_results,
            custom_keywords=intent.custom_keywords,
        )
        
        if not gap.has_gaps():
            return []
        
        # 检查选中规则的覆盖情况
        selector_gaps = self.rule_selector.get_missing_rule_gaps(intent, selected_rules)
        
        # 合并缺口信息
        gap.uncovered_keywords.extend(selector_gaps.get("uncovered_keywords", []))
        gap.uncovered_keywords = list(set(gap.uncovered_keywords))
        
        # 生成规则
        remaining_quota = self.config.max_rules_per_session - len(self._session_generated_rules)
        generated_rules = self.rule_generator.generate_rules(
            requirement=query,
            gap=gap,
            max_rules=remaining_quota,
        )
        
        # 更新统计
        self.stats.rules_generated += len(generated_rules)
        
        # 自动保存高置信度规则
        if self.config.auto_save_generated_rules:
            for rule in generated_rules:
                if rule.confidence >= self.config.min_confidence_to_save:
                    rule_id = self.rule_generator.save_rule(rule)
                    if rule_id:
                        self.stats.rules_saved += 1
        
        # 记录到会话
        self._session_generated_rules.extend(generated_rules)
        
        return generated_rules
    
    def generate_missing_rules(
        self,
        query: str,
        sample_texts: List[str],
        category: str = None,
    ) -> List[GeneratedRule]:
        """
        主动生成缺失规则
        
        Args:
            query: 需求描述
            sample_texts: 样本文本
            category: 目标类别
            
        Returns:
            List[GeneratedRule]: 生成的规则列表
        """
        # 构建缺口分析
        gap = GapAnalysis(
            text_samples=sample_texts,
            analysis_reason=f"用户请求: {query}",
        )
        
        if category:
            gap.missing_categories.append(category)
        
        # 生成规则
        generated_rules = self.rule_generator.generate_rules(
            requirement=query,
            gap=gap,
            max_rules=3,
        )
        
        return generated_rules
    
    def save_generated_rule(self, rule: GeneratedRule) -> Optional[int]:
        """保存生成的规则"""
        return self.rule_generator.save_rule(rule)
    
    def filter_text(
        self,
        text: str,
        scenario: str = None,
        severity: str = None,
    ) -> FilterResult:
        """
        简单的单文本过滤
        
        Args:
            text: 待过滤文本
            scenario: 场景
            severity: 严格程度
            
        Returns:
            FilterResult: 过滤结果
        """
        # 构建简单意图
        intent = QueryIntent(
            scenario=FilterScenario(scenario) if scenario else FilterScenario.NORMAL,
            severity=FilterSeverity(severity) if severity else FilterSeverity.NORMAL,
        )
        
        # 选择规则
        if self.config.enable_dynamic_rules:
            selected_rules = self.select_rules(intent)
            rule_engine = self._create_temp_rule_engine(selected_rules) if selected_rules.all_rules else self.rule_engine
        else:
            rule_engine = self.rule_engine
        
        return self._filter_single_text(text, rule_engine, intent)
    
    def reset_session(self):
        """重置会话状态"""
        self._current_intent = None
        self._current_rules = None
        self._session_generated_rules.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.to_dict()
        stats["session"] = {
            "current_scenario": self._current_intent.scenario.value if self._current_intent else None,
            "rules_selected": self._current_rules.rule_count if self._current_rules else None,
            "rules_generated_this_session": len(self._session_generated_rules),
        }
        return stats
    
    def reload_rules(self):
        """重新加载规则"""
        self.rule_engine.reload()
        self.rule_selector.invalidate_cache()
    
    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()


# 便捷函数
def create_dynamic_pipeline(
    db_path: str = None,
    use_llm: bool = True,
    enable_rule_generation: bool = True,
) -> DynamicFilterPipeline:
    """创建动态过滤管道的便捷函数"""
    config = DynamicFilterConfig(
        enable_dynamic_rules=True,
        enable_rule_generation=enable_rule_generation,
    )
    return DynamicFilterPipeline(
        db_path=db_path,
        use_llm=use_llm,
        config=config,
    )
