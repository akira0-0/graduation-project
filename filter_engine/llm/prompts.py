# -*- coding: utf-8 -*-
"""
LLM提示词模板
用于内容过滤的系统化提示词设计
"""
from typing import Optional, List, Dict
from string import Template


# ==================== 系统提示词 ====================

SYSTEM_PROMPT = """你是一个专业的内容审核专家，负责判断用户提交的文本是否为垃圾信息、广告或敏感内容。

你的任务是：
1. 分析文本内容的性质
2. 判断是否属于以下类别：
   - spam: 垃圾信息（无意义内容、刷屏、骚扰）
   - ad: 广告（推销、引流、联系方式）
   - sensitive: 敏感内容（政治敏感、违规信息）
   - profanity: 不当言论（辱骂、歧视、低俗）
   - clean: 正常内容

你必须严格按照JSON格式输出，不要包含其他内容。"""


# ==================== 任务提示词模板 ====================

FILTER_PROMPT_TEMPLATE = """请分析以下文本内容，判断是否为垃圾信息/广告/敏感内容。

【待分析文本】
{text}

【输出要求】
请以JSON格式输出，包含以下字段：
- is_spam: 布尔值，是否为垃圾/广告/敏感信息
- confidence: 浮点数，置信度（0-1）
- category: 字符串，内容分类（spam/ad/sensitive/profanity/clean）
- reason: 字符串，简短说明判断理由（不超过50字）

【示例输出】
{{"is_spam": true, "confidence": 0.95, "category": "ad", "reason": "包含微信号引流信息"}}

【你的判断】"""


BATCH_FILTER_PROMPT_TEMPLATE = """请分析以下多条文本内容，逐条判断是否为垃圾信息。

【待分析文本列表】
{texts}

【输出要求】
请以JSON数组格式输出，每条对应一个判断结果：
[
  {{"index": 0, "is_spam": true/false, "confidence": 0.0-1.0, "category": "类别", "reason": "理由"}},
  ...
]

【你的判断】"""


# ==================== Few-shot示例 ====================

FEW_SHOT_EXAMPLES = [
    {
        "text": "加我微信xyz123，免费领取资料",
        "result": {
            "is_spam": True,
            "confidence": 0.98,
            "category": "ad",
            "reason": "包含微信号和免费诱导"
        }
    },
    {
        "text": "这个产品真的很好用，推荐给大家",
        "result": {
            "is_spam": False,
            "confidence": 0.85,
            "category": "clean",
            "reason": "正常的产品评价分享"
        }
    },
    {
        "text": "666666666666",
        "result": {
            "is_spam": True,
            "confidence": 0.9,
            "category": "spam",
            "reason": "无意义刷屏内容"
        }
    },
    {
        "text": "点击链接领取红包 http://xxx.com",
        "result": {
            "is_spam": True,
            "confidence": 0.95,
            "category": "ad",
            "reason": "可疑链接引流"
        }
    },
]


# ==================== 提示词构建函数 ====================

def build_filter_prompt(text: str, with_examples: bool = True) -> List[Dict[str, str]]:
    """
    构建过滤提示词
    
    Args:
        text: 待分析文本
        with_examples: 是否包含Few-shot示例
        
    Returns:
        消息列表
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    # 添加Few-shot示例
    if with_examples:
        for example in FEW_SHOT_EXAMPLES[:2]:  # 使用2个示例节省token
            messages.append({
                "role": "user",
                "content": FILTER_PROMPT_TEMPLATE.format(text=example["text"])
            })
            messages.append({
                "role": "assistant",
                "content": str(example["result"]).replace("'", '"').replace("True", "true").replace("False", "false")
            })
    
    # 添加当前请求
    messages.append({
        "role": "user",
        "content": FILTER_PROMPT_TEMPLATE.format(text=text[:2000])  # 限制长度
    })
    
    return messages


def build_batch_filter_prompt(texts: List[str]) -> List[Dict[str, str]]:
    """
    构建批量过滤提示词
    
    Args:
        texts: 待分析文本列表
        
    Returns:
        消息列表
    """
    # 格式化文本列表
    texts_formatted = "\n".join([
        f"[{i}] {text[:500]}"  # 每条限制500字
        for i, text in enumerate(texts[:10])  # 最多10条
    ])
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": BATCH_FILTER_PROMPT_TEMPLATE.format(texts=texts_formatted)
        }
    ]
    
    return messages


def build_context_filter_prompt(
    text: str,
    context: Optional[str] = None,
    rule_hints: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """
    构建带上下文的过滤提示词
    
    Args:
        text: 待分析文本
        context: 上下文信息（如帖子标题、评论上下文）
        rule_hints: 规则提示（已命中但低置信度的规则）
        
    Returns:
        消息列表
    """
    enhanced_prompt = FILTER_PROMPT_TEMPLATE.format(text=text[:2000])
    
    if context:
        enhanced_prompt = f"【上下文】\n{context[:500]}\n\n" + enhanced_prompt
    
    if rule_hints:
        hints = ", ".join(rule_hints[:3])
        enhanced_prompt += f"\n\n【参考信息】规则引擎提示可能涉及: {hints}"
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": enhanced_prompt}
    ]
    
    return messages
