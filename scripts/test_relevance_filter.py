#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试相关性过滤器（验证 LLM 调用修复）

使用方法:
    uv run python scripts/test_relevance_filter.py
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from filter_engine.core.relevance_filter import RelevanceFilter, RelevanceLevel


def test_relevance_filter():
    """测试相关性过滤功能"""
    
    print("=" * 80)
    print("测试相关性过滤器 - 验证 LLM 调用修复")
    print("=" * 80)
    
    # 初始化过滤器
    rf = RelevanceFilter(use_llm=True)
    
    # 测试查询
    query = "丽江有什么好玩的"
    
    # 测试文本
    test_cases = [
        {
            "text": "丽江古城、玉龙雪山都很好玩，推荐去打卡！",
            "expected": "HIGH",
            "note": "高置信度 - 直接关键词匹配"
        },
        {
            "text": "今天天气不错，吃了顿火锅。",
            "expected": "IRRELEVANT",
            "note": "低置信度 - 无关内容"
        },
        {
            "text": "云南的景点很多，束河古镇、大理洱海都值得一去。",
            "expected": "MEDIUM/LOW",
            "note": "中间地带 - 应该调用 LLM（语义相关但缺少核心词）"
        },
        {
            "text": "丽江的美食也很不错，过桥米线很好吃。",
            "expected": "MEDIUM/LOW",
            "note": "中间地带 - 应该调用 LLM（主题不完全匹配）"
        },
    ]
    
    print(f"\n查询: {query}\n")
    
    # 执行测试
    for i, case in enumerate(test_cases, 1):
        print(f"{'─' * 80}")
        print(f"测试用例 {i}: {case['note']}")
        print(f"文本: {case['text'][:50]}...")
        print(f"预期: {case['expected']}")
        
        try:
            result = rf.filter_by_relevance(
                query=query,
                texts=[case['text']],
                min_relevance=RelevanceLevel.LOW,
                use_llm_for_uncertain=True,
            )
            
            if result['results']:
                res = result['results'][0]
                print(f"实际: {res['relevance'].upper()} (score: {res['score']:.2f})")
                print(f"原因: {res['reason']}")
                print(f"匹配关键词: {res.get('keywords_matched', [])}")
                
                # 检查是否调用了 LLM
                if "LLM" in res['reason']:
                    print("✅ LLM 调用成功！")
                elif res['score'] >= 0.3 and res['score'] < 0.6:
                    print("⚠️  中间地带但未调用 LLM（可能 LLM 不可用或调用失败）")
                else:
                    print("✅ 关键词直接判定（符合预期）")
            else:
                print("❌ 无结果")
                
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print(f"\n{'=' * 80}")
    print("测试完成！")
    print("=" * 80)
    
    # 统计信息
    print(f"\nQuery 分析:")
    result = rf.filter_by_relevance(query, ["测试"], use_llm_for_uncertain=False)
    qa = result['query_analysis']
    print(f"  核心实体: {qa['core_entity']}")
    print(f"  意图: {qa['intent']}")
    print(f"  关键词: {qa['keywords'][:10]}")
    
    # LLM 可用性
    print(f"\nLLM 状态:")
    print(f"  是否启用: {rf.use_llm}")
    print(f"  是否可用: {rf.llm_engine.is_available()}")
    if rf.llm_engine.is_available():
        print(f"  提供商: {rf.llm_engine.provider}")
        print(f"  模型: {rf.llm_engine.model}")
    else:
        print("  ⚠️  LLM 不可用，将降级为纯关键词匹配")


if __name__ == "__main__":
    test_relevance_filter()
