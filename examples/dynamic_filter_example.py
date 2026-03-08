# -*- coding: utf-8 -*-
"""
动态规则选择系统使用示例
演示如何使用LLM驱动的动态规则选择功能
"""
from filter_engine.core import (
    DynamicFilterPipeline,
    DynamicFilterConfig,
    QueryAnalyzer,
    FilterScenario,
    FilterSeverity,
)


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("示例1: 基本使用 - 带查询的过滤")
    print("=" * 60)
    
    # 创建管道
    pipeline = DynamicFilterPipeline(
        db_path="filter_engine/data/rules.db",
        use_llm=True,
    )
    
    # 待过滤的文本
    texts = [
        "这个商品质量很好，推荐购买！",
        "加我微信xyz123，免费领取优惠券",
        "666666666666",
        "点击链接领取红包 http://xxx.com/red",
        "今天天气真不错，适合出门散步",
        "V信联系：abc888，保证低价",
    ]
    
    # 使用查询进行过滤
    result = pipeline.filter_with_query(
        query="过滤电商评论中的广告和刷单内容",
        texts=texts,
        context={"source": "小红书"},
    )
    
    print(f"\n查询意图: {result['intent']}")
    print(f"选中规则: {result['selected_rules']}")
    print(f"\n过滤结果统计: {result['stats']}")
    
    print("\n详细结果:")
    for i, (text, res) in enumerate(zip(texts, result['results'])):
        status = "🚫 垃圾" if res['is_spam'] else "✅ 正常"
        print(f"  {i+1}. [{status}] {text[:30]}... (置信度: {res['confidence']:.2f})")
    
    if result['generated_rules']:
        print(f"\n生成的新规则: {len(result['generated_rules'])}条")
        for rule in result['generated_rules']:
            print(f"  - {rule['rule']['name']}: {rule['rule']['content'][:50]}")


def example_scenario_based():
    """场景化过滤示例"""
    print("\n" + "=" * 60)
    print("示例2: 场景化过滤")
    print("=" * 60)
    
    pipeline = DynamicFilterPipeline(
        db_path="filter_engine/data/rules.db",
        use_llm=False,  # 仅用规则引擎
    )
    
    # 电商场景
    ecommerce_texts = [
        "好评返现加微信",
        "质量很好，物流很快",
        "虚假宣传，差评！",
    ]
    
    print("\n电商场景过滤:")
    result = pipeline.filter_with_query(
        query="电商评论过滤",
        texts=ecommerce_texts,
        context={"scenario": "ecommerce"},
    )
    print(f"  过滤结果: {result['stats']}")
    
    # 新闻场景
    news_texts = [
        "今日国际新闻：...",
        "震惊！点击查看...",
        "官方发布最新公告...",
    ]
    
    print("\n新闻场景过滤:")
    result = pipeline.filter_with_query(
        query="新闻内容过滤，严格模式",
        texts=news_texts,
        context={"scenario": "news"},
    )
    print(f"  过滤结果: {result['stats']}")


def example_rule_generation():
    """规则生成示例"""
    print("\n" + "=" * 60)
    print("示例3: 自动规则生成")
    print("=" * 60)
    
    pipeline = DynamicFilterPipeline(
        db_path="filter_engine/data/rules.db",
        use_llm=True,
        config=DynamicFilterConfig(
            enable_rule_generation=True,
            auto_save_generated_rules=False,  # 不自动保存，手动确认
        )
    )
    
    # 需要新规则的样本
    sample_texts = [
        "dd我私信，优惠多多",
        "➕薇❤️：test123",
        "扫码加群，福利多多",
        "点击头像看简介",
    ]
    
    # 生成规则
    generated_rules = pipeline.generate_missing_rules(
        query="过滤小红书评论区的引流广告",
        sample_texts=sample_texts,
        category="ad",
    )
    
    print(f"\n生成了 {len(generated_rules)} 条规则:")
    for rule in generated_rules:
        print(f"\n规则名称: {rule.rule.name}")
        print(f"  类型: {rule.rule.type}")
        print(f"  内容: {rule.rule.content}")
        print(f"  置信度: {rule.confidence:.2f}")
        print(f"  理由: {rule.reasoning}")
        
        # 手动保存
        # save_id = pipeline.save_generated_rule(rule)
        # print(f"  已保存，ID: {save_id}")


def example_query_analyzer():
    """查询分析器示例"""
    print("\n" + "=" * 60)
    print("示例4: 查询意图分析")
    print("=" * 60)
    
    analyzer = QueryAnalyzer()
    
    queries = [
        "过滤电商评论中的广告",
        "严格过滤新闻中的敏感内容",
        "宽松模式过滤社交评论的垃圾信息",
        "过滤包含【微信】【QQ】的引流内容",
    ]
    
    for query in queries:
        intent = analyzer.analyze(query)
        print(f"\n查询: {query}")
        print(f"  场景: {intent.scenario.value}")
        print(f"  严格程度: {intent.severity.value}")
        print(f"  额外类别: {intent.extra_categories}")
        print(f"  自定义关键词: {intent.custom_keywords}")


def example_severity_levels():
    """严格程度示例"""
    print("\n" + "=" * 60)
    print("示例5: 不同严格程度的过滤效果")
    print("=" * 60)
    
    pipeline = DynamicFilterPipeline(
        db_path="filter_engine/data/rules.db",
        use_llm=False,
    )
    
    test_text = "推荐购买，有需要可以私信咨询"
    
    for severity in ["relaxed", "normal", "strict"]:
        result = pipeline.filter_text(
            text=test_text,
            scenario="social",
            severity=severity,
        )
        status = "🚫 垃圾" if result.is_spam else "✅ 正常"
        print(f"\n{severity} 模式: {status} (置信度: {result.confidence:.2f})")


if __name__ == "__main__":
    # 运行示例
    example_basic_usage()
    example_scenario_based()
    example_query_analyzer()
    example_severity_levels()
    
    # 需要LLM的示例（确保配置了API密钥）
    # example_rule_generation()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)
