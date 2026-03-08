# -*- coding: utf-8 -*-
"""
演示智能筛选功能
"""
from filter_engine.core.relevance_filter import SmartDataFilter, RelevanceLevel

# 模拟数据库中的数据
texts = [
    "丽江古城夜景太美了，推荐去四方街",
    "玉龙雪山门票多少钱，学生票半价",
    "加微信xxx免费送旅游攻略",
    "今天心情不好，不想出门",
    "北京故宫一日游攻略分享",
    "丽江束河比较安静，适合度假休闲",
    "刚买的手机真好用",
    "大理洱海也很美，可以环湖骑行",
    "丽江到香格里拉怎么走，推荐大巴",
    "这个商品质量很差，不推荐",
    "丽江的纳西族文化很有特色",
    "加V: abc123，优惠带你玩",
    "泸沽湖离丽江有点远但值得去",
    "今日股市大跌",
    "丽江特产鲜花饼很好吃",
]

print("=" * 60)
print("智能数据筛选演示")
print("查询: 丽江有什么好玩的")
print("=" * 60)

sf = SmartDataFilter(use_llm=False)
result = sf.smart_filter(
    query="丽江有什么好玩的",
    texts=texts,
    filter_spam=True,
    filter_relevance=True,
    min_relevance=RelevanceLevel.MEDIUM,
)

print("\n【查询解析】")
qa = result['query_analysis']
if qa:
    print(f"  核心实体: {qa.get('core_entity', 'N/A')}")
    print(f"  意图类别: {qa.get('intent', 'N/A')}")
    print(f"  关键词: {qa.get('keywords', [])}")

print("\n【筛选统计】")
stats = result['stats']
print(f"  输入总数: {stats['total_input']}")
print(f"  垃圾过滤: {stats['spam_count']}")
print(f"  不相关: {stats['irrelevant_count']}")
print(f"  最终结果: {stats['final_count']}")

print("\n【相关内容 - 按相关性排序】")
for i, r in enumerate(result['final_results'], 1):
    rel = r.get('relevance', 'N/A')
    score = r.get('score', 0)
    content = r.get('content', '')[:40]
    print(f"  {i}. [{rel}][{score:.2f}] {content}...")

print("\n【被过滤的垃圾/广告】")
for r in result['spam_filtered']:
    content = r.get('content', '')[:40]
    print(f"  ❌ {content}...")

print("\n【被排除的不相关内容】")
for r in result['irrelevant_filtered']:
    content = r.get('content', '')[:40]
    reason = r.get('reason', '')
    print(f"  ⚪ {content}...")
    if reason:
        print(f"     原因: {reason}")

print("\n" + "=" * 60)
print("演示完成！")
