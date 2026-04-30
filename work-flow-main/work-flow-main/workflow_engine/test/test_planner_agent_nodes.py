#!/usr/bin/env python3
"""
测试规划器生成的节点类型
验证 LLMPlanner 是否正确使用智能体节点
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.planner.llm_planner import LLMPlanner


def test_planner_uses_agent_nodes():
    """测试规划器是否使用智能体节点"""
    print("=" * 60)
    print("测试规划器是否使用智能体节点")
    print("=" * 60)
    
    planner = LLMPlanner(model_name="deepseek-chat")
    
    # 测试用例：舆情分析工作流
    user_intent = "创建一个关于DeepSeek产品舆情分析的工作流"
    
    print(f"\n用户意图: {user_intent}")
    print("-" * 60)
    
    try:
        workflow = planner.plan(user_intent)
        
        print(f"\n生成的工作流名称: {workflow.name}")
        print(f"节点数量: {len(workflow.nodes)}")
        print(f"边数量: {len(workflow.edges)}")
        
        print("\n节点列表:")
        print("-" * 60)
        
        # 统计节点类型
        node_types = {}
        agent_node_count = 0
        code_node_count = 0
        llm_node_count = 0
        
        for node in workflow.nodes:
            node_types[node.type] = node_types.get(node.type, 0) + 1
            
            # 统计智能体节点和代码节点
            if node.type in ["DataCollectionAgent", "SentimentAgent", "ReportAgent", "FilterAgent"]:
                agent_node_count += 1
                print(f"  ✓ [{node.type}] {node.config.title} (智能体节点)")
            elif node.type == "Code":
                code_node_count += 1
                print(f"  ✗ [{node.type}] {node.config.title} (代码节点 - 不推荐)")
            elif node.type == "LLM":
                llm_node_count += 1
                print(f"  △ [{node.type}] {node.config.title} (LLM节点)")
            else:
                print(f"  · [{node.type}] {node.config.title}")
        
        print("\n" + "=" * 60)
        print("测试结果汇总:")
        print("=" * 60)
        print(f"节点类型分布: {node_types}")
        print(f"智能体节点数量: {agent_node_count}")
        print(f"代码节点数量: {code_node_count}")
        print(f"LLM节点数量: {llm_node_count}")
        
        # 验证结果
        success = True
        messages = []
        
        if agent_node_count > 0:
            messages.append("✅ 成功：规划器正确使用了智能体节点")
        else:
            messages.append("❌ 失败：规划器没有使用智能体节点")
            success = False
        
        if code_node_count == 0:
            messages.append("✅ 成功：没有使用代码节点来模拟智能体")
        else:
            messages.append("⚠️ 警告：仍然使用了代码节点，建议使用智能体节点替代")
        
        print("\n验证结果:")
        for msg in messages:
            print(f"  {msg}")
        
        # 显示边的连接关系
        print("\n边的连接关系:")
        for edge in workflow.edges:
            print(f"  {edge.source} -> {edge.target}")
        
        return success
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_planner_data_collection():
    """测试数据收集任务是否使用 DataCollectionAgent"""
    print("\n" + "=" * 60)
    print("测试数据收集任务")
    print("=" * 60)
    
    planner = LLMPlanner(model_name="deepseek-chat")
    user_intent = "创建一个数据收集工作流，收集关于AI技术发展趋势的信息"
    
    print(f"\n用户意图: {user_intent}")
    print("-" * 60)
    
    try:
        workflow = planner.plan(user_intent)
        
        # 检查是否有 DataCollectionAgent
        has_data_collector = any(n.type == "DataCollectionAgent" for n in workflow.nodes)
        
        print(f"\n工作流名称: {workflow.name}")
        print(f"包含 DataCollectionAgent: {'✅ 是' if has_data_collector else '❌ 否'}")
        
        for node in workflow.nodes:
            if node.type == "DataCollectionAgent":
                print(f"\nDataCollectionAgent 节点详情:")
                print(f"  ID: {node.id}")
                print(f"  标题: {node.config.title}")
                print(f"  角色: {node.config.agent_role}")
                print(f"  目标: {node.config.agent_goal}")
                print(f"  参数: {node.config.params}")
        
        return has_data_collector
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n开始测试规划器的智能体节点使用情况...\n")
    
    # 测试1：舆情分析工作流
    test1_passed = test_planner_uses_agent_nodes()
    
    # 测试2：数据收集工作流
    test2_passed = test_planner_data_collection()
    
    print("\n" + "=" * 60)
    print("最终测试结果")
    print("=" * 60)
    
    if test1_passed and test2_passed:
        print("✅ 所有测试通过！规划器正确使用智能体节点。")
        sys.exit(0)
    else:
        print("❌ 部分测试失败，请检查规划器配置。")
        sys.exit(1)