# -*- coding: utf-8 -*-
"""
智能规则匹配测试脚本
测试 SmartRuleMatcher 的功能
"""
import sys
sys.path.insert(0, '.')

from filter_engine.llm.smart_matcher import SmartRuleMatcher
from filter_engine.rules import RuleManager
from filter_engine.config import settings


def test_smart_match():
    """测试智能规则匹配"""
    print("=" * 60)
    print("智能规则匹配测试")
    print("=" * 60)
    
    # 初始化
    matcher = SmartRuleMatcher()
    
    # 测试查询
    query = "帮我找一下最近丽江有什么便宜又好玩的民宿，别给我看广告。"
    
    print(f"\n【用户查询】\n{query}\n")
    
    # 显示现有规则
    rule_manager = RuleManager(settings.DATABASE_PATH)
    rules = rule_manager.list(enabled_only=True)
    print(f"【现有规则库】共 {len(rules)} 条")
    for rule in rules[:5]:  # 只显示前5条
        print(f"  - {rule.id}: {rule.name} [{rule.type.value}]")
    if len(rules) > 5:
        print(f"  ... 还有 {len(rules) - 5} 条")
    
    print("\n【调用LLM进行智能匹配...】")
    
    # 执行匹配
    result = matcher.match_sync(query)
    
    print(f"\n【匹配结果】")
    print(f"成功: {result.success}")
    
    if result.error:
        print(f"错误: {result.error}")
        return
    
    # 显示思维链
    print(f"\n【思维链 (CoT)】")
    print("Step 1 - 约束提取:")
    for item in result.thought_trace.step_1_extraction:
        print(f"  • {item}")
    
    print("\nStep 2 - 规则匹配:")
    for item in result.thought_trace.step_2_match:
        print(f"  • {item}")
    
    print("\nStep 3 - 缺口分析:")
    for item in result.thought_trace.step_3_gap_analysis:
        print(f"  • {item}")
    
    print("\nStep 4 - 规则生成:")
    for item in result.thought_trace.step_4_generation:
        print(f"  • {item}")
    
    # 显示匹配的规则（按purpose分组）
    filter_rules = [r for r in result.matched_rules if r.purpose == "filter"]
    select_rules = [r for r in result.matched_rules if r.purpose == "select"]
    
    print(f"\n【匹配到的规则】")
    if filter_rules:
        print(f"  🚫 过滤规则 (删除不要的):")
        for rule in filter_rules:
            print(f"     rule_{rule.rule_id}: {rule.rule_name} - {rule.match_reason}")
    if select_rules:
        print(f"  ✅ 筛选规则 (保留想要的):")
        for rule in select_rules:
            print(f"     rule_{rule.rule_id}: {rule.rule_name} - {rule.match_reason}")
    
    # 显示生成的规则（按purpose分组）
    gen_filter = [r for r in result.generated_rules if r.purpose == "filter"]
    gen_select = [r for r in result.generated_rules if r.purpose == "select"]
    
    print(f"\n【生成的规则】")
    if gen_filter:
        print(f"  🚫 过滤规则:")
        for rule in gen_filter:
            print(f"     {rule.name}: {rule.rule}")
    if gen_select:
        print(f"  ✅ 筛选规则:")
        for rule in gen_select:
            print(f"     {rule.name}: {rule.rule}")
    
    # 显示最终规则
    print(f"\n【最终组合规则】")
    import json
    print(json.dumps(result.final_rule, indent=2, ensure_ascii=False))
    
    # 显示执行计划
    if result.execution_plan:
        print(f"\n【执行计划】")
        for key, value in result.execution_plan.items():
            print(f"  {key}: {value}")
    
    # 显示建议保存的规则
    print(f"\n【建议保存的规则】({len(result.suggest_save)} 条)")
    for rule in result.suggest_save:
        purpose_icon = "🚫" if rule.purpose == "filter" else "✅"
        purpose_text = "过滤" if rule.purpose == "filter" else "筛选"
        print(f"  {purpose_icon} {rule.name} [{rule.type}] ({purpose_text})")
        print(f"    分类: {rule.category}")
        print(f"    原因: {rule.reason}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_smart_match()
