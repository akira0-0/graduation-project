# -*- coding: utf-8 -*-
# ⚠️  [REDUNDANT - 待审查是否删除]
# 原因：RuleSelector 按 tags/category 从 SQLite 本地库选取规则，
#       现在 SmartRuleMatcher 按场景从 Supabase 动态加载规则，此文件完全冗余。
#       仅被 dynamic_pipeline.py 使用。
#       删除条件：随 dynamic_pipeline.py 一起删除即可。
"""
动态规则选择器
根据查询意图动态选择适用的规则集合
"""
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

from .query_analyzer import QueryIntent, FilterScenario, FilterSeverity
from ..rules.models import Rule, RuleCategory


@dataclass
class RuleSelectionResult:
    """规则选择结果"""
    base_rules: List[Rule] = field(default_factory=list)      # 基础规则（始终应用）
    scenario_rules: List[Rule] = field(default_factory=list)  # 场景规则（根据场景选择）
    extra_rules: List[Rule] = field(default_factory=list)     # 额外规则（根据类别选择）
    custom_rules: List[Rule] = field(default_factory=list)    # 自定义规则（动态生成）
    
    @property
    def all_rules(self) -> List[Rule]:
        """获取所有选中的规则"""
        seen_ids = set()
        all_rules = []
        
        for rule in self.base_rules + self.scenario_rules + self.extra_rules + self.custom_rules:
            if rule.id not in seen_ids:
                seen_ids.add(rule.id)
                all_rules.append(rule)
        
        # 按优先级排序
        return sorted(all_rules, key=lambda r: r.priority, reverse=True)
    
    @property
    def rule_count(self) -> Dict[str, int]:
        """获取各类规则数量"""
        return {
            "base": len(self.base_rules),
            "scenario": len(self.scenario_rules),
            "extra": len(self.extra_rules),
            "custom": len(self.custom_rules),
            "total": len(self.all_rules),
        }
    
    def to_dict(self) -> Dict:
        return {
            "base_rules": [r.name for r in self.base_rules],
            "scenario_rules": [r.name for r in self.scenario_rules],
            "extra_rules": [r.name for r in self.extra_rules],
            "custom_rules": [r.name for r in self.custom_rules],
            "total_count": len(self.all_rules),
        }


