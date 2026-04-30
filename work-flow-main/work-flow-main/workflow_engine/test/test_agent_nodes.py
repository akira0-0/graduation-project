#!/usr/bin/env python3
"""
智能体节点测试脚本
测试四个智能体节点的功能和协作能力
"""
import os
import sys
import json

# 添加项目根目录到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from workflow_engine.src.core.schema import WorkflowDefinition, NodeDefinition, EdgeDefinition, NodeConfig
from workflow_engine.src.core.builder import GraphBuilder
from workflow_engine.src.monitoring import ExecutionMonitor
from workflow_engine.src.utils.logger import get_logger

logger = get_logger("test_agent_nodes")


def test_data_collection_agent():
    """测试数据收集智能体节点"""
    print("\n" + "="*60)
    print("测试数据收集智能体节点")
    print("="*60)
    
    # 创建节点定义
    node_def = NodeDefinition(
        id="test_collector",
        type="DataCollectionAgent",
        config=NodeConfig(
            title="数据收集",
            description="测试数据收集",
            agent_role="数据收集专家",
            agent_goal="从互联网收集信息",
            params={
                "topic": "Python编程",
                "sources": ["internet"],
                "max_results": 5,
                "time_range": "week"
            }
        )
    )
    
    try:
        # 导入节点类
        from workflow_engine.src.nodes.data_collection_agent_node import DataCollectionAgentNode
        
        # 创建节点实例
        node = DataCollectionAgentNode(node_def)
        
        # 创建模拟状态
        from workflow_engine.src.core.schema import WorkflowState
        state = WorkflowState()
        
        # 执行节点
        print(f"执行节点: {node_def.id}")
        result = node.execute(state)
        
        print(f"✅ 节点执行成功")
        print(f"状态: {result.get('status')}")
        print(f"消息: {result.get('message')}")
        print(f"收集数据数量: {result.get('total_count', 0)}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sentiment_agent():
    """测试情感分析智能体节点"""
    print("\n" + "="*60)
    print("测试情感分析智能体节点")
    print("="*60)
    
    # 创建节点定义
    node_def = NodeDefinition(
        id="test_sentiment",
        type="SentimentAgent",
        config=NodeConfig(
            title="情感分析",
            description="测试情感分析",
            agent_role="情感分析专家",
            agent_goal="分析文本情感",
            params={
                "data": [
                    {"content": "这个产品非常好用，我非常喜欢！", "author": "user1"},
                    {"content": "质量很差，不推荐购买。", "author": "user2"},
                    {"content": "还可以，中规中矩。", "author": "user3"}
                ],
                "analysis_type": "sentiment",
                "language": "zh"
            }
        )
    )
    
    try:
        # 导入节点类
        from workflow_engine.src.nodes.sentiment_agent_node import SentimentAgentNode
        
        # 创建节点实例
        node = SentimentAgentNode(node_def)
        
        # 创建模拟状态
        from workflow_engine.src.core.schema import WorkflowState
        state = WorkflowState()
        
        # 执行节点
        print(f"执行节点: {node_def.id}")
        result = node.execute(state)
        
        print(f"✅ 节点执行成功")
        print(f"状态: {result.get('status')}")
        print(f"消息: {result.get('message')}")
        
        if 'analysis_result' in result:
            analysis = result['analysis_result']
            print(f"总分析数: {analysis.get('total_count', 0)}")
            print(f"正面: {analysis.get('positive_count', 0)}")
            print(f"负面: {analysis.get('negative_count', 0)}")
            print(f"中性: {analysis.get('neutral_count', 0)}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_agent():
    """测试报告生成智能体节点"""
    print("\n" + "="*60)
    print("测试报告生成智能体节点")
    print("="*60)
    
    # 创建节点定义
    node_def = NodeDefinition(
        id="test_report",
        type="ReportAgent",
        config=NodeConfig(
            title="报告生成",
            description="测试报告生成",
            agent_role="报告生成专家",
            agent_goal="生成分析报告",
            params={
                "report_type": "sentiment_analysis",
                "template": "default",
                "format": "markdown"
            }
        )
    )
    
    try:
        # 导入节点类
        from workflow_engine.src.nodes.report_agent_node import ReportAgentNode
        
        # 创建节点实例
        node = ReportAgentNode(node_def)
        
        # 创建模拟状态，包含前序节点的输出
        from workflow_engine.src.core.schema import WorkflowState
        state = WorkflowState()
        state.node_outputs["sentiment_analyzer"] = {
            "analysis_result": {
                "total_count": 100,
                "positive_count": 60,
                "negative_count": 20,
                "neutral_count": 20,
                "dominant_sentiment": "positive",
                "trend": "improving",
                "sentiment_distribution": {
                    "positive": 60.0,
                    "negative": 20.0,
                    "neutral": 20.0
                },
                "positive_examples": [
                    {"content": "非常好用！", "source": "user1"},
                    {"content": "强烈推荐！", "source": "user2"}
                ],
                "negative_examples": [
                    {"content": "有点失望", "source": "user3"}
                ]
            }
        }
        
        # 执行节点
        print(f"执行节点: {node_def.id}")
        result = node.execute(state)
        
        print(f"✅ 节点执行成功")
        print(f"状态: {result.get('status')}")
        print(f"消息: {result.get('message')}")
        print(f"报告类型: {result.get('report_type')}")
        
        if 'report_content' in result and result['report_content']:
            print(f"报告内容长度: {len(result['report_content'])} 字符")
            print("\n报告预览（前500字符）:")
            print("-" * 60)
            print(result['report_content'][:500])
            print("-" * 60)
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_filter_agent():
    """测试信息过滤智能体节点"""
    print("\n" + "="*60)
    print("测试信息过滤智能体节点")
    print("="*60)
    
    # 创建节点定义
    node_def = NodeDefinition(
        id="test_filter",
        type="FilterAgent",
        config=NodeConfig(
            title="信息过滤",
            description="测试信息过滤",
            agent_role="数据质量分析师",
            agent_goal="过滤数据",
            params={
                "data": [
                    {"id": 1, "content": "DeepSeek是一个很好的AI模型", "score": 0.9},
                    {"id": 2, "content": "测试数据测试数据", "score": 0.3},
                    {"id": 3, "content": "AI技术发展迅速", "score": 0.8},
                    {"id": 4, "content": "随机文本", "score": 0.4}
                ],
                "filters": {
                    "min_confidence": 0.5,
                    "exclude_duplicates": True
                },
                "limit": 10
            }
        )
    )
    
    try:
        # 导入节点类
        from workflow_engine.src.nodes.filter_agent_node import FilterAgentNode
        
        # 创建节点实例
        node = FilterAgentNode(node_def)
        
        # 创建模拟状态
        from workflow_engine.src.core.schema import WorkflowState
        state = WorkflowState()
        
        # 执行节点
        print(f"执行节点: {node_def.id}")
        result = node.execute(state)
        
        print(f"✅ 节点执行成功")
        print(f"状态: {result.get('status')}")
        print(f"消息: {result.get('message')}")
        print(f"原始数据数量: {result.get('original_count', 0)}")
        print(f"过滤后数量: {result.get('filtered_count', 0)}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complete_workflow():
    """测试完整的舆论分析工作流"""
    print("\n" + "="*60)
    print("测试完整的舆论分析工作流")
    print("="*60)
    
    # 加载工作流定义
    workflow_file = os.path.join(project_root, "test_data", "public_opinion_workflow.json")
    
    if not os.path.exists(workflow_file):
        print(f"❌ 工作流文件不存在: {workflow_file}")
        return False
    
    try:
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow_dict = json.load(f)
        
        workflow_def = WorkflowDefinition(**workflow_dict)
        print(f"✅ 工作流定义加载成功: {workflow_def.name}")
        print(f"   节点数: {len(workflow_def.nodes)}")
        print(f"   连接数: {len(workflow_def.edges)}")
        
        # 创建监控器
        monitor = ExecutionMonitor(workflow_def.name)
        
        # 创建图构建器
        builder = GraphBuilder(workflow_def, monitor)
        
        # 构建图
        graph = builder.build()
        print(f"✅ 工作流图构建成功")
        
        # 创建初始状态
        initial_state = WorkflowState()
        
        # 执行工作流
        print(f"\n开始执行工作流...")
        final_state = graph.invoke(initial_state)
        
        print(f"\n✅ 工作流执行完成")
        print(f"执行状态: {final_state}")
        
        # 获取监控报告
        report = monitor.get_report()
        print(f"\n执行报告:")
        print(f"  总节点数: {report['statistics'].get('total_nodes', 0)}")
        print(f"  成功节点: {report['statistics'].get('success_nodes', 0)}")
        print(f"  失败节点: {report['statistics'].get('failed_nodes', 0)}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("智能体节点功能测试")
    print("="*60)
    
    results = {
        "数据收集智能体": test_data_collection_agent(),
        "情感分析智能体": test_sentiment_agent(),
        "报告生成智能体": test_report_agent(),
        "信息过滤智能体": test_filter_agent(),
        # "完整工作流": test_complete_workflow()  # 暂时跳过，因为需要数据库
    }
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for s in results.values() if s)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)