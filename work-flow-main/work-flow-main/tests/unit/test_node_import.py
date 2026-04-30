#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试节点导入
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
workflow_engine_dir = project_root / "workflow_engine"
sys.path.insert(0, str(workflow_engine_dir))

print("测试节点导入...")
print("=" * 70)

try:
    print("导入 BaseNode...")
    from src.nodes.base import BaseNode
    print(f"✓ BaseNode 导入成功: {BaseNode}")
except Exception as e:
    print(f"✗ BaseNode 导入失败: {str(e)}")
    import traceback
    traceback.print_exc()

try:
    print("\n导入 LLMNode...")
    from src.nodes.llm import LLMNode
    print(f"✓ LLMNode 导入成功: {LLMNode}")
except Exception as e:
    print(f"✗ LLMNode 导入失败: {str(e)}")
    import traceback
    traceback.print_exc()

try:
    print("\n导入 CodeNode...")
    from src.nodes.code import CodeNode
    print(f"✓ CodeNode 导入成功: {CodeNode}")
except Exception as e:
    print(f"✗ CodeNode 导入失败: {str(e)}")
    import traceback
    traceback.print_exc()

try:
    print("\n导入 ConditionNode...")
    from src.nodes.condition import ConditionNode
    print(f"✓ ConditionNode 导入成功: {ConditionNode}")
except Exception as e:
    print(f"✗ ConditionNode 导入失败: {str(e)}")
    import traceback
    traceback.print_exc()

try:
    print("\n导入 LoopNode...")
    from src.nodes.loop import LoopNode
    print(f"✓ LoopNode 导入成功: {LoopNode}")
except Exception as e:
    print(f"✗ LoopNode 导入失败: {str(e)}")
    import traceback
    traceback.print_exc()

try:
    print("\n导入 GraphBuilder...")
    from src.core.builder import GraphBuilder
    print(f"✓ GraphBuilder 导入成功: {GraphBuilder}")
    print(f"  NODE_MAP: {GraphBuilder.NODE_MAP}")
except Exception as e:
    print(f"✗ GraphBuilder 导入失败: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("测试完成")