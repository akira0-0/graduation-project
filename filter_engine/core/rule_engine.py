# -*- coding: utf-8 -*-
"""
规则匹配引擎
集成AC自动机进行高速多关键词匹配，优化正则表达式处理
"""
import re
import json
import signal
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from functools import lru_cache

try:
    import ahocorasick
    HAS_AHOCORASICK = True
except ImportError:
    HAS_AHOCORASICK = False
    print("Warning: pyahocorasick not installed, using fallback matching")

from ..rules import RuleManager, Rule, RuleType, MatchedRule, RuleEngineResult


@dataclass
class CompiledRule:
    """编译后的规则"""
    rule: Rule
    keywords: List[str] = field(default_factory=list)
    regex_patterns: List[re.Pattern] = field(default_factory=list)
    pattern_config: Dict[str, Any] = field(default_factory=dict)


class RegexTimeoutError(Exception):
    """正则表达式超时异常"""
    pass


class RuleEngine:
    """
    规则匹配引擎
    
    特性:
    - AC自动机进行多关键词并行匹配 O(n)
    - 正则表达式预编译和超时保护
    - 模式规则支持组合逻辑
    """
    
    # 正则匹配超时时间（秒）
    REGEX_TIMEOUT = 1.0
    
    def __init__(self, rule_manager: RuleManager):
        """
        初始化规则引擎
        
        Args:
            rule_manager: 规则管理器实例
        """
        self.rule_manager = rule_manager
        self._compiled_rules: Dict[int, CompiledRule] = {}
        self._ac_automaton = None
        self._keyword_to_rule: Dict[str, List[int]] = {}  # keyword -> [rule_ids]
        
        self._build_engine()
    
    def _build_engine(self):
        """构建匹配引擎"""
        rules = self.rule_manager.list(enabled_only=True)
        self._compiled_rules.clear()
        self._keyword_to_rule.clear()
        
        all_keywords = []
        
        for rule in rules:
            compiled = self._compile_rule(rule)
            self._compiled_rules[rule.id] = compiled
            
            # 收集所有关键词用于AC自动机
            for kw in compiled.keywords:
                all_keywords.append((kw, rule.id))
                if kw not in self._keyword_to_rule:
                    self._keyword_to_rule[kw] = []
                self._keyword_to_rule[kw].append(rule.id)
        
        # 构建AC自动机
        self._build_ac_automaton(all_keywords)
    
    def _compile_rule(self, rule: Rule) -> CompiledRule:
        """编译单条规则"""
        compiled = CompiledRule(rule=rule)
        
        try:
            content = json.loads(rule.content)
        except json.JSONDecodeError:
            content = [rule.content]
        
        if rule.type == RuleType.KEYWORD:
            # 关键词列表
            if isinstance(content, list):
                compiled.keywords = [str(kw).lower() for kw in content if kw]
            else:
                compiled.keywords = [str(content).lower()]
                
        elif rule.type == RuleType.REGEX:
            # 正则表达式
            patterns = content if isinstance(content, list) else [content]
            for pattern in patterns:
                try:
                    # 编译正则，使用非贪婪模式和忽略大小写
                    compiled.regex_patterns.append(
                        re.compile(pattern, re.IGNORECASE | re.DOTALL)
                    )
                except re.error as e:
                    print(f"Warning: Invalid regex pattern '{pattern}': {e}")
                    
        elif rule.type == RuleType.PATTERN:
            # 模式规则（组合逻辑）
            compiled.pattern_config = content if isinstance(content, dict) else {}
            
            # 提取模式中的关键词
            if "keywords" in compiled.pattern_config:
                compiled.keywords = [
                    str(kw).lower() 
                    for kw in compiled.pattern_config["keywords"] 
                    if kw
                ]
            if "regex" in compiled.pattern_config:
                for pattern in compiled.pattern_config.get("regex", []):
                    try:
                        compiled.regex_patterns.append(
                            re.compile(pattern, re.IGNORECASE)
                        )
                    except re.error:
                        pass
        
        return compiled
    
    def _build_ac_automaton(self, keywords: List[Tuple[str, int]]):
        """构建AC自动机"""
        if not HAS_AHOCORASICK:
            self._ac_automaton = None
            return
        
        if not keywords:
            self._ac_automaton = None
            return
        
        self._ac_automaton = ahocorasick.Automaton()
        
        for keyword, rule_id in keywords:
            if keyword:
                # 存储 (keyword, rule_id) 元组
                self._ac_automaton.add_word(keyword, (keyword, rule_id))
        
        self._ac_automaton.make_automaton()
    
    def reload(self):
        """重新加载规则"""
        self._build_engine()
    
    def filter(self, text: str) -> RuleEngineResult:
        """
        过滤文本
        
        Args:
            text: 待过滤文本
            
        Returns:
            RuleEngineResult: 包含 filter_matched 和 select_matched 区分两种规则
        """
        if not text:
            return RuleEngineResult()
        
        text_lower = text.lower()
        matched_rules: List[MatchedRule] = []
        matched_rule_ids: Set[int] = set()
        categories: Set[str] = set()
        
        # 1. AC自动机匹配关键词
        ac_matches = self._match_with_ac(text_lower)
        for rule_id, matched_text in ac_matches:
            if rule_id not in matched_rule_ids:
                compiled = self._compiled_rules.get(rule_id)
                if compiled:
                    # 获取规则的 purpose
                    purpose = getattr(compiled.rule, 'purpose', 'filter')
                    if hasattr(purpose, 'value'):
                        purpose = purpose.value
                    
                    matched_rules.append(MatchedRule(
                        rule_id=rule_id,
                        rule_name=compiled.rule.name,
                        rule_type=compiled.rule.type,
                        category=compiled.rule.category,
                        purpose=purpose,
                        matched_text=matched_text,
                        confidence=1.0,
                    ))
                    matched_rule_ids.add(rule_id)
                    if compiled.rule.category:
                        categories.add(compiled.rule.category)
        
        # 2. 正则表达式匹配
        regex_matches = self._match_with_regex(text)
        for rule_id, matched_text, confidence in regex_matches:
            if rule_id not in matched_rule_ids:
                compiled = self._compiled_rules.get(rule_id)
                if compiled:
                    purpose = getattr(compiled.rule, 'purpose', 'filter')
                    if hasattr(purpose, 'value'):
                        purpose = purpose.value
                    
                    matched_rules.append(MatchedRule(
                        rule_id=rule_id,
                        rule_name=compiled.rule.name,
                        rule_type=compiled.rule.type,
                        category=compiled.rule.category,
                        purpose=purpose,
                        matched_text=matched_text,
                        confidence=confidence,
                    ))
                    matched_rule_ids.add(rule_id)
                    if compiled.rule.category:
                        categories.add(compiled.rule.category)
        
        # 3. 模式规则匹配
        pattern_matches = self._match_patterns(text, text_lower, matched_rule_ids)
        for rule_id, matched_text, confidence in pattern_matches:
            compiled = self._compiled_rules.get(rule_id)
            if compiled:
                purpose = getattr(compiled.rule, 'purpose', 'filter')
                if hasattr(purpose, 'value'):
                    purpose = purpose.value
                
                matched_rules.append(MatchedRule(
                    rule_id=rule_id,
                    rule_name=compiled.rule.name,
                    rule_type=compiled.rule.type,
                    category=compiled.rule.category,
                    purpose=purpose,
                    matched_text=matched_text,
                    confidence=confidence,
                ))
                if compiled.rule.category:
                    categories.add(compiled.rule.category)
        
        # 区分 filter 和 select 规则
        filter_rules = [r for r in matched_rules if r.purpose == 'filter']
        select_rules = [r for r in matched_rules if r.purpose == 'select']
        
        filter_matched = len(filter_rules) > 0
        select_matched = len(select_rules) > 0
        
        # 计算综合置信度（只针对 filter 规则）
        is_matched = len(matched_rules) > 0
        confidence = 0.0
        if filter_matched:
            # 只计算 filter 规则的置信度
            max_conf = max(m.confidence for m in filter_rules)
            match_bonus = min(0.1 * (len(filter_rules) - 1), 0.2)
            confidence = min(max_conf + match_bonus, 1.0)
        
        return RuleEngineResult(
            is_matched=is_matched,
            confidence=confidence,
            matched_rules=matched_rules,
            categories=list(categories),
            filter_matched=filter_matched,
            select_matched=select_matched,
            filter_rules=filter_rules,
            select_rules=select_rules,
        )
    
    def _match_with_ac(self, text_lower: str) -> List[Tuple[int, str]]:
        """使用AC自动机匹配"""
        matches = []
        
        if self._ac_automaton and HAS_AHOCORASICK:
            try:
                for end_idx, (keyword, rule_id) in self._ac_automaton.iter(text_lower):
                    matches.append((rule_id, keyword))
            except Exception:
                pass
        else:
            # 降级：逐个关键词匹配
            for keyword, rule_ids in self._keyword_to_rule.items():
                if keyword in text_lower:
                    for rule_id in rule_ids:
                        matches.append((rule_id, keyword))
        
        return matches
    
    def _match_with_regex(self, text: str) -> List[Tuple[int, str, float]]:
        """使用正则表达式匹配"""
        matches = []
        
        for rule_id, compiled in self._compiled_rules.items():
            if compiled.rule.type != RuleType.REGEX:
                continue
            
            for pattern in compiled.regex_patterns:
                try:
                    match = self._safe_regex_search(pattern, text)
                    if match:
                        matches.append((rule_id, match.group(0), 1.0))
                        break  # 一个规则只需匹配一次
                except RegexTimeoutError:
                    # 超时，降低置信度但仍记录
                    matches.append((rule_id, "[regex timeout]", 0.5))
                except Exception:
                    pass
        
        return matches
    
    def _safe_regex_search(self, pattern: re.Pattern, text: str, timeout: float = None) -> Optional[re.Match]:
        """
        安全的正则匹配（带超时保护）
        
        注意：Python标准库不支持正则超时，这里用文本长度限制作为替代
        """
        timeout = timeout or self.REGEX_TIMEOUT
        
        # 限制文本长度，避免回溯爆炸
        max_len = 10000
        if len(text) > max_len:
            text = text[:max_len]
        
        try:
            return pattern.search(text)
        except Exception:
            return None
    
    def _match_patterns(
        self, 
        text: str, 
        text_lower: str,
        already_matched: Set[int]
    ) -> List[Tuple[int, str, float]]:
        """
        匹配模式规则（组合逻辑）
        
        支持的模式配置:
        - all: 所有条件都需满足
        - any: 任一条件满足即可
        - count: 满足指定数量的条件
        """
        matches = []
        
        for rule_id, compiled in self._compiled_rules.items():
            if compiled.rule.type != RuleType.PATTERN:
                continue
            if rule_id in already_matched:
                continue
            
            config = compiled.pattern_config
            if not config:
                continue
            
            mode = config.get("mode", "any")
            threshold = config.get("threshold", 1)
            
            hit_count = 0
            matched_texts = []
            
            # 检查关键词
            for kw in compiled.keywords:
                if kw in text_lower:
                    hit_count += 1
                    matched_texts.append(kw)
            
            # 检查正则
            for pattern in compiled.regex_patterns:
                try:
                    match = pattern.search(text)
                    if match:
                        hit_count += 1
                        matched_texts.append(match.group(0))
                except Exception:
                    pass
            
            # 判断是否满足条件
            total_conditions = len(compiled.keywords) + len(compiled.regex_patterns)
            is_match = False
            confidence = 0.0
            
            if mode == "all":
                is_match = hit_count == total_conditions
                confidence = 1.0 if is_match else 0.0
            elif mode == "any":
                is_match = hit_count >= 1
                confidence = min(hit_count / max(total_conditions, 1), 1.0)
            elif mode == "count":
                is_match = hit_count >= threshold
                confidence = min(hit_count / max(threshold, 1), 1.0)
            
            if is_match:
                matches.append((
                    rule_id,
                    ", ".join(matched_texts[:3]),  # 最多显示3个匹配项
                    confidence,
                ))
        
        return matches
    
    def test_rule(self, rule: Rule, text: str) -> RuleEngineResult:
        """
        测试单条规则
        
        Args:
            rule: 规则对象
            text: 测试文本
            
        Returns:
            RuleEngineResult
        """
        # 临时编译规则
        compiled = self._compile_rule(rule)
        text_lower = text.lower()
        
        matched_rules = []
        
        # 关键词匹配
        for kw in compiled.keywords:
            if kw in text_lower:
                matched_rules.append(MatchedRule(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    rule_type=rule.type,
                    category=rule.category,
                    matched_text=kw,
                    confidence=1.0,
                ))
                break
        
        # 正则匹配
        if not matched_rules:
            for pattern in compiled.regex_patterns:
                try:
                    match = pattern.search(text)
                    if match:
                        matched_rules.append(MatchedRule(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            rule_type=rule.type,
                            category=rule.category,
                            matched_text=match.group(0),
                            confidence=1.0,
                        ))
                        break
                except Exception:
                    pass
        
        is_matched = len(matched_rules) > 0
        return RuleEngineResult(
            is_matched=is_matched,
            confidence=1.0 if is_matched else 0.0,
            matched_rules=matched_rules,
            categories=[rule.category] if rule.category and is_matched else [],
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        keyword_count = sum(len(c.keywords) for c in self._compiled_rules.values())
        regex_count = sum(len(c.regex_patterns) for c in self._compiled_rules.values())
        
        return {
            "total_rules": len(self._compiled_rules),
            "keyword_count": keyword_count,
            "regex_count": regex_count,
            "ac_automaton_enabled": self._ac_automaton is not None,
        }
