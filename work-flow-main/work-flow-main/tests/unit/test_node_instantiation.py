#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试节点实例化
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
workflow_engine_dir = project_root / "workflow_engine"
sys.path.insert(0, str(workflow_engine_dir))

from src.core.schema import NodeDefinition, WorkflowState
from src.nodes.llm import LLMNode
from src.nodes.code import CodeNode
from src.nodes.condition import ConditionNode
from src.nodes.loop import LoopNode
from src.nodes.data_collection_agent_node import DataCollectionAgentNode
from src.agents.data_collection_agent import DataCollectionAgent
import src.nodes.data_collection_agent_node as data_collection_node_module
import src.agents.data_collection_agent as data_collection_agent_module


def test_node_instantiation():
    """测试节点实例化"""
    print("=" * 70)
    print("测试：节点实例化")
    print("=" * 70)
    
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
            id="test_loop",
            type="Loop",
            config={
                "title": "测试Loop节点",
                "agent_role": "测试角色",
                "agent_goal": "测试目标",
                "agent_backstory": "测试背景",
                "params": {
                    "loop_type": "count",
                    "max_iterations": 3
                }
            }
        )
    ]
    
    for node_def in test_nodes:
        print(f"\n{'='*70}")
        print(f"测试节点: {node_def.id} (类型: {node_def.type})")
        print(f"{'='*70}")
        
        try:
            if node_def.type == "Code":
                print(f"创建 CodeNode...")
                node = CodeNode(node_def)
                print(f"✓ CodeNode 创建成功")
            elif node_def.type == "LLM":
                print(f"创建 LLMNode...")
                node = LLMNode(node_def)
                print(f"✓ LLMNode 创建成功")
            elif node_def.type == "Condition":
                print(f"创建 ConditionNode...")
                node = ConditionNode(node_def)
                print(f"✓ ConditionNode 创建成功")
            elif node_def.type == "Loop":
                print(f"创建 LoopNode...")
                node = LoopNode(node_def)
                print(f"✓ LoopNode 创建成功")
            else:
                print(f"✗ 未知节点类型: {node_def.type}")
                
        except Exception as e:
            print(f"✗ 节点创建失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


def _build_data_collection_node_definition(topic: str = "测试主题") -> NodeDefinition:
    """构建数据收集节点定义"""
    return NodeDefinition(
        id="test_data_collection_node",
        type="DataCollectionAgent",
        config={
            "title": "数据收集节点",
            "params": {
                "topic": topic,
                "sources": ["internet"],
                "max_results": 10,
                "time_range": "week"
            }
        }
    )


def test_data_collection_agent_total_count_consistency_normal(monkeypatch):
    """正常采集：agent total_count 与 collected_data 长度一致"""
    agent = DataCollectionAgent.__new__(DataCollectionAgent)
    agent.workflow_id = "test-workflow"
    agent.auto_save = False
    agent._save_collection_strategy = lambda *args, **kwargs: None

    sample_kb = [{
        "id": "kb_1",
        "title": "知识库数据",
        "content": "content",
        "source": "wikipedia",
        "timestamp": "2026-01-01T00:00:00"
    }]
    sample_rt = [{
        "id": "rt_1",
        "title": "实时数据",
        "content": "content",
        "source": "news",
        "timestamp": "2026-01-01T00:10:00"
    }]

    monkeypatch.setattr(data_collection_agent_module, "search_knowledge_base", lambda topic: sample_kb)
    monkeypatch.setattr(data_collection_agent_module, "collect_real_time_data", lambda topic, sources=None: sample_rt)

    result = DataCollectionAgent.execute_preset_workflow(
        agent,
        topic="AI",
        workflow_steps=["knowledge_base_search", "real_time_collection", "data_aggregation"],
        save_to_db=False
    )

    assert result["total_count"] == len(result["collected_data"]) == 2
    assert result["summary"]["total_items"] == result["total_count"]
    assert result["message"] == "成功收集 2 条数据"


def test_data_collection_agent_total_count_consistency_empty(monkeypatch):
    """空数据：agent total_count 与 collected_data 长度一致"""
    agent = DataCollectionAgent.__new__(DataCollectionAgent)
    agent.workflow_id = "test-workflow"
    agent.auto_save = False
    agent._save_collection_strategy = lambda *args, **kwargs: None

    monkeypatch.setattr(data_collection_agent_module, "search_knowledge_base", lambda topic: [])
    monkeypatch.setattr(data_collection_agent_module, "collect_real_time_data", lambda topic, sources=None: [])

    result = DataCollectionAgent.execute_preset_workflow(
        agent,
        topic="AI",
        workflow_steps=["knowledge_base_search", "real_time_collection", "data_aggregation"],
        save_to_db=False
    )

    assert result["total_count"] == len(result["collected_data"]) == 0
    assert result["summary"]["total_items"] == result["total_count"]
    assert result["message"] == "成功收集 0 条数据"


def test_data_collection_node_total_count_consistency_normal(monkeypatch):
    """正常采集：node 返回 total_count 与 collected_data 长度一致"""
    class _FakeAgent:
        def __init__(self, workflow_id: str, auto_save: bool = True):
            self.workflow_id = workflow_id
            self.auto_save = auto_save

        def execute_preset_workflow(self, topic, workflow_steps=None, save_to_db=None):
            return {
                "collected_data": [{"id": "1"}, {"id": "2"}],
                "total_count": 999,
                "message": "成功收集 999 条数据"
            }

    monkeypatch.setattr(data_collection_node_module, "DataCollectionAgent", _FakeAgent)

    node = DataCollectionAgentNode(_build_data_collection_node_definition("AI"))
    state = WorkflowState(workflow_id=None)
    result = node.execute(state)

    assert result["total_count"] == len(result["collected_data"]) == 2
    assert result["message"] == "成功收集 2 条数据"


def test_data_collection_node_total_count_consistency_empty(monkeypatch):
    """空数据：node 返回 total_count 与 collected_data 长度一致"""
    class _FakeAgent:
        def __init__(self, workflow_id: str, auto_save: bool = True):
            self.workflow_id = workflow_id
            self.auto_save = auto_save

        def execute_preset_workflow(self, topic, workflow_steps=None, save_to_db=None):
            return {
                "collected_data": [],
                "total_count": 9,
                "message": "成功收集 9 条数据"
            }

    monkeypatch.setattr(data_collection_node_module, "DataCollectionAgent", _FakeAgent)

    node = DataCollectionAgentNode(_build_data_collection_node_definition("AI"))
    state = WorkflowState(workflow_id=None)
    result = node.execute(state)

    assert result["total_count"] == len(result["collected_data"]) == 0
    assert result["message"] == "成功收集 0 条数据"


if __name__ == "__main__":
    test_node_instantiation()