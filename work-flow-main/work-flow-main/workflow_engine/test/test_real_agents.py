"""
测试真实智能体功能
验证数据收集、情感分析、过滤和报告生成智能体的真实功能
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.data_collection_agent import DataCollectionAgent, search_internet
from src.agents.sentiment_agent import SentimentAnalysisAgent
from src.agents.report_generation_agent import ReportGenerationAgent
from src.agents.filter_agent import FilterAgent
from datetime import datetime


def test_data_collection_agent():
    """测试数据收集智能体"""
    print("\n" + "="*60)
    print("测试数据收集智能体")
    print("="*60)
    
    try:
        # 测试互联网搜索
        print("\n1. 测试互联网搜索功能...")
        results = search_internet("Python 编程", max_results=3)
        print(f"   找到 {len(results)} 条搜索结果")
        
        if results:
            for i, result in enumerate(results[:2], 1):
                print(f"   结果 {i}:")
                print(f"     标题: {result.get('title', 'N/A')}")
                print(f"     URL: {result.get('url', 'N/A')[:60]}...")
                print(f"     摘要: {result.get('snippet', 'N/A')[:80]}...")
        
        print("✅ 互联网搜索功能测试通过")
        
        # 测试完整工作流
        print("\n2. 测试完整数据收集工作流...")
        agent = DataCollectionAgent(workflow_id="test_workflow_001")
        result = agent.execute_preset_workflow(
            topic="人工智能",
            workflow_steps=["internet_search", "knowledge_base_search"]
        )
        
        print(f"   收集数据总量: {result.get('total_count', 0)}")
        print(f"   数据来源: {result.get('summary', {}).get('sources', [])}")
        
        agent.close()
        print("✅ 数据收集工作流测试通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据收集智能体测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sentiment_agent():
    """测试情感分析智能体"""
    print("\n" + "="*60)
    print("测试情感分析智能体")
    print("="*60)
    
    try:
        agent = SentimentAnalysisAgent(workflow_id="test_workflow_002")
        
        # 测试数据
        test_data = [
            {"content": "这个产品太棒了！我非常喜欢！", "source": "user1"},
            {"content": "糟糕的体验，再也不买了。", "source": "user2"},
            {"content": "还可以，一般般吧。", "source": "user3"},
            {"content": "Best product ever! Amazing quality!", "source": "user4"},
            {"content": "Terrible service, very disappointed.", "source": "user5"}
        ]
        
        print(f"\n1. 测试基础情感分析，共 {len(test_data)} 条数据...")
        result = agent.analyze_sentiment(test_data)
        
        summary = result.get("summary", {})
        print(f"   总分析数: {summary.get('total_analyzed', 0)}")
        print(f"   正面: {summary.get('sentiment_counts', {}).get('positive', 0)}")
        print(f"   负面: {summary.get('sentiment_counts', {}).get('negative', 0)}")
        print(f"   中性: {summary.get('sentiment_counts', {}).get('neutral', 0)}")
        print(f"   主要情感: {summary.get('dominant_sentiment', 'N/A')}")
        
        # 测试高级分析
        print("\n2. 测试高级情感分析（集成方法）...")
        advanced_result = agent.analyze_sentiment_advanced(
            test_data,
            use_ensemble=True,
            methods=["lexicon", "jieba"]
        )
        
        print(f"   使用方法数: {advanced_result.get('analysis_config', {}).get('method_count', 0)}")
        print(f"   分析方法: {advanced_result.get('analysis_config', {}).get('methods', [])}")
        
        # 测试情感检测
        print("\n3. 测试细粒度情感检测...")
        emotion_result = agent.detect_emotion("我今天太开心了，一切都太美好了！")
        print(f"   主要情感: {emotion_result.get('primary_emotion', 'N/A')}")
        print(f"   情感分数: {emotion_result.get('emotion_scores', {})}")
        
        agent.close()
        print("✅ 情感分析智能体测试通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 情感分析智能体测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_filter_agent():
    """测试信息过滤智能体"""
    print("\n" + "="*60)
    print("测试信息过滤智能体")
    print("="*60)
    
    try:
        agent = FilterAgent(workflow_id="test_workflow_003")
        
        # 测试数据
        test_data = [
            {"content": "这是一条很好的产品评价", "source": "user1", "timestamp": "2025-01-01T10:00:00"},
            {"content": "广告推广营销内容", "source": "spam1", "timestamp": "2025-01-02T10:00:00"},
            {"content": "这是一条很好的产品评价", "source": "user2", "timestamp": "2025-01-03T10:00:00"},  # 重复
            {"content": "短评", "source": "user3", "timestamp": "2025-01-04T10:00:00"},  # 太短
            {"content": "这是一条详细的产品评价，内容非常丰富，包含了很多有用的信息。", "source": "user4", "timestamp": "2025-01-05T10:00:00"},
        ]
        
        print(f"\n1. 测试基础过滤，原始数据量: {len(test_data)}")
        
        # 测试过滤条件
        filter_criteria = {
            "exclude_duplicates": True,
            "exclude_keywords": ["广告", "推广", "营销"],
            "min_length": 5,
            "max_length": 1000
        }
        
        result = agent.filter_data(test_data, filter_criteria)
        
        print(f"   过滤后数据量: {result.get('filtered_count', 0)}")
        print(f"   原始数据量: {result.get('original_count', 0)}")
        print(f"   过滤步骤: {len(result.get('filter_stats', {}).get('filter_steps', []))}")
        
        # 显示过滤统计
        for step in result.get('filter_stats', {}).get('filter_steps', []):
            print(f"   - {step['step']}: {step['input_count']} -> {step['output_count']}")
        
        # 测试质量评分过滤
        print("\n2. 测试质量评分过滤...")
        quality_data = [
            {"content": "详细的产品评价，包含很多信息", "title": "评价", "source": "user1", "timestamp": "2025-01-01T10:00:00", "metadata": {"likes": 10}},
            {"content": "简单", "source": "user2", "timestamp": "2025-01-01T10:00:00"},
            {"content": "中等长度的评价内容", "title": "标题", "source": "user3", "timestamp": "2025-01-01T10:00:00"},
        ]
        
        quality_result = agent.filter_data(quality_data, {"quality_threshold": 0.3})
        print(f"   高质量数据量: {quality_result.get('filtered_count', 0)}")
        
        for item in quality_result.get('filtered_data', []):
            print(f"   - 内容: {item.get('content', '')[:30]}... (质量分: {item.get('quality_score', 0):.2f})")
        
        # 测试规则管理
        print("\n3. 测试过滤规则管理...")
        rules = agent.get_filter_rules()
        print(f"   当前规则数: {len(rules)}")
        
        agent.close()
        print("✅ 信息过滤智能体测试通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 信息过滤智能体测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_generation_agent():
    """测试报告生成智能体"""
    print("\n" + "="*60)
    print("测试报告生成智能体")
    print("="*60)
    
    try:
        agent = ReportGenerationAgent(workflow_id="test_workflow_004")
        
        # 测试情感分析报告
        print("\n1. 测试情感分析报告生成...")
        sentiment_data = {
            "topic": "产品评价分析",
            "total_analyzed": 100,
            "sentiment_counts": {
                "positive": 60,
                "negative": 25,
                "neutral": 15
            },
            "sentiment_distribution": {
                "positive": 0.6,
                "negative": 0.25,
                "neutral": 0.15
            },
            "dominant_sentiment": "positive",
            "analyzed_data": [
                {"content": "产品非常好用，推荐！", "sentiment": "positive", "source": "user1"},
                {"content": "质量一般，可以改进", "sentiment": "neutral", "source": "user2"},
                {"content": "太差了，不推荐购买", "sentiment": "negative", "source": "user3"}
            ],
            "trend": {
                "trend": "improving",
                "first_half": {"positive": 25, "negative": 15, "total": 50},
                "second_half": {"positive": 35, "negative": 10, "total": 50}
            }
        }
        
        result = agent.generate_report("sentiment_analysis", sentiment_data)
        
        print(f"   报告类型: {result.get('report_type', 'N/A')}")
        print(f"   使用模板: {result.get('extra_data', {}).get('template_used', 'N/A')}")
        print(f"   应用规则数: {len(result.get('extra_data', {}).get('rules_applied', []))}")
        print(f"   生成时间: {result.get('extra_data', {}).get('generated_at', 'N/A')}")
        print(f"   报告内容长度: {len(result.get('content', ''))} 字符")
        
        # 显示报告片段
        content = result.get('content', '')
        print(f"\n   报告片段:")
        print("   " + "\n   ".join(content.split('\n')[:10]))
        
        # 测试数据收集报告
        print("\n2. 测试数据收集报告生成...")
        collection_data = {
            "topic": "人工智能趋势",
            "total_items": 50,
            "collected_data": [
                {"id": "1", "title": "AI发展趋势", "source": "news", "content": "...", "timestamp": "2025-01-01T10:00:00"},
                {"id": "2", "title": "AI应用案例", "source": "twitter", "content": "...", "timestamp": "2025-01-02T10:00:00"},
            ],
            "workflow_steps": ["internet_search", "knowledge_base_search"],
            "time_range": {
                "start": "2025-01-01",
                "end": "2025-01-31"
            }
        }
        
        collection_result = agent.generate_report("data_collection", collection_data)
        print(f"   报告类型: {collection_result.get('report_type', 'N/A')}")
        print(f"   报告内容长度: {len(collection_result.get('content', ''))} 字符")
        
        # 测试自定义模板
        print("\n3. 测试自定义模板管理...")
        agent.add_custom_template("custom_report", "# 自定义报告\n\n主题: {{ topic }}\n数据量: {{ total_items }}")
        print("   ✅ 自定义模板添加成功")
        
        agent.close()
        print("✅ 报告生成智能体测试通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 报告生成智能体测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end_workflow():
    """测试端到端工作流"""
    print("\n" + "="*60)
    print("测试端到端工作流")
    print("="*60)
    
    try:
        # 步骤1: 数据收集
        print("\n步骤1: 数据收集...")
        collection_agent = DataCollectionAgent(workflow_id="test_workflow_005")
        collection_result = collection_agent.execute_preset_workflow(
            topic="Python 编程",
            workflow_steps=["internet_search"]
        )
        
        collected_data = collection_result.get("collected_data", [])
        print(f"   收集数据量: {len(collected_data)}")
        collection_agent.close()
        
        # 步骤2: 数据过滤
        print("\n步骤2: 数据过滤...")
        filter_agent = FilterAgent(workflow_id="test_workflow_005")
        filter_result = filter_agent.filter_data(
            collected_data,
            {"min_length": 20, "exclude_duplicates": True}
        )
        
        filtered_data = filter_result.get("filtered_data", [])
        print(f"   过滤后数据量: {len(filtered_data)}")
        filter_agent.close()
        
        # 步骤3: 情感分析
        print("\n步骤3: 情感分析...")
        sentiment_agent = SentimentAnalysisAgent(workflow_id="test_workflow_005")
        sentiment_result = sentiment_agent.analyze_sentiment(filtered_data[:5])  # 只分析前5条
        
        print(f"   分析数据量: {sentiment_result.get('summary', {}).get('total_analyzed', 0)}")
        sentiment_agent.close()
        
        # 步骤4: 报告生成
        print("\n步骤4: 报告生成...")
        report_agent = ReportGenerationAgent(workflow_id="test_workflow_005")
        
        report_data = {
            "topic": "Python 编程舆情分析",
            "total_analyzed": sentiment_result.get("summary", {}).get("total_analyzed", 0),
            "sentiment_counts": sentiment_result.get("summary", {}).get("sentiment_counts", {}),
            "sentiment_distribution": sentiment_result.get("summary", {}).get("sentiment_distribution", {}),
            "dominant_sentiment": sentiment_result.get("summary", {}).get("dominant_sentiment", "neutral"),
            "analyzed_data": sentiment_result.get("analyzed_data", []),
            "trend": sentiment_result.get("trend", {})
        }
        
        report_result = report_agent.generate_report("sentiment_analysis", report_data)
        print(f"   报告生成成功，长度: {len(report_result.get('content', ''))} 字符")
        report_agent.close()
        
        print("\n✅ 端到端工作流测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 端到端工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("真实智能体功能测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "数据收集智能体": False,
        "情感分析智能体": False,
        "信息过滤智能体": False,
        "报告生成智能体": False,
        "端到端工作流": False
    }
    
    # 运行测试
    try:
        results["数据收集智能体"] = test_data_collection_agent()
    except Exception as e:
        print(f"数据收集智能体测试异常: {e}")
    
    try:
        results["情感分析智能体"] = test_sentiment_agent()
    except Exception as e:
        print(f"情感分析智能体测试异常: {e}")
    
    try:
        results["信息过滤智能体"] = test_filter_agent()
    except Exception as e:
        print(f"信息过滤智能体测试异常: {e}")
    
    try:
        results["报告生成智能体"] = test_report_generation_agent()
    except Exception as e:
        print(f"报告生成智能体测试异常: {e}")
    
    try:
        results["端到端工作流"] = test_end_to_end_workflow()
    except Exception as e:
        print(f"端到端工作流测试异常: {e}")
    
    # 显示测试结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, passed_flag in results.items():
        status = "✅ 通过" if passed_flag else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)