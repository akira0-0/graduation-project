#!/usr/bin/env python
"""
简单条件分支测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path('workflow_engine')))

import logging
logging.basicConfig(level=logging.DEBUG)

from src.core.schema import NodeDefinition, WorkflowDefinition, EdgeDefinition, NodeConfig
from src.core.builder import GraphBuilder
from src.monitoring.execution_monitor import ExecutionMonitor

print("=" * 70)
print("简单条件分支测试")
print("=" * 70)

nodes = [
    NodeDefinition(id='start', type='Start', config=NodeConfig(title='开始节点', params={})),
    NodeDefinition(id='condition_node', type='Condition', config=NodeConfig(title='条件节点', params={'condition': '$value > 10'})),
    NodeDefinition(id='task_a', type='Code', config=NodeConfig(title='任务A', params={'code': 'def main():\n    return {"result": "执行任务A"}'})),
    NodeDefinition(id='task_b', type='Code', config=NodeConfig(title='任务B', params={'code': 'def main():\n    return {"result": "执行任务B"}'})),
]

edges = [
    EdgeDefinition(source='start', target='condition_node'),
    EdgeDefinition(source='condition_node', target='task_a', condition='true'),
    EdgeDefinition(source='condition_node', target='task_b', condition='false'),
]

workflow = WorkflowDefinition(id='test', name='测试', nodes=nodes, edges=edges)
monitor = ExecutionMonitor(workflow_id='test', workflow_name='测试')
builder = GraphBuilder(workflow, monitor)
graph = builder.build()

print("\n执行工作流...")
try:
    result = graph.invoke({
        'node_outputs': {},
        'context': {'value': 15},
        'current_node': '',
        'branch_decisions': {},
        'messages': []
    })
    print('\n✓ 工作流执行成功')
    print(f'最终状态: {result}')
except Exception as e:
    print(f'\n✗ 工作流执行失败: {e}')
    import traceback
    traceback.print_exc()