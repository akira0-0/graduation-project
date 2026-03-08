# -*- coding: utf-8 -*-
"""
数据过滤引擎

功能:
- 动态可管理的规则过滤引擎 (AC自动机 + 正则)
- 基于LLM的语义理解过滤
- 协同决策系统
- LLM驱动的动态规则选择
- 自动规则生成
- 缓存优化

使用示例:
    from filter_engine import FilterPipeline
    
    pipeline = FilterPipeline(use_llm=True)
    result = pipeline.filter_text("待检测的文本")
    print(result.is_spam, result.confidence)
    
    # 动态规则选择
    from filter_engine import DynamicFilterPipeline
    
    dynamic_pipeline = DynamicFilterPipeline(use_llm=True)
    result = dynamic_pipeline.filter_with_query(
        query="过滤电商评论中的广告",
        texts=["加我微信xxx", "产品很好用"],
    )
"""
from .config import settings, get_settings
from .pipeline import FilterPipeline
from .rules import (
    Rule,
    RuleCreate,
    RuleUpdate,
    RuleType,
    RuleCategory,
    RuleManager,
    FilterResult,
)
from .core import (
    RuleEngine, 
    DecisionEngine, 
    FilterCache,
    DynamicFilterPipeline,
    DynamicFilterConfig,
    QueryAnalyzer,
    QueryIntent,
    FilterScenario,
    FilterSeverity,
    RuleSelector,
    RuleSelectionResult,
)
from .llm import LLMEngine, RuleGenerator, GapAnalysis, GeneratedRule

__version__ = "2.1.0"
__all__ = [
    # 配置
    "settings",
    "get_settings",
    # 管道
    "FilterPipeline",
    "DynamicFilterPipeline",
    "DynamicFilterConfig",
    # 规则
    "Rule",
    "RuleCreate",
    "RuleUpdate",
    "RuleType",
    "RuleCategory",
    "RuleManager",
    "FilterResult",
    # 引擎
    "RuleEngine",
    "DecisionEngine",
    "FilterCache",
    "LLMEngine",
    # 动态规则选择
    "QueryAnalyzer",
    "QueryIntent",
    "FilterScenario",
    "FilterSeverity",
    "RuleSelector",
    "RuleSelectionResult",
    # 规则生成
    "RuleGenerator",
    "GapAnalysis",
    "GeneratedRule",
]

