# -*- coding: utf-8 -*-
"""
协同决策引擎
融合规则引擎和LLM结果，输出最终判断
"""
from typing import Optional, Dict, Any, List

from ..config import settings
from ..rules.models import RuleEngineResult, LLMResult, FilterResult, MatchedRule


class DecisionEngine:
    """
    协同决策引擎
    
    决策策略:
    1. 规则高置信命中 → 直接判定
    2. 规则低置信/疑似 → 结合LLM判断
    3. 规则未命中 → 依赖LLM或判定为正常
    4. 规则与LLM冲突 → 加权决策
    """
    
    def __init__(
        self,
        spam_threshold: float = None,
        suspicious_threshold: float = None,
        llm_weight: float = None,
        rule_weight: float = None,
    ):
        """
        初始化决策引擎
        
        Args:
            spam_threshold: 垃圾信息判定阈值
            suspicious_threshold: 疑似垃圾阈值
            llm_weight: LLM判断权重
            rule_weight: 规则判断权重
        """
        self.spam_threshold = spam_threshold or settings.SPAM_THRESHOLD
        self.suspicious_threshold = suspicious_threshold or settings.SUSPICIOUS_THRESHOLD
        self.llm_weight = llm_weight or settings.LLM_WEIGHT
        self.rule_weight = rule_weight or settings.RULE_WEIGHT
        
        # 确保权重和为1
        total_weight = self.llm_weight + self.rule_weight
        if total_weight > 0:
            self.llm_weight /= total_weight
            self.rule_weight /= total_weight
    
    def decide(
        self,
        rule_result: Optional[RuleEngineResult] = None,
        llm_result: Optional[LLMResult] = None,
    ) -> Dict[str, Any]:
        """
        综合决策
        
        Args:
            rule_result: 规则引擎结果
            llm_result: LLM结果
            
        Returns:
            决策结果字典
        """
        # 情况1: 只有规则结果
        if rule_result and not llm_result:
            return self._decide_rule_only(rule_result)
        
        # 情况2: 只有LLM结果
        if llm_result and not rule_result:
            return self._decide_llm_only(llm_result)
        
        # 情况3: 两者都有
        if rule_result and llm_result:
            return self._decide_combined(rule_result, llm_result)
        
        # 情况4: 都没有
        return {
            "is_spam": False,
            "confidence": 0.0,
            "matched_rules": [],
            "category": None,
            "source": "none",
        }
    
    def _decide_rule_only(self, rule_result: RuleEngineResult) -> Dict[str, Any]:
        """只有规则结果时的决策
        
        根据规则的 purpose 区分：
        - filter 规则命中 → is_spam = True（需要过滤掉）
        - select 规则命中 → is_spam = False（需要保留）
        """
        # 使用 filter_matched 判断是否命中过滤规则
        is_filter_matched = getattr(rule_result, 'filter_matched', rule_result.is_matched)
        is_select_matched = getattr(rule_result, 'select_matched', False)
        
        # 只有 filter 规则命中才判定为垃圾
        is_spam = is_filter_matched and rule_result.confidence >= self.spam_threshold
        
        # 获取匹配规则列表
        filter_rules = getattr(rule_result, 'filter_rules', [])
        select_rules = getattr(rule_result, 'select_rules', [])
        all_matched = [m.rule_name for m in rule_result.matched_rules]
        
        return {
            "is_spam": is_spam,
            "confidence": rule_result.confidence,
            "matched_rules": all_matched,
            "filter_matched_rules": [m.rule_name for m in filter_rules],
            "select_matched_rules": [m.rule_name for m in select_rules],
            "is_filter_matched": is_filter_matched,
            "is_select_matched": is_select_matched,
            "category": rule_result.categories[0] if rule_result.categories else None,
            "source": "rule",
        }
    
    def _decide_llm_only(self, llm_result: LLMResult) -> Dict[str, Any]:
        """只有LLM结果时的决策"""
        is_spam = llm_result.is_spam and llm_result.confidence >= self.spam_threshold
        
        return {
            "is_spam": is_spam,
            "confidence": llm_result.confidence,
            "matched_rules": [],
            "llm_reason": llm_result.reason,
            "category": llm_result.category,
            "source": "llm",
        }
    
    def _decide_combined(
        self,
        rule_result: RuleEngineResult,
        llm_result: LLMResult,
    ) -> Dict[str, Any]:
        """
        规则与LLM结合决策
        
        策略:
        1. filter规则高置信(>=0.9) → 以规则为准，判定为垃圾
        2. 两者一致 → 提高置信度
        3. 两者冲突 → 加权决策，偏向LLM
        
        注意：只有 filter 规则命中才可能判定为垃圾
        """
        # 使用 filter_matched 判断规则是否检测到垃圾
        is_filter_matched = getattr(rule_result, 'filter_matched', rule_result.is_matched)
        is_select_matched = getattr(rule_result, 'select_matched', False)
        
        rule_is_spam = is_filter_matched  # 只有 filter 规则命中才算垃圾
        llm_is_spam = llm_result.is_spam
        
        rule_conf = rule_result.confidence if is_filter_matched else 0.0
        llm_conf = llm_result.confidence
        
        # 过滤规则高置信命中，直接采用
        if is_filter_matched and rule_conf >= 0.9:
            return {
                "is_spam": True,
                "confidence": rule_conf,
                "matched_rules": [m.rule_name for m in rule_result.matched_rules],
                "llm_reason": llm_result.reason,
                "category": rule_result.categories[0] if rule_result.categories else llm_result.category,
                "source": "rule_high_confidence",
            }
        
        # 两者一致
        if rule_is_spam == llm_is_spam:
            # 取较高置信度，并给予一致性加成
            combined_conf = max(rule_conf, llm_conf)
            combined_conf = min(combined_conf + 0.1, 1.0)  # 一致性加成
            
            is_spam = rule_is_spam and combined_conf >= self.spam_threshold
            
            return {
                "is_spam": is_spam,
                "confidence": combined_conf,
                "matched_rules": [m.rule_name for m in rule_result.matched_rules],
                "llm_reason": llm_result.reason,
                "category": rule_result.categories[0] if rule_result.categories else llm_result.category,
                "source": "combined_agree",
            }
        
        # 两者冲突，加权决策
        # 将布尔值转换为分数
        rule_score = rule_conf if rule_is_spam else (1 - rule_conf)
        llm_score = llm_conf if llm_is_spam else (1 - llm_conf)
        
        # 加权平均
        combined_score = (
            rule_score * self.rule_weight +
            llm_score * self.llm_weight
        )
        
        # 判断最终结果
        # 如果加权分数高，偏向认为是垃圾
        # 需要考虑原始判断方向
        if llm_is_spam:
            # LLM认为是垃圾，规则认为不是
            is_spam = combined_score >= self.spam_threshold
            confidence = combined_score
        else:
            # 规则认为是垃圾，LLM认为不是
            is_spam = combined_score >= self.spam_threshold and rule_conf >= 0.7
            confidence = combined_score * 0.8  # 冲突时降低置信度
        
        return {
            "is_spam": is_spam,
            "confidence": confidence,
            "matched_rules": [m.rule_name for m in rule_result.matched_rules],
            "llm_reason": llm_result.reason,
            "category": llm_result.category if llm_is_spam else (
                rule_result.categories[0] if rule_result.categories else None
            ),
            "source": "combined_conflict",
        }
    
    def should_use_llm(self, rule_result: RuleEngineResult) -> bool:
        """
        判断是否需要调用LLM
        
        场景:
        1. 规则未命中
        2. 规则命中但置信度在疑似区间
        3. 命中低优先级规则
        """
        if not rule_result.is_matched:
            return True  # 规则未命中，建议LLM复核
        
        if rule_result.confidence < self.spam_threshold:
            return True  # 低置信度，需要LLM确认
        
        if self.suspicious_threshold <= rule_result.confidence < self.spam_threshold:
            return True  # 疑似区间，需要LLM确认
        
        return False  # 高置信命中，不需要LLM
    
    def explain(
        self,
        rule_result: Optional[RuleEngineResult],
        llm_result: Optional[LLMResult],
        decision: Dict[str, Any],
    ) -> str:
        """
        生成决策解释
        
        Returns:
            人类可读的决策解释
        """
        parts = []
        
        if decision["is_spam"]:
            parts.append(f"判定为垃圾信息（置信度: {decision['confidence']:.0%}）")
        else:
            parts.append(f"判定为正常内容（置信度: {1-decision['confidence']:.0%}）")
        
        source = decision.get("source", "unknown")
        if source == "rule":
            parts.append("依据: 规则引擎判断")
        elif source == "llm":
            parts.append("依据: LLM语义分析")
        elif source == "rule_high_confidence":
            parts.append("依据: 规则高置信命中")
        elif source == "combined_agree":
            parts.append("依据: 规则与LLM一致")
        elif source == "combined_conflict":
            parts.append("依据: 规则与LLM加权决策")
        
        if decision.get("matched_rules"):
            rules = ", ".join(decision["matched_rules"][:3])
            parts.append(f"命中规则: {rules}")
        
        if decision.get("llm_reason"):
            parts.append(f"LLM理由: {decision['llm_reason']}")
        
        if decision.get("category"):
            parts.append(f"分类: {decision['category']}")
        
        return " | ".join(parts)
