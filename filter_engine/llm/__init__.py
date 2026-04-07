# -*- coding: utf-8 -*-
"""LLM过滤模块"""
from .client import (
    BaseLLMClient,
    OpenAIClient,
    QwenClient,
    GLMClient,
    OllamaClient,
    create_llm_client,
    LLMResponse,
)
from .engine import LLMEngine
from .parser import LLMOutputParser, parse_llm_output, parse_batch_output
from .prompts import (
    SYSTEM_PROMPT,
    FILTER_PROMPT_TEMPLATE,
    build_filter_prompt,
    build_batch_filter_prompt,
    build_context_filter_prompt,
)
from .rule_generator import RuleGenerator, GapAnalysis, GeneratedRule
from .smart_matcher import (
    SmartRuleMatcher,
    SmartMatchResult,
    ThoughtTrace,
    MatchedRuleInfo,
    GapRule,
    SuggestSaveRule,
)
from .prompts_smart import (
    SMART_MATCH_SYSTEM,
    SMART_MATCH_PROMPT,
    build_smart_match_prompt,
)

__all__ = [
    # 客户端
    "BaseLLMClient",
    "OpenAIClient",
    "QwenClient",
    "GLMClient",
    "OllamaClient",
    "create_llm_client",
    "LLMResponse",
    # 引擎
    "LLMEngine",
    # 解析器
    "LLMOutputParser",
    "parse_llm_output",
    "parse_batch_output",
    # 提示词
    "SYSTEM_PROMPT",
    "FILTER_PROMPT_TEMPLATE",
    "build_filter_prompt",
    "build_batch_filter_prompt",
    "build_context_filter_prompt",
    # 规则生成器
    "RuleGenerator",
    "GapAnalysis",
    "GeneratedRule",
    # 智能匹配器
    "SmartRuleMatcher",
    "SmartMatchResult",
    "ThoughtTrace",
    "MatchedRuleInfo",
    "GapRule,",
    "SuggestSaveRule",
    "SMART_MATCH_SYSTEM",
    "SMART_MATCH_PROMPT",
    "build_smart_match_prompt",
]