class RuleSelector:
    """
    动态规则选择器
    
    根据查询意图选择适用的规则：
    1. 基础规则：始终应用的核心规则
    2. 场景规则：根据场景（电商/新闻/社交等）选择
    3. 额外规则：根据额外关注的类别选择
    4. 自定义规则：根据自定义关键词动态生成
    """
    
    # 基础规则标签（这些规则始终启用）
    BASE_RULE_TAGS = {"base", "core", "common", "基础", "通用"}
    
    # 场景到规则标签的映射
    SCENARIO_RULE_TAGS = {
        FilterScenario.ECOMMERCE: {"ecommerce", "电商", "商品", "购物"},
        FilterScenario.NEWS: {"news", "新闻", "资讯", "媒体"},
        FilterScenario.SOCIAL: {"social", "社交", "评论", "互动"},
        FilterScenario.FINANCE: {"finance", "金融", "理财", "投资"},
        FilterScenario.MEDICAL: {"medical", "医疗", "健康", "药品"},
        FilterScenario.EDUCATION: {"education", "教育", "培训", "学习"},
        FilterScenario.NORMAL: set(),  # 通用场景不加载额外规则
        FilterScenario.CUSTOM: set(),
    }
    
    # 类别到规则类别的映射
    CATEGORY_MAPPING = {
        "ad": RuleCategory.AD,
        "spam": RuleCategory.SPAM,
        "sensitive": RuleCategory.SENSITIVE,
        "profanity": RuleCategory.PROFANITY,
    }
    
    # 严格程度对应的优先级阈值
    SEVERITY_PRIORITY_THRESHOLD = {
        FilterSeverity.RELAXED: 80,   # 宽松：只用高优先级规则
        FilterSeverity.NORMAL: 50,    # 正常：使用中等以上优先级规则
        FilterSeverity.STRICT: 0,     # 严格：使用所有规则
    }
    
    def __init__(self, rule_manager):
        """
        初始化规则选择器
        
        Args:
            rule_manager: 规则管理器实例
        """
        self.rule_manager = rule_manager
        self._rule_cache: Dict[str, List[Rule]] = {}
        self._cache_valid = False
    
    def invalidate_cache(self):
        """使缓存失效"""
        self._cache_valid = False
        self._rule_cache.clear()
    
    def _load_all_rules(self) -> List[Rule]:
        """加载所有启用的规则"""
        if not self._cache_valid or "all" not in self._rule_cache:
            self._rule_cache["all"] = self.rule_manager.list(enabled_only=True)
            self._cache_valid = True
        return self._rule_cache["all"]
    
    def select(self, intent: QueryIntent) -> RuleSelectionResult:
        """
        根据查询意图选择规则
        
        Args:
            intent: 查询意图
            
        Returns:
            RuleSelectionResult: 规则选择结果
        """
        all_rules = self._load_all_rules()
        result = RuleSelectionResult()
        
        # 获取优先级阈值
        priority_threshold = self.SEVERITY_PRIORITY_THRESHOLD.get(
            intent.severity, 50
        )
        
        # 1. 选择基础规则
        result.base_rules = self._select_base_rules(all_rules, priority_threshold)
        
        # 2. 选择场景规则
        result.scenario_rules = self._select_scenario_rules(
            all_rules, intent.scenario, priority_threshold
        )
        
        # 3. 选择额外类别规则
        result.extra_rules = self._select_extra_rules(
            all_rules, intent.extra_categories, priority_threshold
        )
        
        return result
    
    def _select_base_rules(
        self,
        rules: List[Rule],
        priority_threshold: int
    ) -> List[Rule]:
        """选择基础规则"""
        base_rules = []
        
        for rule in rules:
            # 检查优先级
            if rule.priority < priority_threshold:
                continue
            
            # 检查是否是基础规则（通过名称或描述判断）
            is_base = self._is_base_rule(rule)
            
            if is_base:
                base_rules.append(rule)
        
        return base_rules
    
    def _is_base_rule(self, rule: Rule) -> bool:
        """判断是否是基础规则"""
        # 检查名称
        name_lower = rule.name.lower()
        for tag in self.BASE_RULE_TAGS:
            if tag in name_lower:
                return True
        
        # 检查描述
        if rule.description:
            desc_lower = rule.description.lower()
            for tag in self.BASE_RULE_TAGS:
                if tag in desc_lower:
                    return True
        
        # 高优先级规则默认作为基础规则
        if rule.priority >= 90:
            return True
        
        return False
    
    def _select_scenario_rules(
        self,
        rules: List[Rule],
        scenario: FilterScenario,
        priority_threshold: int
    ) -> List[Rule]:
        """选择场景规则"""
        if scenario == FilterScenario.NORMAL:
            return []
        
        scenario_tags = self.SCENARIO_RULE_TAGS.get(scenario, set())
        if not scenario_tags:
            return []
        
        scenario_rules = []
        
        for rule in rules:
            if rule.priority < priority_threshold:
                continue
            
            # 检查规则是否属于该场景
            if self._rule_matches_tags(rule, scenario_tags):
                scenario_rules.append(rule)
        
        return scenario_rules
    
    def _select_extra_rules(
        self,
        rules: List[Rule],
        extra_categories: List[str],
        priority_threshold: int
    ) -> List[Rule]:
        """选择额外类别规则"""
        if not extra_categories:
            return []
        
        # 转换类别
        target_categories = set()
        for cat in extra_categories:
            if cat in self.CATEGORY_MAPPING:
                target_categories.add(self.CATEGORY_MAPPING[cat])
        
        if not target_categories:
            return []
        
        extra_rules = []
        
        for rule in rules:
            if rule.priority < priority_threshold:
                continue
            
            # 检查规则类别
            if rule.category and rule.category in [c.value for c in target_categories]:
                extra_rules.append(rule)
        
        return extra_rules
    
    def _rule_matches_tags(self, rule: Rule, tags: Set[str]) -> bool:
        """检查规则是否匹配标签"""
        name_lower = rule.name.lower()
        desc_lower = (rule.description or "").lower()
        
        for tag in tags:
            if tag in name_lower or tag in desc_lower:
                return True
        
        return False
    
    def get_missing_rule_gaps(
        self,
        intent: QueryIntent,
        selected_rules: RuleSelectionResult
    ) -> Dict[str, List[str]]:
        """
        分析规则缺口
        
        检查自定义关键词是否被现有规则覆盖
        
        Returns:
            Dict: 未覆盖的关键词按类型分组
        """
        gaps = {
            "uncovered_keywords": [],
            "missing_categories": [],
            "suggested_rules": [],
        }
        
        # 获取所有规则的关键词
        all_keywords = set()
        for rule in selected_rules.all_rules:
            # 假设关键词规则的content是逗号分隔的关键词
            if rule.type == "keyword":
                keywords = [k.strip() for k in rule.content.split(",")]
                all_keywords.update(keywords)
        
        # 检查自定义关键词是否被覆盖
        for keyword in intent.custom_keywords:
            if keyword not in all_keywords:
                gaps["uncovered_keywords"].append(keyword)
        
        # 检查额外类别是否有对应规则
        covered_categories = set()
        for rule in selected_rules.all_rules:
            if rule.category:
                covered_categories.add(rule.category)
        
        for cat in intent.extra_categories:
            if cat not in covered_categories:
                gaps["missing_categories"].append(cat)
        
        # 生成建议
        if gaps["uncovered_keywords"]:
            gaps["suggested_rules"].append({
                "type": "keyword",
                "name": f"自定义关键词_{intent.scenario.value}",
                "content": ",".join(gaps["uncovered_keywords"]),
            })
        
        return gaps


# 便捷函数
def select_rules(intent: QueryIntent, rule_manager) -> RuleSelectionResult:
    """选择规则的便捷函数"""
    selector = RuleSelector(rule_manager)
    return selector.select(intent)
