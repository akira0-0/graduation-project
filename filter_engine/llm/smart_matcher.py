# -*- coding: utf-8 -*-
"""
智能规则匹配器（场景感知版）

工作流程：
  1. 场景预检测（规则 + LLM 双重识别）
  2. 按场景分层加载规则库（通用规则 + 场景规则）
  3. LLM 思维链分析：意图提取 → 规则匹配 → 缺口识别 → 补充规则生成
  4. 使用规则引擎对数据执行第二层过滤（场景规则 + 即时补充规则）
  5. 返回结构化结果，供上层调用者决定是否触发 LLM 语义过滤（第三层）
"""
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .client import create_llm_client, BaseLLMClient
from .prompts_smart import SMART_MATCH_SYSTEM, build_smart_match_prompt, SCENARIO_NAMES
from ..rules import RuleManager, Rule
from ..config import settings


# ──────────────────────────────────────────────
# 场景 → 规则名前缀映射
# ──────────────────────────────────────────────
SCENARIO_PREFIX_MAP: Dict[str, str] = {
    "ecommerce": "电商-",
    "travel":    "旅游-",
    "news":      "新闻-",
    "social":    "社交-",
    "finance":   "财经-",
    "medical":   "医疗-",
    "education": "教育-",
    "normal":    "",       # 通用场景不限前缀，但只用 "通用-" 规则
}


# ──────────────────────────────────────────────
# 数据类
# ──────────────────────────────────────────────

@dataclass
class MatchedRuleInfo:
    """匹配到的规则信息"""
    rule_id: int
    rule_name: str
    match_reason: str
    purpose: str = "filter"


@dataclass
class GapRule:
    """LLM 生成的补充规则（填补规则缺口）"""
    name: str
    type: str           # keyword / regex
    content: List[str]  # 关键词或正则列表
    category: str       # spam / ad / sensitive / other
    purpose: str        # filter / select
    description: str = ""
    needs_llm_semantic: bool = False  # 是否还需要 LLM 语义过滤才能覆盖


@dataclass
class SuggestSaveRule:
    """建议保存到规则库的规则"""
    name: str
    type: str
    category: str
    content: List[str]
    reason: str
    purpose: str = "filter"


@dataclass
class ThoughtTrace:
    """LLM 思维链"""
    step_1_extraction: List[str] = field(default_factory=list)
    step_2_match: List[str] = field(default_factory=list)
    step_3_gap_analysis: List[str] = field(default_factory=list)
    step_4_generation: List[str] = field(default_factory=list)


@dataclass
class SmartMatchResult:
    """智能匹配完整结果"""
    success: bool
    query: str

    # 场景分析
    detected_scenario: str = "normal"
    scenario_coverage: str = "sufficient"   # sufficient / partial / missing

    # 思维链
    thought_trace: ThoughtTrace = field(default_factory=ThoughtTrace)

    # 规则层
    matched_rules: List[MatchedRuleInfo] = field(default_factory=list)   # 规则库已有，命中的
    gap_rules: List[GapRule] = field(default_factory=list)               # LLM 补充的缺口规则

    # LLM 语义过滤标记（第三层）
    needs_llm_filter: bool = False
    llm_filter_reason: str = ""

    # 建议保存
    suggest_save: List[SuggestSaveRule] = field(default_factory=list)

    # 执行计划
    execution_plan: Dict[str, str] = field(default_factory=dict)

    # 元信息
    error: Optional[str] = None
    raw_response: Optional[str] = None

    # 兼容旧前端：保留 generated_rules 和 final_rule 字段
    @property
    def generated_rules(self) -> List[Dict]:
        return [
            {"name": r.name, "description": r.description,
             "purpose": r.purpose, "rule": {"op": "contains", "value": r.content}}
            for r in self.gap_rules
        ]

    @property
    def final_rule(self) -> Dict:
        return self.execution_plan

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "query": self.query,
            "detected_scenario": self.detected_scenario,
            "detected_scenario_cn": SCENARIO_NAMES.get(self.detected_scenario, "通用"),
            "scenario_coverage": self.scenario_coverage,
            "thought_trace": {
                "step_1_extraction": self.thought_trace.step_1_extraction,
                "step_2_match": self.thought_trace.step_2_match,
                "step_3_gap_analysis": self.thought_trace.step_3_gap_analysis,
                "step_4_generation": self.thought_trace.step_4_generation,
            },
            "matched_rules": [
                {"rule_id": r.rule_id, "rule_name": r.rule_name,
                 "match_reason": r.match_reason, "purpose": r.purpose}
                for r in self.matched_rules
            ],
            "gap_rules": [
                {"name": r.name, "type": r.type, "content": r.content,
                 "category": r.category, "purpose": r.purpose,
                 "description": r.description, "needs_llm_semantic": r.needs_llm_semantic}
                for r in self.gap_rules
            ],
            # 兼容旧前端字段
            "generated_rules": self.generated_rules,
            "final_rule": self.final_rule,
            "needs_llm_filter": self.needs_llm_filter,
            "llm_filter_reason": self.llm_filter_reason,
            "suggest_save": [
                {"name": r.name, "type": r.type, "category": r.category,
                 "content": r.content, "purpose": r.purpose, "reason": r.reason}
                for r in self.suggest_save
            ],
            "execution_plan": self.execution_plan,
            "error": self.error,
        }


