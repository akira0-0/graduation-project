#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试_create_node_function方法
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
workflow_engine_dir = project_root / "workflow_engine"
sys.path.insert(0, str(workflow_engine_dir))

from src.core.schema import NodeDefinition, WorkflowState
from src.core.builder import GraphBuilder


def test_create_node_function():
    """测试_create_node_function方法"""
    print("=" * 70)
    print("测试：_create_node_function方法")
    print("=" * 70)
    
    # 创建builder
    builder = GraphBuilder(None, None)
    print("✓ Builder创建成功")
    print(f"NODE_MAP: {builder.NODE_MAP}")
    
    # 测试不同类型的节点
    test_nodes = [
        NodeDefinition(
            id="test_code",
            type="Code",
            config={
                "title": "测试Code节点",
                "agent_role": "测试角色",
                "agent_goal": "测试目标",
                "agent_backstory": "测试背景",
                "params": {
                    "code": "def main():\n    return {'result': 'success'}",
                    "inputs": {}
                }
            }
        ),
        NodeDefinition(
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
        ),
        NodeDefinition(
            id="test_condition",
            type="Condition",
            config={
                "title": "测试Condition节点",
                "agent_role": "测试角色",
                "agent_goal": "测试目标",
                "agent_backstory": "测试背景",
                "params": {
                    "condition": "$test_code.result",
                    "condition_type": "simple"
                }
            }
        ),
        NodeDefinition(
            id="test_start",
            type="Start",
            config={"title": "开始", "params": {}}
        )
    ]
    
    for node_def in test_nodes:
        print(f"\n{'='*70}")
        print(f"测试节点: {node_def.id} (类型: {node_def.type})")
        print(f"{'='*70}")
        
        try:
            print(f"调用 _create_node_function...")
            node_func = builder._create_node_function(node_def)
            print(f"  返回结果: {node_func}")
            print(f"  结果类型: {type(node_func)}")
            print(f"  是否可调用: {callable(node_func)}")
            
            # 检查是否有节点实例被创建
            print(f"  节点实例: {builder.node_instances.get(node_def.id, 'None')}")
            
            if node_func:
                print(f"  函数名: {node_func.__name__}")
                print(f"  函数模块: {node_func.__module__}")
            
            print(f"✓ 测试成功")
            
        except Exception as e:
            print(f"✗ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    test_create_node_function()