# -*- coding: utf-8 -*-
"""
LLM输出解析器
将LLM的非结构化输出解析为标准化结果
"""
import re
import json
from typing import Optional, Dict, Any, List

from ..rules.models import LLMResult


class LLMOutputParser:
    """LLM输出解析器"""
    
    # JSON提取正则
    JSON_PATTERN = re.compile(r'\{[^{}]*\}', re.DOTALL)
    JSON_ARRAY_PATTERN = re.compile(r'\[[^\[\]]*\]', re.DOTALL)
    
    # 字段提取正则
    IS_SPAM_PATTERN = re.compile(r'"?is_spam"?\s*[:：]\s*(true|false|True|False|是|否|1|0)', re.IGNORECASE)
    CONFIDENCE_PATTERN = re.compile(r'"?confidence"?\s*[:：]\s*([\d.]+)')
    CATEGORY_PATTERN = re.compile(r'"?category"?\s*[:：]\s*"?(\w+)"?')
    REASON_PATTERN = re.compile(r'"?reason"?\s*[:：]\s*"?([^"}\n]+)"?')
    
    @classmethod
    def parse(cls, raw_output: str) -> LLMResult:
        """
        解析LLM输出
        
        Args:
            raw_output: LLM原始输出
            
        Returns:
            LLMResult
        """
        if not raw_output:
            return LLMResult(raw_response=raw_output)
        
        # 尝试解析JSON
        result = cls._parse_json(raw_output)
        if result:
            return result
        
        # 降级：正则提取
        result = cls._parse_regex(raw_output)
        if result:
            return result
        
        # 最后降级：关键词判断
        return cls._parse_heuristic(raw_output)
    
    @classmethod
    def parse_batch(cls, raw_output: str) -> List[LLMResult]:
        """
        解析批量输出
        
        Args:
            raw_output: LLM原始输出
            
        Returns:
            LLMResult列表
        """
        results = []
        
        # 尝试解析JSON数组
        try:
            # 提取JSON数组
            match = cls.JSON_ARRAY_PATTERN.search(raw_output)
            if match:
                data = json.loads(match.group())
                if isinstance(data, list):
                    for item in data:
                        results.append(cls._dict_to_result(item, raw_output))
                    return results
        except json.JSONDecodeError:
            pass
        
        # 尝试提取多个JSON对象
        matches = cls.JSON_PATTERN.findall(raw_output)
        for match in matches:
            try:
                data = json.loads(match)
                results.append(cls._dict_to_result(data, raw_output))
            except json.JSONDecodeError:
                continue
        
        return results if results else [cls.parse(raw_output)]
    
    @classmethod
    def _parse_json(cls, raw_output: str) -> Optional[LLMResult]:
        """尝试解析JSON"""
        try:
            # 直接解析
            data = json.loads(raw_output)
            return cls._dict_to_result(data, raw_output)
        except json.JSONDecodeError:
            pass
        
        # 提取JSON对象
        match = cls.JSON_PATTERN.search(raw_output)
        if match:
            try:
                data = json.loads(match.group())
                return cls._dict_to_result(data, raw_output)
            except json.JSONDecodeError:
                pass
        
        return None
    
    @classmethod
    def _parse_regex(cls, raw_output: str) -> Optional[LLMResult]:
        """使用正则提取"""
        is_spam = None
        confidence = 0.0
        category = None
        reason = None
        
        # 提取is_spam
        match = cls.IS_SPAM_PATTERN.search(raw_output)
        if match:
            value = match.group(1).lower()
            is_spam = value in ('true', '是', '1')
        
        # 提取confidence
        match = cls.CONFIDENCE_PATTERN.search(raw_output)
        if match:
            try:
                confidence = float(match.group(1))
                confidence = min(max(confidence, 0.0), 1.0)
            except ValueError:
                pass
        
        # 提取category
        match = cls.CATEGORY_PATTERN.search(raw_output)
        if match:
            category = match.group(1).lower()
        
        # 提取reason
        match = cls.REASON_PATTERN.search(raw_output)
        if match:
            reason = match.group(1).strip()
        
        if is_spam is not None:
            return LLMResult(
                is_spam=is_spam,
                confidence=confidence,
                category=category,
                reason=reason,
                raw_response=raw_output,
            )
        
        return None
    
    @classmethod
    def _parse_heuristic(cls, raw_output: str) -> LLMResult:
        """启发式解析（最后降级方案）"""
        text_lower = raw_output.lower()
        
        # 关键词判断
        spam_keywords = ['垃圾', '广告', '敏感', '违规', 'spam', 'ad', 'sensitive']
        clean_keywords = ['正常', '合规', '没有问题', 'clean', 'safe']
        
        is_spam = False
        confidence = 0.5
        
        for kw in spam_keywords:
            if kw in text_lower:
                is_spam = True
                confidence = 0.6
                break
        
        for kw in clean_keywords:
            if kw in text_lower:
                is_spam = False
                confidence = 0.6
                break
        
        return LLMResult(
            is_spam=is_spam,
            confidence=confidence,
            reason="启发式解析",
            raw_response=raw_output,
        )
    
    @classmethod
    def _dict_to_result(cls, data: Dict[str, Any], raw_output: str) -> LLMResult:
        """将字典转换为LLMResult"""
        is_spam = data.get('is_spam', False)
        if isinstance(is_spam, str):
            is_spam = is_spam.lower() in ('true', '是', '1')
        
        confidence = data.get('confidence', 0.0)
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 0.0
        confidence = min(max(confidence, 0.0), 1.0)
        
        return LLMResult(
            is_spam=bool(is_spam),
            confidence=confidence,
            category=data.get('category'),
            reason=data.get('reason'),
            raw_response=raw_output,
        )


# 便捷函数
def parse_llm_output(raw_output: str) -> LLMResult:
    """解析LLM输出"""
    return LLMOutputParser.parse(raw_output)


def parse_batch_output(raw_output: str) -> List[LLMResult]:
    """解析批量输出"""
    return LLMOutputParser.parse_batch(raw_output)