# ──────────────────────────────────────────────
# 智能匹配器
# ──────────────────────────────────────────────

class SmartRuleMatcher:
    """
    智能规则匹配器（场景感知版）

    三层过滤架构：
      Layer-1  基础规则引擎：通用规则（外部调用，本类不负责）
      Layer-2  场景规则引擎：本类负责识别场景 + 匹配/补充规则
      Layer-3  LLM 语义过滤：本类标记 needs_llm_filter，由上层决定是否调用
    """

    def __init__(
        self,
        rule_manager: Optional[RuleManager] = None,
        llm_client: Optional[BaseLLMClient] = None,
        db_path: Optional[str] = None,
    ):
        self.db_path = db_path or settings.DATABASE_PATH
        self.rule_manager = rule_manager or RuleManager(self.db_path)
        self.llm_client = llm_client or create_llm_client()

    # ──────────────────────────────────────────
    # 场景检测（纯 LLM）
    # ──────────────────────────────────────────

    async def detect_scenario_llm(self, query: str) -> str:
        """
        使用 LLM 进行场景识别（语义理解，准确率高）
        返回标准英文场景名：normal/ecommerce/travel/news/social/finance/medical/education
        """
        from .prompts_smart import SCENARIO_DETECT_PROMPT
        prompt = SCENARIO_DETECT_PROMPT.replace("{{query}}", query)
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await self.llm_client.chat(messages=messages, temperature=0.0, max_tokens=10)
            scenario = response.content.strip().lower()
            valid = {"normal", "ecommerce", "travel", "news", "social", "finance", "medical", "education"}
            return scenario if scenario in valid else "normal"
        except Exception as e:
            print(f"⚠️  LLM场景识别失败，使用默认场景 normal: {e}")
            return "normal"



    def _load_rules_for_scenario(self, scenario: str) -> Tuple[List[Rule], List[Rule]]:
        """
        按场景加载规则
        Returns:
            (base_rules, scene_rules)  —— 通用规则 + 场景专属规则
        """
        base_rules = self.rule_manager.list(enabled_only=True, name_prefix="通用-")
        prefix = SCENARIO_PREFIX_MAP.get(scenario, "")
        scene_rules = self.rule_manager.list(enabled_only=True, name_prefix=prefix) if prefix else []
        return base_rules, scene_rules

    def _rules_to_summary(self, rules: List[Rule]) -> List[Dict[str, Any]]:
        """规则列表转为摘要字典（含关键词内容，帮助 LLM 语义匹配）"""
        result = []
        for r in rules:
            # 解析 content 字段，展示实际关键词/正则
            content_preview = ""
            try:
                raw = r.content or ""
                parsed = json.loads(raw) if raw else []
                if isinstance(parsed, list):
                    # 最多展示前 8 个词，避免提示词过长
                    preview_items = [str(x) for x in parsed[:8] if x]
                    content_preview = "、".join(preview_items)
                    if len(parsed) > 8:
                        content_preview += f"…（共{len(parsed)}个）"
                elif isinstance(parsed, dict):
                    content_preview = json.dumps(parsed, ensure_ascii=False)[:80]
            except Exception:
                content_preview = str(r.content or "")[:80]

            result.append({
                "id": r.id,
                "name": r.name,
                "type": r.type.value if hasattr(r.type, "value") else str(r.type),
                "purpose": r.purpose.value if hasattr(r.purpose, "value") else str(r.purpose),
                "category": r.category.value if r.category and hasattr(r.category, "value") else (str(r.category) if r.category else "other"),
                "description": r.description or "",
                "content_preview": content_preview,  # 实际词/正则内容，供 LLM 语义匹配
            })
        return result

    # ──────────────────────────────────────────
    # LLM 调用与解析
    # ──────────────────────────────────────────

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON"""
        response = response.strip()
        # 去掉 markdown 代码块
        response = re.sub(r"^```[a-z]*\n?", "", response)
        response = re.sub(r"\n?```$", "", response)
        # 找到最外层 JSON 对象
        match = re.search(r"\{[\s\S]*\}", response)
        if match:
            response = match.group()
        return json.loads(response)

    def _build_result(self, query: str, scenario: str, data: Dict, raw: str) -> SmartMatchResult:
        """将 LLM JSON 数据组装为 SmartMatchResult"""
        tt_data = data.get("thought_trace", {})
        thought_trace = ThoughtTrace(
            step_1_extraction=tt_data.get("step_1_extraction", []),
            step_2_match=tt_data.get("step_2_match", []),
            step_3_gap_analysis=tt_data.get("step_3_gap_analysis", []),
            step_4_generation=tt_data.get("step_4_generation", []),
        )

        matched_rules = [
            MatchedRuleInfo(
                rule_id=item.get("rule_id", 0),
                rule_name=item.get("rule_name", ""),
                match_reason=item.get("match_reason", ""),
                purpose=item.get("purpose", "filter"),
            )
            for item in data.get("matched_rules", [])
        ]

        gap_rules = []
        for item in data.get("gap_rules", []):
            raw_content = item.get("content", [])
            # content 可能已经是 list，也可能是 JSON 字符串
            if isinstance(raw_content, str):
                try:
                    raw_content = json.loads(raw_content)
                except Exception:
                    raw_content = [raw_content]
            gap_rules.append(GapRule(
                name=item.get("name", ""),
                type=item.get("type", "keyword"),
                content=raw_content if isinstance(raw_content, list) else [str(raw_content)],
                category=item.get("category", "other"),
                purpose=item.get("purpose", "filter"),
                description=item.get("description", ""),
                needs_llm_semantic=item.get("needs_llm_semantic", False),
            ))

        suggest_save = []
        for item in data.get("suggest_save", []):
            raw_content = item.get("content", item.get("rule", {}).get("value", ""))
            if isinstance(raw_content, str):
                try:
                    raw_content = json.loads(raw_content)
                except Exception:
                    raw_content = [raw_content]
            elif isinstance(raw_content, dict):
                raw_content = [str(raw_content.get("value", ""))]
            suggest_save.append(SuggestSaveRule(
                name=item.get("name", ""),
                type=item.get("type", "keyword"),
                category=item.get("category", "other"),
                content=raw_content if isinstance(raw_content, list) else [str(raw_content)],
                purpose=item.get("purpose", "filter"),
                reason=item.get("reason", ""),
            ))

        detected = data.get("detected_scenario", scenario)
        coverage = data.get("scenario_coverage", "sufficient")
        needs_llm = data.get("needs_llm_filter", bool(gap_rules and any(r.needs_llm_semantic for r in gap_rules)))
        llm_reason = data.get("llm_filter_reason", "")
        execution_plan = data.get("execution_plan", {})

        return SmartMatchResult(
            success=True,
            query=query,
            detected_scenario=detected,
            scenario_coverage=coverage,
            thought_trace=thought_trace,
            matched_rules=matched_rules,
            gap_rules=gap_rules,
            needs_llm_filter=needs_llm,
            llm_filter_reason=llm_reason,
            suggest_save=suggest_save,
            execution_plan=execution_plan,
            raw_response=raw,
        )

    def _make_messages(self, query: str, scenario: str) -> List[Dict[str, str]]:
        """构建 LLM 消息列表"""
        base_rules, scene_rules = self._load_rules_for_scenario(scenario)
        prompt = build_smart_match_prompt(
            query=query,
            existing_rules=[],           # 兼容参数，不再直接使用
            detected_scenario=scenario,
            scene_rules=self._rules_to_summary(scene_rules),
        )
        return [
            {"role": "system", "content": SMART_MATCH_SYSTEM},
            {"role": "user", "content": prompt},
        ]

    # ──────────────────────────────────────────
    # 公开接口
    # ──────────────────────────────────────────

    async def match(self, query: str, force_scenario: Optional[str] = None) -> SmartMatchResult:
        """
        异步智能匹配（Layer-2 核心入口）

        Args:
            query: 用户自然语言查询
            force_scenario: 强制指定场景（可选），跳过自动识别
        """
        raw_response = ""
        try:
            scenario = force_scenario if force_scenario else await self.detect_scenario_llm(query)
            messages = self._make_messages(query, scenario)
            response = await self.llm_client.chat(messages=messages, temperature=0.1, max_tokens=3000)
            raw_response = response.content
            data = self._parse_llm_response(raw_response)
            return self._build_result(query, scenario, data, raw_response)
        except json.JSONDecodeError as e:
            return self._error_result(query, f"JSON解析失败: {e}", raw_response)
        except Exception as e:
            return self._error_result(query, f"匹配失败: {e}", raw_response)

    def match_sync(self, query: str, force_scenario: Optional[str] = None) -> SmartMatchResult:
        """同步智能匹配"""
        import asyncio
        coro = self.match(query, force_scenario=force_scenario)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在已有事件循环中（如Jupyter）
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.match(query, force_scenario=force_scenario))
                    return future.result()
            return loop.run_until_complete(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    def _error_result(self, query: str, error: str, raw: str = "") -> SmartMatchResult:
        return SmartMatchResult(
            success=False, query=query, error=error, raw_response=raw
        )

    # ──────────────────────────────────────────
    # 辅助：将缺口规则转换为 RuleCreate 并保存
    # ──────────────────────────────────────────

    def save_suggested_rules(self, suggest_save) -> List[int]:
        """
        保存建议规则到数据库

        Args:
            suggest_save: List[SuggestSaveRule] 或 List[dict]
        Returns:
            保存成功的规则 ID 列表
        """
        from ..rules.models import RuleCreate, RuleType, RuleCategory, RulePurpose

        saved_ids = []
        for item in suggest_save:
            # 兼容 dict 和 dataclass
            if isinstance(item, dict):
                name = item.get("name", "未命名")
                rtype = item.get("type", "keyword")
                category = item.get("category", "other")
                purpose_str = item.get("purpose", "filter")
                raw_content = item.get("content", item.get("rule", {}).get("value", ""))
                reason = item.get("reason", "")
                description = item.get("description", "")
            else:
                name = item.name
                rtype = item.type
                category = item.category
                purpose_str = item.purpose
                raw_content = item.content if hasattr(item, "content") else (item.rule if hasattr(item, "rule") else [])
                reason = item.reason if hasattr(item, "reason") else ""
                description = getattr(item, "description", "")

            # 规范化 content → JSON 字符串
            if isinstance(raw_content, list):
                content_str = json.dumps(raw_content, ensure_ascii=False)
            elif isinstance(raw_content, str):
                try:
                    json.loads(raw_content)
                    content_str = raw_content
                except Exception:
                    content_str = json.dumps([raw_content], ensure_ascii=False)
            elif isinstance(raw_content, dict):
                val = raw_content.get("value", "")
                content_str = json.dumps([val] if val else [""], ensure_ascii=False)
            else:
                content_str = '[""]'

            try:
                purpose = RulePurpose.SELECT if purpose_str == "select" else RulePurpose.FILTER
                cat_val = category if category in ["spam", "ad", "sensitive", "profanity", "other"] else "other"
                rule_create = RuleCreate(
                    name=name,
                    type=RuleType(rtype if rtype in ["keyword", "regex", "pattern"] else "keyword"),
                    content=content_str,
                    category=RuleCategory(cat_val),
                    purpose=purpose,
                    priority=50,
                    enabled=True,
                    description=description or (f"[{purpose_str}] {reason}" if reason else f"LLM自动生成"),
                )
                rule = self.rule_manager.create(rule_create)
                saved_ids.append(rule.id)
            except Exception as e:
                print(f"保存规则失败 [{name}]: {e}")

        return saved_ids

    # ──────────────────────────────────────────
    # 辅助：批量内容过滤（用于 API 层）
    # ──────────────────────────────────────────

    def apply_gap_rules_to_content(
        self,
        contents: List[str],
        gap_rules: List[GapRule],
    ) -> List[Dict[str, Any]]:
        """
        将 LLM 生成的缺口规则即时应用到内容列表（无需写库）

        Returns:
            List[{"content": str, "matched": bool, "rule": str|None, "purpose": str|None}]
        """
        results = []
        for text in contents:
            matched = False
            matched_name = None
            matched_purpose = None
            text_lower = text.lower()

            for gap in gap_rules:
                hit = False
                if gap.type == "keyword":
                    hit = any(str(kw).lower() in text_lower for kw in gap.content if kw)
                elif gap.type == "regex":
                    for pat in gap.content:
                        try:
                            if re.search(pat, text, re.IGNORECASE):
                                hit = True
                                break
                        except re.error:
                            pass
                if hit:
                    matched = True
                    matched_name = gap.name
                    matched_purpose = gap.purpose
                    break

            results.append({
                "content": text,
                "matched": matched,
                "rule": matched_name,
                "purpose": matched_purpose,
            })
        return results

