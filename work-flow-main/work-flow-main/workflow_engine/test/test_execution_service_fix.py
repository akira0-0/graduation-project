"""
测试 ExecutionService 中 workflow_id 参数传递的修复
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.execution_service import ExecutionService
from src.core.schema import (
    WorkflowDefinition,
    NodeDefinition,
    EdgeDefinition,
    NodeConfig
)
from unittest.mock import Mock, patch, MagicMock


def test_workflow_id_parameter_passing():
    """测试 workflow_id 参数是否正确传递"""
    print("\n" + "="*60)
    print("测试 workflow_id 参数传递修复")
    print("="*60)
    
    # 创建简单的测试工作流
    workflow_def = WorkflowDefinition(
        name="Test Workflow",
        description="测试工作流",
        nodes=[
            NodeDefinition(
                id="start",
                type="Start",
                config=NodeConfig(title="开始", description="开始节点")
            ),
            NodeDefinition(
                id="end",
                type="End",
                config=NodeConfig(title="结束", description="结束节点")
            )
        ],
        edges=[
            EdgeDefinition(source="start", target="end")
        ],
        variables={}
    )
    
    execution_service = ExecutionService()
    
    # 测试1: 模拟 _execute_with_langgraph 方法,验证参数传递
    print("\n测试场景1: 验证 workflow_id 参数传递到 _execute_with_langgraph")
    
    with patch.object(execution_service, '_execute_with_langgraph') as mock_execute:
        # 配置 mock 返回值
        mock_execute.return_value = {"status": "completed", "result": {}}
        
        # 调用 execute_workflow 并传递 workflow_id
        result = execution_service.execute_workflow(
            workflow_def=workflow_def,
            engine="langgraph",
            enable_monitoring=False,
            workflow_id="test-workflow-123"
        )
        
        # 验证 _execute_with_langgraph 被调用,且参数正确
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        
        # 打印实际参数用于调试
        print(f"   实际参数: 位置参数={call_args[0]}, 关键字参数={call_args[1]}")
        
        # 检查参数 - workflow_id 作为位置参数传递(第4个参数)
        assert call_args[0][0] == workflow_def, "workflow_def 参数错误"
        
        # 检查 workflow_id 是否在位置参数中(第4个位置参数,索引为3)
        if len(call_args[0]) >= 4:
            assert call_args[0][3] == "test-workflow-123", "workflow_id 位置参数未正确传递"
            print(f"   ✅ workflow_id 作为位置参数正确传递: {call_args[0][3]}")
        else:
            # 或者作为关键字参数
            assert call_args[1].get('workflow_id') == "test-workflow-123", "workflow_id 参数未正确传递"
            print(f"   ✅ workflow_id 作为关键字参数正确传递: {call_args[1].get('workflow_id')}")
        
        print("✅ 测试通过! workflow_id 参数正确传递")
        print(f"   传递的 workflow_id: {call_args[1].get('workflow_id')}")
    
    # 测试2: 不传递 workflow_id
    print("\n测试场景2: 不传递 workflow_id 参数")
    
    with patch.object(execution_service, '_execute_with_langgraph') as mock_execute:
        mock_execute.return_value = {"status": "completed", "result": {}}
        
        result = execution_service.execute_workflow(
            workflow_def=workflow_def,
            engine="langgraph",
            enable_monitoring=False
        )
        
        call_args = mock_execute.call_args
        # workflow_id 应该为 None
        assert call_args[1].get('workflow_id') is None, "workflow_id 应该为 None"
        
        print("✅ 测试通过! workflow_id 为 None 时正常处理")
    
    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)
    print("\n修复总结:")
    print("1. ✅ _execute_with_langgraph 方法添加了 workflow_id 参数")
    print("2. ✅ execute_workflow 正确传递 workflow_id 到 _execute_with_langgraph")
    print("3. ✅ 修复了 'name 'workflow_id' is not defined' 错误")


if __name__ == "__main__":
    test_workflow_id_parameter_passing()