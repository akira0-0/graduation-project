# -*- coding: utf-8 -*-
"""
LLM规则生成器
使用大模型自动生成过滤规则
"""
import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from ..rules.models import RuleCreate, RuleType, RuleCategory


@dataclass
class GapAnalysis:
    """规则缺口分析结果"""
    uncovered_keywords: List[str] = field(default_factory=list)
    uncovered_patterns: List[str] = field(default_factory=list)
    missing_categories: List[str] = field(default_factory=list)
    text_samples: List[str] = field(default_factory=list)  # 未被过滤的文本样本
    analysis_reason: str = ""
    
    def has_gaps(self) -> bool:
        return bool(
            self.uncovered_keywords or 
            self.uncovered_patterns or 
            self.missing_categories or
            self.text_samples
        )
    
    def to_dict(self) -> Dict:
        return {
            "uncovered_keywords": self.uncovered_keywords,
            "uncovered_patterns": self.uncovered_patterns,
            "missing_categories": self.missing_categories,
            "text_samples": self.text_samples,
            "analysis_reason": self.analysis_reason,
        }


@dataclass
class GeneratedRule:
    """生成的规则"""
    rule: RuleCreate
    confidence: float  # 置信度 0-1
    reasoning: str     # 生成理由
    test_cases: List[Dict[str, Any]] = field(default_factory=list)  # 测试用例
    
    def to_dict(self) -> Dict:
        return {
            "rule": {
                "name": self.rule.name,
                "type": self.rule.type.value if hasattr(self.rule.type, 'value') else self.rule.type,
                "content": self.rule.content,
                "category": self.rule.category.value if self.rule.category and hasattr(self.rule.category, 'value') else self.rule.category,
                "priority": self.rule.priority,
                "description": self.rule.description,
            },
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "test_cases": self.test_cases,
        }


# LLM提示词模板
RULE_GENERATION_SYSTEM_PROMPT = """你是一个专业的内容过滤规则专家。你的任务是根据给定的文本样本和需求，生成有效的过滤规则。

规则类型说明：
1. keyword（关键词）：用逗号分隔的关键词列表，匹配包含这些词的文本
2. regex（正则表达式）：Python正则表达式，用于匹配特定模式
3. pattern（模式）：复合模式，支持更复杂的匹配逻辑

规则类别说明：
- spam: 垃圾信息（刷屏、无意义内容）
- ad: 广告（推销、引流、联系方式）
- sensitive: 敏感内容（政治、违规）
- profanity: 不当言论（辱骂、低俗）

你需要：
1. 分析文本样本的特征
2. 提取共同的关键词或模式
3. 生成精准的过滤规则
4. 避免过度匹配导致误伤正常内容"""


RULE_GENERATION_PROMPT_TEMPLATE = """请根据以下信息生成过滤规则：

【需求描述】
{requirement}

【未覆盖的关键词】
{uncovered_keywords}

【文本样本】
{text_samples}

【现有规则摘要】
{existing_rules_summary}

【输出要求】
请以JSON格式输出生成的规则，格式如下：
{{
    "rules": [
        {{
            "name": "规则名称（唯一标识）",
            "type": "keyword 或 regex 或 pattern",
            "content": "规则内容",
            "category": "spam/ad/sensitive/profanity",
            "priority": 50-100的优先级,
            "description": "规则描述",
            "reasoning": "生成理由",
            "confidence": 0.0-1.0的置信度,
            "test_cases": [
                {{"text": "测试文本", "should_match": true/false}}
            ]
        }}
    ],
    "analysis": "整体分析说明"
}}

【你的输出】"""


RULE_VALIDATION_PROMPT_TEMPLATE = """请验证以下过滤规则的有效性：

【规则信息】
名称：{rule_name}
类型：{rule_type}
内容：{rule_content}
类别：{rule_category}

【测试文本】
{test_texts}

【验证要求】
请评估：
1. 规则是否能准确匹配目标内容？
2. 是否会误伤正常内容？
3. 建议的改进方案

请以JSON格式输出：
{{
    "is_valid": true/false,
    "accuracy": 0.0-1.0,
    "false_positive_risk": "低/中/高",
    "suggestions": ["建议1", "建议2"],
    "improved_content": "改进后的规则内容（如果需要）"
}}

【你的评估】"""


