#!/usr/bin/env python
"""
工作流引擎集成测试
测试完整的工作流执行流程
"""
import sys
from pathlib import Path

# 添加 workflow_engine 到 Python 路径
workflow_engine_dir = Path(__file__).parent / "workflow_engine"
if str(workflow_engine_dir) not in sys.path:
    sys.path.insert(0, str(workflow_engine_dir))

import json
from src.core.schema import WorkflowDefinition, NodeDefinition, EdgeDefinition, NodeConfig
from src.core.builder import GraphBuilder
from src.monitoring.execution_monitor import ExecutionMonitor

def test_simple_workflow():
    """测试简单的工作流执行"""
    print("=" * 70)
    print("测试1: 简单工作流执行")
    print("=" * 70)
    
    # 创建工作流定义
    from src.core.schema import NodeConfig
    
    nodes = [
        NodeDefinition(
            id="start",
            type="Start",
            config=NodeConfig(
                title="开始节点",
                params={}
            )
        ),
        NodeDefinition(
            id="task1",
            type="Code",
            config=NodeConfig(
                title="任务1",
                params={
                    "code": "def main():\n    print('执行任务1')\n    return {'result': '任务1完成'}"
                }
            )
        ),
        NodeDefinition(
            id="end",
            type="End",
            config=NodeConfig(
                title="结束节点",
                params={}
            )
        )
    ]
    
    edges = [
        EdgeDefinition(source="start", target="task1"),
        EdgeDefinition(source="task1", target="end")
    ]
    
    workflow = WorkflowDefinition(
        id="test_workflow",
        name="测试工作流",
        description="用于测试的简单工作流",
        nodes=nodes,
        edges=edges
    )
    
    # 创建 Builder
    monitor = ExecutionMonitor(workflow_id="test_workflow", workflow_name="测试工作流")
    builder = GraphBuilder(workflow, monitor)
    
    # 构建图
    print("构建工作流图...")
    graph = builder.build()
    
    if graph:
        print("✓ 图构建成功")
        
        # 执行工作流
        print("\n执行工作流...")
        try:
            result = graph.invoke({
                "node_outputs": {},
                "context": {},
                "current_node": "",
                "branch_decisions": {},
                "messages": []
            })
            
            print(f"✓ 工作流执行成功")
            print(f"  最终状态: {result}")
            
            return True
        except Exception as e:
            print(f"✗ 工作流执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("✗ 图构建失败")
        return False


def test_llm_workflow():
    """测试包含 LLM 节点的工作流"""
    print("\n" + "=" * 70)
    print("测试2: LLM 工作流执行")
    print("=" * 70)
    
    # 创建工作流定义
    from src.core.schema import NodeConfig
    
    nodes = [
        NodeDefinition(
            id="start",
            type="Start",
            config=NodeConfig(
                title="开始节点",
                params={}
            )
        ),
        NodeDefinition(
            id="llm_node",
            type="LLM",
            config=NodeConfig(
                title="LLM节点",
                params={
                    "model": "deepseek-chat",
                    "prompt": "你好，请自我介绍一下",
                    "temperature": 0.7
                }
            )
        ),
        NodeDefinition(
            id="end",
            type="End",
            config=NodeConfig(
                title="结束节点",
                params={}
            )
        )
    ]
    
    edges = [
        EdgeDefinition(source="start", target="llm_node"),
        EdgeDefinition(source="llm_node", target="end")
    ]
    
    workflow = WorkflowDefinition(
        id="llm_workflow",
        name="LLM 测试工作流",
        description="测试 LLM 节点的工作流",
        nodes=nodes,
        edges=edges
    )
    
    # 创建 Builder
    monitor = ExecutionMonitor(workflow_id="llm_workflow", workflow_name="LLM 测试工作流")
    builder = GraphBuilder(workflow, monitor)
    
    # 构建图
    print("构建工作流图...")
    graph = builder.build()
    
    if graph:
        print("✓ 图构建成功")
        
        # 检查是否有 API key
        import os
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠ 警告: 未设置 OPENAI_API_KEY，跳过执行测试")
            return True
        
        # 执行工作流
        print("\n执行工作流...")
        try:
            result = graph.invoke({
                "node_outputs": {},
                "context": {},
                "current_node": "",
                "branch_decisions": {},
                "messages": []
            })
            
            print(f"✓ 工作流执行成功")
            print(f"  最终状态: {result}")
            
            return True
        except Exception as e:
            print(f"✗ 工作流执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("✗ 图构建失败")
        return False


def test_condition_workflow():
    """测试包含条件分支的工作流"""
    print("\n" + "=" * 70)
    print("测试3: 条件分支工作流执行")
    print("=" * 70)
    
    # 创建工作流定义
    from src.core.schema import NodeConfig
    
    nodes = [
        NodeDefinition(
            id="start",
            type="Start",
            config=NodeConfig(
                title="开始节点",
                params={}
            )
        ),
        NodeDefinition(
            id="condition_node",
            type="Condition",
            config=NodeConfig(
                title="条件节点",
                params={
                    "condition": "$value > 10"
                }
            )
        ),
        NodeDefinition(
            id="task_a",
            type="Code",
            config=NodeConfig(
                title="任务A",
                params={
                    "code": "def main():\n    return {'result': '执行任务A'}"
                }
            )
        ),
        NodeDefinition(
            id="task_b",
            type="Code",
            config=NodeConfig(
                title="任务B",
                params={
                    "code": "def main():\n    return {'result': '执行任务B'}"
                }
            )
        )
    ]
    
    edges = [
        EdgeDefinition(source="start", target="condition_node"),
        EdgeDefinition(source="condition_node", target="task_a", condition="true"),
        EdgeDefinition(source="condition_node", target="task_b", condition="false")
    ]
    
    workflow = WorkflowDefinition(
        id="condition_workflow",
        name="条件分支测试工作流",
        description="测试条件分支的工作流",
        nodes=nodes,
        edges=edges
    )
    
    # 创建 Builder
    monitor = ExecutionMonitor(workflow_id="condition_workflow", workflow_name="条件分支测试工作流")
    builder = GraphBuilder(workflow, monitor)
    
    # 构建图
    print("构建工作流图...")
    graph = builder.build()
    
    if graph:
        print("✓ 图构建成功")
        
        # 执行工作流
        print("\n执行工作流...")
        try:
            result = graph.invoke({
                "node_outputs": {},
                "context": {"value": 15},
                "current_node": "",
                "branch_decisions": {},
                "messages": []
            })
            
            print(f"✓ 工作流执行成功")
            print(f"  最终状态: {result}")
            
            return True
        except Exception as e:
            print(f"✗ 工作流执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("✗ 图构建失败")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("工作流引擎集成测试")
    print("=" * 70 + "\n")
    
    results = []
    
    # 运行测试
    results.append(("简单工作流", test_simple_workflow()))
    results.append(("LLM 工作流", test_llm_workflow()))
    results.append(("条件分支工作流", test_condition_workflow()))
    
    # 总结
    print("\n" + "=" * 70)
    print("测试结果总结")
    print("=" * 70)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ 所有测试通过!")
    else:
        print("❌ 部分测试失败")
    print("=" * 70)