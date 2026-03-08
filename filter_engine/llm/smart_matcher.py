# -*- coding: utf-8 -*-
"""
智能规则匹配器
使用LLM理解用户意图，匹配现有规则，生成缺失规则
"""
import json
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from .client import create_llm_client, BaseLLMClient
from .prompts_smart import SMART_MATCH_SYSTEM, build_smart_match_prompt
from ..rules import RuleManager, Rule
from ..config import settings


@dataclass
class MatchedRuleInfo:
    """匹配到的规则信息"""
    rule_id: int
    rule_name: str
    match_reason: str
    purpose: str = "filter"  # filter(过滤/删除) 或 select(筛选/保留)


@dataclass
class GeneratedRuleInfo:
    """生成的规则信息"""
    name: str
    description: str
    rule: Dict[str, Any]  # {"field": "xx", "op": "xx", "value": "xx"}
    purpose: str = "select"  # filter(过滤/删除) 或 select(筛选/保留)


@dataclass
class SuggestSaveRule:
    """建议保存的规则"""
    name: str
    type: str  # keyword, regex, pattern
    category: str  # spam, ad, other
    rule: Dict[str, Any]
    reason: str
    purpose: str = "select"  # filter(过滤/删除) 或 select(筛选/保留)


@dataclass
class ThoughtTrace:
    """思维链追踪"""
    step_1_extraction: List[str] = field(default_factory=list)
    step_2_match: List[str] = field(default_factory=list)
    step_3_gap_analysis: List[str] = field(default_factory=list)
    step_4_generation: List[str] = field(default_factory=list)


@dataclass
class SmartMatchResult:
    """智能匹配结果"""
    success: bool
    query: str
    thought_trace: ThoughtTrace
    matched_rules: List[MatchedRuleInfo]
    generated_rules: List[GeneratedRuleInfo]
    final_rule: Dict[str, Any]
    suggest_save: List[SuggestSaveRule]
    execution_plan: Dict[str, str] = None  # 执行计划
    error: Optional[str] = None
    raw_response: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "query": self.query,
            "thought_trace": {
                "step_1_extraction": self.thought_trace.step_1_extraction,
                "step_2_match": self.thought_trace.step_2_match,
                "step_3_gap_analysis": self.thought_trace.step_3_gap_analysis,
                "step_4_generation": self.thought_trace.step_4_generation,
            },
            "matched_rules": [
                {"rule_id": r.rule_id, "rule_name": r.rule_name, "match_reason": r.match_reason, "purpose": r.purpose}
                for r in self.matched_rules
            ],
            "generated_rules": [
                {"name": r.name, "description": r.description, "rule": r.rule, "purpose": r.purpose}
                for r in self.generated_rules
            ],
            "final_rule": self.final_rule,
            "suggest_save": [
                {"name": r.name, "type": r.type, "category": r.category, "rule": r.rule, "reason": r.reason, "purpose": r.purpose}
                for r in self.suggest_save
            ],
            "execution_plan": self.execution_plan or {},
            "error": self.error,
        }


