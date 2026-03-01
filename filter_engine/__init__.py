# -*- coding: utf-8 -*-
"""
数据过滤引擎

功能:
- 动态可管理的规则过滤引擎 (AC自动机 + 正则)
- 基于LLM的语义理解过滤
- 协同决策系统
- 缓存优化

使用示例:
    from filter_engine import FilterPipeline
    
    pipeline = FilterPipeline(use_llm=True)
    result = pipeline.filter_text("待检测的文本")
    print(result.is_spam, result.confidence)
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
from .core import RuleEngine, DecisionEngine, FilterCache
from .llm import LLMEngine

__version__ = "2.0.0"
__all__ = [
    # 配置
    "settings",
    "get_settings",
    # 管道
    "FilterPipeline",
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
]

