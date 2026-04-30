"""
智能体功能测试脚本
测试数据收集、情感分析、报告生成和信息过滤智能体
"""
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from src.database import (
    init_db,
    get_session,
    ConversationMemoryService,
    AgentMemoryService,
    AuditLogService
)
from src.agents import (
    DataCollectionAgent,
    SentimentAnalysisAgent,
    ReportGenerationAgent,
    FilterAgent
)
from src.utils.logger import get_logger

logger = get_logger("test_agents")


def test_database_connection():
    """测试数据库连接"""
    print("\n" + "="*60)
    print("测试 1: 数据库连接")
    print("="*60)
    
    try:
        init_db()
        print("✓ 数据库连接成功")
        db = get_session()
        print("✓ 数据库会话创建成功")
        db.close()
        return True
    except Exception as e:
        print(f"✗ 数据库连接失败: {str(e)}")
        return False


def test_conversation_memory():
    """测试对话记忆服务"""
    print("\n" + "="*60)
    print("测试 2: 对话记忆服务")
    print("="*60)
    
    try:
        db = get_session()
        service = ConversationMemoryService(db)
        
        # 创建工作流
        workflow = service.create_workflow(
            name="测试工作流",
            description="用于测试的工作流",
            definition={"test": "data"}
        )
        print(f"✓ 创建工作流成功: {workflow.id}")
        
        # 保存对话
        conversation = service.save_conversation(
            workflow_id=workflow.id,
            user_message="测试用户消息",
            assistant_response="测试助手响应"
        )
        print(f"✓ 保存对话成功: {conversation.id}")
        
        # 获取对话历史
        history = service.get_conversation_history(workflow.id)
        print(f"✓ 获取对话历史成功，共 {len(history)} 条")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ 对话记忆服务测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_data_collection_agent():
    """测试数据收集智能体"""
    print("\n" + "="*60)
    print("测试 3: 数据收集智能体")
    print("="*60)
    
    try:
        # 创建测试工作流
        db = get_session()
        conv_service = ConversationMemoryService(db)
        workflow = conv_service.create_workflow(
            name="数据收集测试",
            description="测试数据收集智能体",
            definition={"test": "data_collection"}
        )
        db.close()
        
        # 初始化智能体
        agent = DataCollectionAgent(workflow.id)
        
        # 执行数据收集
        print("执行数据收集工作流...")
        result = agent.execute_preset_workflow(topic="DeepSeek")
        
        print(f"✓ 数据收集完成")
        print(f"  - 总数据量: {result['summary']['total_items']}")
        print(f"  - 数据来源: {result['summary']['sources']}")
        print(f"  - 知识库数据: {result.get('knowledge_base_count', 0)} 条")
        print(f"  - 实时数据: {result.get('real_time_count', 0)} 条")
        
        # 获取收集历史
        history = agent.get_collection_history()
        print(f"✓ 获取收集历史成功，共 {len(history)} 条记录")
        
        agent.close()
        return True
    except Exception as e:
        print(f"✗ 数据收集智能体测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_sentiment_analysis_agent():
    """测试情感分析智能体"""
    print("\n" + "="*60)
    print("测试 4: 情感分析智能体")
    print("="*60)
    
    try:
        # 创建测试工作流
        db = get_session()
        conv_service = ConversationMemoryService(db)
        workflow = conv_service.create_workflow(
            name="情感分析测试",
            description="测试情感分析智能体",
            definition={"test": "sentiment_analysis"}
        )
        db.close()
        
        # 初始化智能体
        agent = SentimentAnalysisAgent(workflow.id)
        
        # 准备测试数据
        test_data = [
            {"id": 1, "content": "DeepSeek is amazing! I love it.", "source": "twitter"},
            {"id": 2, "content": "I had a terrible experience with this.", "source": "reddit"},
            {"id": 3, "content": "It's okay, but could be better.", "source": "facebook"},
            {"id": 4, "content": "Best AI ever!!!", "source": "twitter"},
            {"id": 5, "content": "I hate this product.", "source": "reddit"}
        ]
        
        # 执行情感分析
        print("执行情感分析...")
        result = agent.analyze_sentiment(test_data)
        
        print(f"✓ 情感分析完成")
        print(f"  - 分析条数: {result['summary']['total_analyzed']}")
        print(f"  - 主要情感: {result['summary']['dominant_sentiment']}")
        print(f"  - 正面: {result['summary']['sentiment_counts']['positive']} 条")
        print(f"  - 负面: {result['summary']['sentiment_counts']['negative']} 条")
        print(f"  - 中性: {result['summary']['sentiment_counts']['neutral']} 条")
        print(f"  - 趋势: {result['trend']['trend']}")
        
        # 测试从案例学习
        print("\n测试从用户反馈学习...")
        agent.learn_from_case({
            "content": "This is absolutely fantastic!",
            "expected_sentiment": "positive"
        })
        print("✓ 案例学习成功")
        
        agent.close()
        return True
    except Exception as e:
        print(f"✗ 情感分析智能体测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_report_generation_agent():
    """测试报告生成智能体"""
    print("\n" + "="*60)
    print("测试 5: 报告生成智能体")
    print("="*60)
    
    try:
        # 创建测试工作流
        db = get_session()
        conv_service = ConversationMemoryService(db)
        workflow = conv_service.create_workflow(
            name="报告生成测试",
            description="测试报告生成智能体",
            definition={"test": "report_generation"}
        )
        db.close()
        
        # 初始化智能体
        agent = ReportGenerationAgent(workflow.id)
        
        # 准备测试数据（情感分析结果）
        test_data = {
            "topic": "DeepSeek",
            "total_analyzed": 10,
            "sentiment_counts": {"positive": 6, "negative": 2, "neutral": 2},
            "sentiment_distribution": {"positive": 0.6, "negative": 0.2, "neutral": 0.2},
            "dominant_sentiment": "positive",
            "trend": {
                "trend": "improving",
                "first_half": {"positive": 2, "negative": 1, "total": 3},
                "second_half": {"positive": 4, "negative": 1, "total": 5}
            },
            "analyzed_data": [
                {"content": "Great!", "sentiment": "positive", "source": "twitter"},
                {"content": "Bad!", "sentiment": "negative", "source": "reddit"},
                {"content": "Okay", "sentiment": "neutral", "source": "facebook"}
            ]
        }
        
        # 生成情感分析报告
        print("生成情感分析报告...")
        report_result = agent.generate_report(
            report_type="sentiment_analysis",
            data=test_data
        )
        
        print(f"✓ 报告生成成功")
        print(f"  - 报告类型: {report_result['report_type']}")
        print(f"  - 使用的模板: {report_result['extra_data']['template_used']}")
        print(f"  - 应用的规则: {report_result['extra_data']['rules_applied']}")
        print(f"  - 执行时间: {report_result['extra_data']['execution_time_ms']}ms")
        
        # 获取审计日志
        print("\n获取审计日志...")
        audit_logs = agent.get_audit_logs(limit=5)
        print(f"✓ 获取审计日志成功，共 {len(audit_logs)} 条")
        if audit_logs:
            print(f"  - 最新操作: {audit_logs[0]['operation_type']}")
            print(f"  - 状态: {audit_logs[0]['status']}")
        
        agent.close()
        return True
    except Exception as e:
        print(f"✗ 报告生成智能体测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_filter_agent():
    """测试信息过滤智能体"""
    print("\n" + "="*60)
    print("测试 6: 信息过滤智能体")
    print("="*60)
    
    try:
        # 创建测试工作流
        db = get_session()
        conv_service = ConversationMemoryService(db)
        workflow = conv_service.create_workflow(
            name="信息过滤测试",
            description="测试信息过滤智能体",
            definition={"test": "filter"}
        )
        db.close()
        
        # 初始化智能体
        agent = FilterAgent(workflow.id)
        
        # 准备测试数据
        test_data = [
            {"id": 1, "content": "Test data 1", "source": "source1"},
            {"id": 2, "content": "Test data 2", "source": "source2"},
            {"id": 3, "content": "Test data 3", "source": "source3"}
        ]
        
        # 执行过滤
        print("执行数据过滤...")
        result = agent.filter_data(test_data)
        
        print(f"✓ 过滤接口调用成功")
        print(f"  - 原始数据: {result['original_count']} 条")
        print(f"  - 过滤后数据: {result['filtered_count']} 条")
        print(f"  - 状态: {result['extra_data']['status']}")
        
        agent.close()
        return True
    except Exception as e:
        print(f"✗ 信息过滤智能体测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_services():
    """测试记忆服务"""
    print("\n" + "="*60)
    print("测试 7: 记忆服务")
    print("="*60)
    
    try:
        # 创建测试工作流
        db = get_session()
        conv_service = ConversationMemoryService(db)
        workflow = conv_service.create_workflow(
            name="记忆服务测试",
            description="测试记忆服务",
            definition={"test": "memory"}
        )
        
        memory_service = AgentMemoryService(db)
        
        # 测试保存记忆
        print("保存领域知识...")
        memory_service.save_memory(
            workflow_id=workflow.id,
            agent_type="sentiment_analysis",
            memory_type="domain_knowledge",
            key="test_knowledge",
            value={"test": "value"},
            extra_data={"source": "test"}
        )
        print("✓ 领域知识保存成功")
        
        # 测试保存案例模式
        print("保存案例模式...")
        memory_service.save_memory(
            workflow_id=workflow.id,
            agent_type="sentiment_analysis",
            memory_type="case_pattern",
            key="test_pattern",
            value={"pattern": "test", "features": {}},
            extra_data={"source": "test"}
        )
        print("✓ 案例模式保存成功")
        
        # 测试保存模板
        print("保存模板...")
        memory_service.save_memory(
            workflow_id=workflow.id,
            agent_type="report_generation",
            memory_type="template",
            key="test_template",
            value="# Test Template\n{{ content }}",
            extra_data={"source": "test"}
        )
        print("✓ 模板保存成功")
        
        # 测试保存规则
        print("保存规则...")
        memory_service.save_memory(
            workflow_id=workflow.id,
            agent_type="report_generation",
            memory_type="rule",
            key="test_rule",
            value={"conditions": {}, "actions": {}},
            extra_data={"source": "test"}
        )
        print("✓ 规则保存成功")
        
        # 测试获取记忆
        print("\n获取记忆...")
        memories = memory_service.get_memory(workflow.id, "sentiment_analysis")
        print(f"✓ 获取记忆成功，共 {len(memories)} 条")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ 记忆服务测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始运行智能体功能测试")
    print("="*60)
    
    test_results = []
    
    # 运行测试
    test_results.append(("数据库连接", test_database_connection()))
    test_results.append(("对话记忆服务", test_conversation_memory()))
    test_results.append(("数据收集智能体", test_data_collection_agent()))
    test_results.append(("情感分析智能体", test_sentiment_analysis_agent()))
    test_results.append(("报告生成智能体", test_report_generation_agent()))
    test_results.append(("信息过滤智能体", test_filter_agent()))
    test_results.append(("记忆服务", test_memory_services()))
    
    # 输出测试结果汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)