class SmartRuleMatcher:
    """
    智能规则匹配器
    
    功能：
    1. 解析用户自然语言查询
    2. 匹配现有规则库
    3. 识别规则缺口
    4. 生成缺失规则
    5. 组合最终规则
    """
    
    def __init__(
        self,
        rule_manager: Optional[RuleManager] = None,
        llm_client: Optional[BaseLLMClient] = None,
        db_path: Optional[str] = None,
    ):
        """
        初始化智能匹配器
        
        Args:
            rule_manager: 规则管理器
            llm_client: LLM客户端
            db_path: 数据库路径
        """
        self.db_path = db_path or settings.DATABASE_PATH
        self.rule_manager = rule_manager or RuleManager(self.db_path)
        self.llm_client = llm_client or create_llm_client()
    
    def _get_existing_rules_summary(self) -> List[Dict[str, Any]]:
        """获取现有规则摘要"""
        rules = self.rule_manager.list(enabled_only=True)
        return [
            {
                "id": rule.id,
                "name": rule.name,
                "type": rule.type.value if hasattr(rule.type, 'value') else str(rule.type),
                "category": rule.category.value if rule.category and hasattr(rule.category, 'value') else str(rule.category) if rule.category else "other",
                "description": rule.description or "无描述",
            }
            for rule in rules
        ]
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        # 尝试提取JSON
        response = response.strip()
        
        # 移除可能的markdown代码块标记
        if response.startswith("```"):
            lines = response.split("\n")
            # 找到第一个{和最后一个}
            start_idx = None
            end_idx = None
            for i, line in enumerate(lines):
                if "{" in line and start_idx is None:
                    start_idx = i
                if "}" in line:
                    end_idx = i
            if start_idx is not None and end_idx is not None:
                response = "\n".join(lines[start_idx:end_idx + 1])
        
        # 尝试找到JSON对象
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            response = match.group()
        
        return json.loads(response)
    
    def _build_result_from_json(self, query: str, data: Dict[str, Any], raw_response: str) -> SmartMatchResult:
        """从JSON构建结果"""
        # 解析思维链
        thought_trace_data = data.get("thought_trace", {})
        thought_trace = ThoughtTrace(
            step_1_extraction=thought_trace_data.get("step_1_extraction", []),
            step_2_match=thought_trace_data.get("step_2_match", []),
            step_3_gap_analysis=thought_trace_data.get("step_3_gap_analysis", []),
            step_4_generation=thought_trace_data.get("step_4_generation", []),
        )
        
        # 解析匹配的规则
        matched_rules = []
        for item in data.get("matched_rules", []):
            matched_rules.append(MatchedRuleInfo(
                rule_id=item.get("rule_id", 0),
                rule_name=item.get("rule_name", ""),
                match_reason=item.get("match_reason", ""),
                purpose=item.get("purpose", "filter"),
            ))
        
        # 解析生成的规则
        generated_rules = []
        for item in data.get("generated_rules", []):
            generated_rules.append(GeneratedRuleInfo(
                name=item.get("name", ""),
                description=item.get("description", ""),
                rule=item.get("rule", {}),
                purpose=item.get("purpose", "select"),
            ))
        
        # 解析建议保存的规则
        suggest_save = []
        for item in data.get("suggest_save", []):
            suggest_save.append(SuggestSaveRule(
                name=item.get("name", ""),
                type=item.get("type", "keyword"),
                category=item.get("category", "other"),
                rule=item.get("rule", {}),
                reason=item.get("reason", ""),
                purpose=item.get("purpose", "select"),
            ))
        
        # 解析执行计划
        execution_plan = data.get("execution_plan", {})
        
        return SmartMatchResult(
            success=True,
            query=query,
            thought_trace=thought_trace,
            matched_rules=matched_rules,
            generated_rules=generated_rules,
            final_rule=data.get("final_rule", {}),
            suggest_save=suggest_save,
            execution_plan=execution_plan,
            raw_response=raw_response,
        )
    
    def match_sync(self, query: str) -> SmartMatchResult:
        """
        同步执行智能匹配
        
        Args:
            query: 用户自然语言查询
            
        Returns:
            SmartMatchResult: 匹配结果
        """
        try:
            # 获取现有规则
            existing_rules = self._get_existing_rules_summary()
            
            # 构建提示词
            prompt = build_smart_match_prompt(query, existing_rules)
            
            # 调用LLM
            messages = [
                {"role": "system", "content": SMART_MATCH_SYSTEM},
                {"role": "user", "content": prompt},
            ]
            
            response = self.llm_client.chat_sync(
                messages=messages,
                temperature=0.1,
                max_tokens=2000,
            )
            
            raw_response = response.content
            
            # 解析响应
            data = self._parse_llm_response(raw_response)
            
            # 构建结果
            return self._build_result_from_json(query, data, raw_response)
            
        except json.JSONDecodeError as e:
            return SmartMatchResult(
                success=False,
                query=query,
                thought_trace=ThoughtTrace(),
                matched_rules=[],
                generated_rules=[],
                final_rule={},
                suggest_save=[],
                error=f"JSON解析失败: {str(e)}",
                raw_response=raw_response if 'raw_response' in locals() else None,
            )
        except Exception as e:
            return SmartMatchResult(
                success=False,
                query=query,
                thought_trace=ThoughtTrace(),
                matched_rules=[],
                generated_rules=[],
                final_rule={},
                suggest_save=[],
                error=f"匹配失败: {str(e)}",
            )
    
    async def match(self, query: str) -> SmartMatchResult:
        """
        异步执行智能匹配
        
        Args:
            query: 用户自然语言查询
            
        Returns:
            SmartMatchResult: 匹配结果
        """
        try:
            # 获取现有规则
            existing_rules = self._get_existing_rules_summary()
            
            # 构建提示词
            prompt = build_smart_match_prompt(query, existing_rules)
            
            # 调用LLM
            messages = [
                {"role": "system", "content": SMART_MATCH_SYSTEM},
                {"role": "user", "content": prompt},
            ]
            
            response = await self.llm_client.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=2000,
            )
            
            raw_response = response.content
            
            # 解析响应
            data = self._parse_llm_response(raw_response)
            
            # 构建结果
            return self._build_result_from_json(query, data, raw_response)
            
        except json.JSONDecodeError as e:
            return SmartMatchResult(
                success=False,
                query=query,
                thought_trace=ThoughtTrace(),
                matched_rules=[],
                generated_rules=[],
                final_rule={},
                suggest_save=[],
                error=f"JSON解析失败: {str(e)}",
                raw_response=raw_response if 'raw_response' in locals() else None,
            )
        except Exception as e:
            return SmartMatchResult(
                success=False,
                query=query,
                thought_trace=ThoughtTrace(),
                matched_rules=[],
                generated_rules=[],
                final_rule={},
                suggest_save=[],
                error=f"匹配失败: {str(e)}",
            )
    
    def save_suggested_rules(self, suggest_save: List[SuggestSaveRule]) -> List[int]:
        """
        保存建议的规则到数据库
        
        Args:
            suggest_save: 建议保存的规则列表
            
        Returns:
            保存成功的规则ID列表
        """
        saved_ids = []
        
        for item in suggest_save:
            try:
                # 转换规则内容为JSON字符串
                if item.rule.get("op") == "contains":
                    # 关键词规则
                    content = json.dumps([item.rule.get("value", "")], ensure_ascii=False)
                    rule_type = "keyword"
                elif item.rule.get("op") == "regex":
                    # 正则规则
                    content = json.dumps([item.rule.get("value", "")], ensure_ascii=False)
                    rule_type = "regex"
                else:
                    # 模式规则
                    content = json.dumps(item.rule, ensure_ascii=False)
                    rule_type = "pattern"
                
                from ..rules.models import RuleCreate, RuleType, RuleCategory, RulePurpose
                
                # 根据 purpose 确定规则用途
                purpose = RulePurpose.SELECT if item.purpose == "select" else RulePurpose.FILTER
                
                rule_create = RuleCreate(
                    name=item.name,
                    type=RuleType(rule_type),
                    content=content,
                    category=RuleCategory(item.category) if item.category in ["spam", "ad", "sensitive", "profanity", "other"] else RuleCategory.OTHER,
                    purpose=purpose,
                    priority=50,
                    enabled=True,
                    description=f"[{item.purpose}] {item.reason}" if item.reason else f"[{item.purpose}] LLM自动生成",
                )
                
                rule = self.rule_manager.create(rule_create)
                saved_ids.append(rule.id)
                
            except Exception as e:
                print(f"保存规则失败 [{item.name}]: {e}")
                continue
        
        return saved_ids
