# -*- coding: utf-8 -*-
"""
测试过滤引擎
"""
import sys
sys.path.insert(0, r'e:\xhs-crawler')

from filter_engine import FilterPipeline
from filter_engine.rules import RuleManager, RuleCreate

# 初始化
print("=" * 50)
print("初始化过滤管道...")
pipeline = FilterPipeline(use_llm=False)
print("初始化成功!")

# 创建测试规则
print("\n" + "=" * 50)
print("创建测试规则...")

rule_manager = RuleManager("filter_engine/data/rules.db")

# 创建关键词规则
try:
    rule1 = rule_manager.create(RuleCreate(
        name="测试关键词规则",
        type="keyword",
        content='["垃圾", "广告", "骗子"]',
        category="spam",
        priority=100,
        description="测试用关键词规则"
    ))
    print(f"创建规则成功: {rule1.name} (ID: {rule1.id})")
except Exception as e:
    print(f"规则可能已存在: {e}")

# 重建引擎
pipeline.reload_rules()
print("规则已重新加载")

# 测试过滤
print("\n" + "=" * 50)
print("测试过滤功能...")

test_cases = [
    "这是一条正常的评论",
    "这是垃圾内容",
    "广告推广联系我",
    "骗子不要相信",
    "今天天气真好",
]

for text in test_cases:
    result = pipeline.filter_text(text)
    status = "🚫 过滤" if result.should_filter else "✅ 通过"
    print(f"{status} | {text[:20]:<20} | 置信度: {result.confidence:.2f}")
    if result.matched_rules:
        for mr in result.matched_rules:
            print(f"      命中规则: {mr.rule_name}, 匹配: {mr.matched_content}")

print("\n" + "=" * 50)
print("测试完成!")
