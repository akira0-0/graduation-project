#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试使用LLMNode创建节点
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
workflow_engine_dir = project_root / "workflow_engine"
sys.path.insert(0, str(workflow_engine_dir))

from langgraph.graph import StateGraph, END
from src.core.schema import WorkflowState, NodeDefinition
from src.nodes.llm import LLMNode


def test_llm_node_creation():
    """测试LLM节点创建"""
    print("=" * 70)
    print("测试：LLM节点创建")
    print("=" * 70)
    
    try:
        # 创建节点定义
        node_def = NodeDefinition(
            id="test_llm",
            type="LLM",
            config={
                "title": "测试LLM节点",
                "agent_role": "测试角色",
                "agent_goal": "测试目标",
                "agent_backstory": "测试背景",
                "params": {
                    "model": "deepseek-chat",
                    "prompt": "Say hello",
                    "inputs": {}
                }
            }
        )
        
        print(f"✓ 节点定义创建成功: {node_def.id}")
        
        # 创建节点实例
        node_instance = LLMNode(node_def)
        print(f"✓ 节点实例创建成功: {node_instance.node_id}")
        
        # 创建LangGraph
        graph = StateGraph(WorkflowState)
        print("✓ StateGraph创建成功")
        
        # 创建节点函数（模拟builder的逻辑）
        def execute_node(state: WorkflowState) -> dict:
            """执行节点逻辑"""
            result = node_instance.execute(state)
            new_outputs = state.node_outputs.copy()
            new_outputs[node_def.id] = result
            return {
                "node_outputs": new_outputs,
                "current_node": node_def.id
            }
        
        # 添加节点
        print(f"添加节点 {node_def.id}...")
        graph.add_node(node_def.id, execute_node)
        print(f"✓ 节点添加成功")
        
        # 添加边
        print(f"添加边 {node_def.id} -> END...")
        graph.add_edge(node_def.id, END)
        print("✓ 边添加成功")
        
        # 设置入口点
        print("设置入口点...")
        graph.set_entry_point(node_def.id)
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
            current_node=None,
            context={"topic": "test"}
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
    success = test_llm_node_creation()
    print("\n" + "=" * 70)
    if success:
        print("✅ 测试通过")
    else:
        print("❌ 测试失败")
    print("=" * 70)