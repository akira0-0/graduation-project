#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试builder的问题
"""
import sys
from pathlib import Path
import traceback

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
workflow_engine_dir = project_root / "workflow_engine"
sys.path.insert(0, str(workflow_engine_dir))

from src.core.schema import WorkflowDefinition, WorkflowState, NodeDefinition
from src.core.builder import GraphBuilder
from src.monitoring import ExecutionMonitor


def test_builder_creation():
    """测试builder创建"""
    print("=" * 70)
    print("测试：Builder创建和节点添加")
    print("=" * 70)
    
    try:
        # 加载简单工作流
        workflow_file = project_root / "简单的总结工作流.json"
        
        import json
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        # 创建WorkflowDefinition
        workflow_def = WorkflowDefinition(**workflow_data)
        print(f"✓ 工作流定义加载成功: {workflow_def.name}")
        print(f"  节点数: {len(workflow_def.nodes)}")
        print(f"  边数: {len(workflow_def.edges)}")
        
        # 创建builder
        monitor = ExecutionMonitor(workflow_def.name, workflow_def.name)
        builder = GraphBuilder(workflow_def, monitor)
        print("✓ Builder创建成功")
        
        # 测试每个节点的创建
        for node in workflow_def.nodes:
            if node.type not in ["Start", "End"]:
                print(f"\n处理节点: {node.id} ({node.type})")
                try:
                    node_func = builder._create_node_function(node)
                    print(f"  ✓ 节点函数创建成功")
                    print(f"  函数: {node_func}")
                    print(f"  函数名: {node_func.__name__}")
                    print(f"  函数模块: {node_func.__module__}")
                    
                    # 尝试调用函数（不执行）
                    print(f"  函数可调用: {callable(node_func)}")
                    
                except Exception as e:
                    print(f"  ✗ 节点函数创建失败: {str(e)}")
                    traceback.print_exc()
        
        # 尝试构建图
        print("\n" + "=" * 70)
        print("尝试构建完整图...")
        print("=" * 70)
        app = builder.build()
        print("✓ 图构建成功")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_builder_creation()
    print("\n" + "=" * 70)
    if success:
        print("✅ 测试通过")
    else:
        print("❌ 测试失败")
    print("=" * 70)