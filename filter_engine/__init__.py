# -*- coding: utf-8 -*-
"""
数据过滤引擎

功能:
- 动态可管理的规则过滤引擎 (AC自动机 + 正则)
- SmartRuleMatcher 智能场景规则匹配 (Layer-2)
- SmartDataFilter LLM 语义相关性过滤 (Layer-3)

使用示例:
    from filter_engine.api import app
    # 通过 /api/filter/auto 或 /api/filter/complete 调用
"""
from .config import settings, get_settings
from .rules import (
    Rule,
    RuleCreate,
    RuleUpdate,
    RuleType,
    RuleCategory,
    RuleManager,
    FilterResult,
)
from .core import RuleEngine
from .core.relevance_filter import RelevanceFilter, RelevanceLevel, SmartDataFilter

__version__ = "2.1.0"
__all__ = [
    # 配置
    "settings",
    "get_settings",
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
    "RelevanceFilter",
    "RelevanceLevel",
    "SmartDataFilter",
]
