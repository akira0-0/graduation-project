#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试LangGraph的基本功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
workflow_engine_dir = project_root / "workflow_engine"
sys.path.insert(0, str(workflow_engine_dir))

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator


class SimpleState(TypedDict):
    messages: Annotated[list, operator.add]
    count: int


def simple_node(state: SimpleState) -> dict:
    """简单的节点函数"""
    print(f"执行节点，当前状态: {state}")
    return {"messages": ["hello"], "count": state.get("count", 0) + 1}


def test_basic_graph():
    """测试基本的图构建"""
    print("=" * 70)
    print("测试：基本图构建")
    print("=" * 70)
    
    try:
        # 创建图
        graph = StateGraph(SimpleState)
        
        # 添加节点
        print("添加节点 node1...")
        graph.add_node("node1", simple_node)
        print("✓ 节点添加成功")
        
        # 添加边
        print("添加边 node1 -> END...")
        graph.add_edge("node1", END)
        print("✓ 边添加成功")
        
        # 设置入口点
        print("设置入口点...")
        graph.set_entry_point("node1")
        print("✓ 入口点设置成功")
        
        # 编译
        print("编译图...")
        app = graph.compile()
        print("✓ 图编译成功")
        
        # 执行
        print("\n执行图...")
        result = app.invoke({"messages": [], "count": 0})
        print(f"✓ 执行成功，结果: {result}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_basic_graph()
    print("\n" + "=" * 70)
    if success:
        print("✅ 测试通过")
    else:
        print("❌ 测试失败")
    print("=" * 70)