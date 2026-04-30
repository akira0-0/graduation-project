#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试使用WorkflowState创建LangGraph节点
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
workflow_engine_dir = project_root / "workflow_engine"
sys.path.insert(0, str(workflow_engine_dir))

from langgraph.graph import StateGraph, END
from src.core.schema import WorkflowState


def test_node(state: WorkflowState) -> dict:
    """测试节点函数"""
    print(f"执行节点，当前状态: {state}")
    return {
        "node_outputs": {**state.node_outputs, "test_node": {"result": "success"}},
        "current_node": "test_node"
    }


def test_workflow_state_graph():
    """测试使用WorkflowState的图构建"""
    print("=" * 70)
    print("测试：使用WorkflowState的图构建")
    print("=" * 70)
    
    try:
        # 创建图
        graph = StateGraph(WorkflowState)
        
        # 添加节点
        print("添加节点 test_node...")
        graph.add_node("test_node", test_node)
        print("✓ 节点添加成功")
        
        # 添加边
        print("添加边 test_node -> END...")
        graph.add_edge("test_node", END)
        print("✓ 边添加成功")
        
        # 设置入口点
        print("设置入口点...")
        graph.set_entry_point("test_node")
        print("✓ 入口点设置成功")
        
        # 编译
        print("编译图...")
        app = graph.compile()
        print("✓ 图编译成功")
        
        # 执行
        print("\n执行图...")
        initial_state = WorkflowState(
            messages=[],
            node_outputs={},
            loop_counters={},
            loop_outputs={},
            branch_decisions={},
            current_node=None
        )
        result = app.invoke(initial_state)
        print(f"✓ 执行成功")
        print(f"结果: {result}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_workflow_state_graph()
    print("\n" + "=" * 70)
    if success:
        print("✅ 测试通过")
    else:
        print("❌ 测试失败")
    print("=" * 70)