class RuleGenerator:
    """
    LLM规则生成器
    
    功能：
    1. 分析规则缺口
    2. 根据文本样本生成规则
    3. 验证规则有效性
    4. 优化现有规则
    """
    
    def __init__(self, llm_engine=None, rule_manager=None):
        """
        初始化规则生成器
        
        Args:
            llm_engine: LLM引擎实例
            rule_manager: 规则管理器实例
        """
        self._llm_engine = llm_engine
        self.rule_manager = rule_manager
        self._generation_history: List[Dict] = []
    
    @property
    def llm_engine(self):
        """懒加载LLM引擎"""
        if self._llm_engine is None:
            from ..llm.engine import LLMEngine
            self._llm_engine = LLMEngine()
        return self._llm_engine
    
    def analyze_gap(
        self,
        texts: List[str],
        filter_results: List[Dict],
        custom_keywords: List[str] = None,
    ) -> GapAnalysis:
        """
        分析规则缺口
        
        Args:
            texts: 文本列表
            filter_results: 过滤结果列表
            custom_keywords: 用户指定的自定义关键词
            
        Returns:
            GapAnalysis: 缺口分析结果
        """
        gap = GapAnalysis()
        
        # 找出未被过滤但可能需要过滤的文本
        unfiltered_texts = []
        for text, result in zip(texts, filter_results):
            if not result.get("is_spam", False):
                # 检查是否包含可疑特征
                if self._has_suspicious_features(text):
                    unfiltered_texts.append(text)
        
        gap.text_samples = unfiltered_texts[:10]  # 最多10个样本
        
        # 检查自定义关键词覆盖情况
        if custom_keywords:
            existing_keywords = self._get_existing_keywords()
            gap.uncovered_keywords = [
                kw for kw in custom_keywords 
                if kw not in existing_keywords
            ]
        
        # 提取未覆盖文本中的共同模式
        if unfiltered_texts:
            gap.uncovered_patterns = self._extract_patterns(unfiltered_texts)
        
        return gap
    
    def _has_suspicious_features(self, text: str) -> bool:
        """检查文本是否有可疑特征"""
        suspicious_patterns = [
            r'[vV微][信xX]',           # 微信变体
            r'加我|联系我|私信',         # 引流词
            r'\d{5,}',                 # 长数字串
            r'http[s]?://',            # 链接
            r'[￥$]\d+',               # 价格
            r'免费|优惠|折扣|秒杀',      # 营销词
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _get_existing_keywords(self) -> set:
        """获取现有规则中的所有关键词"""
        keywords = set()
        
        if self.rule_manager:
            rules = self.rule_manager.list(enabled_only=True, rule_type="keyword")
            for rule in rules:
                kws = [k.strip() for k in rule.content.split(",")]
                keywords.update(kws)
        
        return keywords
    
    def _extract_patterns(self, texts: List[str]) -> List[str]:
        """从文本中提取共同模式"""
        patterns = []
        
        # 提取常见的可疑模式
        all_text = " ".join(texts)
        
        # 检测联系方式模式
        contact_patterns = re.findall(r'[vV微][信xX][\s:：]?[\w]+', all_text)
        if contact_patterns:
            patterns.append("联系方式引流")
        
        # 检测价格模式
        price_patterns = re.findall(r'[￥$]\d+', all_text)
        if price_patterns:
            patterns.append("价格营销")
        
        # 检测重复内容
        words = all_text.split()
        word_counts = {}
        for word in words:
            if len(word) >= 2:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        repeated_words = [w for w, c in word_counts.items() if c >= 3]
        if repeated_words:
            patterns.append(f"高频词: {', '.join(repeated_words[:5])}")
        
        return patterns
    
    def generate_rules(
        self,
        requirement: str,
        gap: GapAnalysis,
        max_rules: int = 3,
    ) -> List[GeneratedRule]:
        """
        根据需求和缺口分析生成规则
        
        Args:
            requirement: 需求描述
            gap: 缺口分析结果
            max_rules: 最大生成规则数
            
        Returns:
            List[GeneratedRule]: 生成的规则列表
        """
        if not gap.has_gaps():
            return []
        
        # 构建提示词
        prompt = RULE_GENERATION_PROMPT_TEMPLATE.format(
            requirement=requirement,
            uncovered_keywords=", ".join(gap.uncovered_keywords) if gap.uncovered_keywords else "无",
            text_samples="\n".join([f"- {t[:200]}" for t in gap.text_samples[:5]]),
            existing_rules_summary=self._get_existing_rules_summary(),
        )
        
        # 调用LLM
        try:
            response = self._call_llm_for_rules(prompt)
            generated_rules = self._parse_rule_response(response)
            
            # 限制数量
            generated_rules = generated_rules[:max_rules]
            
            # 记录历史
            self._generation_history.append({
                "timestamp": datetime.now().isoformat(),
                "requirement": requirement,
                "gap": gap.to_dict(),
                "generated_count": len(generated_rules),
            })
            
            return generated_rules
            
        except Exception as e:
            print(f"规则生成失败: {e}")
            return []
    
    def _get_existing_rules_summary(self) -> str:
        """获取现有规则摘要"""
        if not self.rule_manager:
            return "无现有规则"
        
        rules = self.rule_manager.list(enabled_only=True, limit=20)
        if not rules:
            return "无现有规则"
        
        summary_lines = []
        for rule in rules:
            summary_lines.append(f"- {rule.name} ({rule.type}): {rule.content[:50]}...")
        
        return "\n".join(summary_lines)
    
    def _call_llm_for_rules(self, prompt: str) -> str:
        """调用LLM生成规则"""
        messages = [
            {"role": "system", "content": RULE_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        # 这里需要根据实际的LLM引擎实现调整
        if hasattr(self.llm_engine, 'chat'):
            return self.llm_engine.chat(messages)
        elif hasattr(self.llm_engine, '_call_api'):
            return self.llm_engine._call_api(messages)
        else:
            raise NotImplementedError("LLM引擎未实现chat方法")
    
    def _parse_rule_response(self, response: str) -> List[GeneratedRule]:
        """解析LLM响应"""
        generated_rules = []
        
        try:
            # 提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                return []
            
            data = json.loads(json_match.group())
            rules_data = data.get("rules", [])
            
            for rule_data in rules_data:
                rule = RuleCreate(
                    name=rule_data.get("name", f"auto_rule_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                    type=RuleType(rule_data.get("type", "keyword")),
                    content=rule_data.get("content", ""),
                    category=RuleCategory(rule_data.get("category", "spam")) if rule_data.get("category") else None,
                    priority=rule_data.get("priority", 50),
                    description=rule_data.get("description", "LLM自动生成"),
                    enabled=True,
                )
                
                generated_rule = GeneratedRule(
                    rule=rule,
                    confidence=rule_data.get("confidence", 0.5),
                    reasoning=rule_data.get("reasoning", ""),
                    test_cases=rule_data.get("test_cases", []),
                )
                
                generated_rules.append(generated_rule)
                
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
        except Exception as e:
            print(f"规则解析失败: {e}")
        
        return generated_rules
    
    def validate_rule(
        self,
        rule: RuleCreate,
        test_texts: List[str],
    ) -> Dict[str, Any]:
        """
        验证规则有效性
        
        Args:
            rule: 待验证的规则
            test_texts: 测试文本列表
            
        Returns:
            Dict: 验证结果
        """
        # 基本验证
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
        }
        
        # 检查规则内容
        if not rule.content or not rule.content.strip():
            validation_result["is_valid"] = False
            validation_result["errors"].append("规则内容为空")
            return validation_result
        
        # 验证正则表达式语法
        if rule.type == RuleType.REGEX:
            try:
                re.compile(rule.content)
            except re.error as e:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"正则表达式语法错误: {e}")
                return validation_result
        
        # 测试匹配效果
        if test_texts:
            match_count = 0
            for text in test_texts:
                if self._test_rule_match(rule, text):
                    match_count += 1
            
            match_rate = match_count / len(test_texts)
            validation_result["match_rate"] = match_rate
            
            if match_rate == 0:
                validation_result["warnings"].append("规则未匹配任何测试文本")
            elif match_rate > 0.8:
                validation_result["warnings"].append("规则匹配率过高，可能存在误伤风险")
        
        return validation_result
    
    def _test_rule_match(self, rule: RuleCreate, text: str) -> bool:
        """测试规则是否匹配文本"""
        if rule.type == RuleType.KEYWORD:
            keywords = [k.strip() for k in rule.content.split(",")]
            return any(kw in text for kw in keywords)
        elif rule.type == RuleType.REGEX:
            try:
                return bool(re.search(rule.content, text))
            except:
                return False
        return False
    
    def save_rule(self, generated_rule: GeneratedRule) -> Optional[int]:
        """
        保存生成的规则到数据库
        
        Args:
            generated_rule: 生成的规则
            
        Returns:
            int: 规则ID，失败返回None
        """
        if not self.rule_manager:
            print("规则管理器未配置")
            return None
        
        try:
            # 检查规则名是否已存在
            existing = self.rule_manager.get_by_name(generated_rule.rule.name)
            if existing:
                # 添加时间戳后缀
                generated_rule.rule.name = f"{generated_rule.rule.name}_{datetime.now().strftime('%H%M%S')}"
            
            # 创建规则
            rule = self.rule_manager.create(generated_rule.rule)
            print(f"规则已保存: {rule.name} (ID: {rule.id})")
            return rule.id
            
        except Exception as e:
            print(f"规则保存失败: {e}")
            return None
    
    def get_generation_history(self) -> List[Dict]:
        """获取生成历史"""
        return self._generation_history.copy()


# 便捷函数
def generate_rules_from_gap(
    requirement: str,
    gap: GapAnalysis,
    llm_engine=None,
    rule_manager=None,
) -> List[GeneratedRule]:
    """从缺口分析生成规则的便捷函数"""
    generator = RuleGenerator(llm_engine, rule_manager)
    return generator.generate_rules(requirement, gap)
