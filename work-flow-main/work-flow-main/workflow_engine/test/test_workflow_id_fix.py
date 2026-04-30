#!/usr/bin/env python3
"""
测试 workflow_id 错误修复
验证在没有数据库的情况下，workflow_id 错误处理是否正确
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, MagicMock
from src.services.ai_conversation_service import AIConversationService
from src.core.schema import WorkflowDefinition


def test_workflow_id_error_handling():
    """测试 workflow_id 错误处理"""
    print("=" * 60)
    print("测试 workflow_id 错误处理")
    print("=" * 60)
    
    # 创建 Mock 对象
    mock_workflow_service = Mock()
    mock_conversation_repo = Mock()
    
    # 测试场景1: generate_workflow 返回成功保存的工作流
    print("\n测试场景1: 正常情况 - 工作流成功保存")
    print("-" * 60)
    
    # 创建一个有效的 WorkflowDefinition
    valid_workflow = WorkflowDefinition(
        name="测试工作流",
        description="测试工作流描述",
        nodes=[
            {"id": "start", "type": "Start", "config": {"title": "开始", "params": {}}},
            {"id": "end", "type": "End", "config": {"title": "结束", "params": {}}}
        ],
        edges=[
            {"source": "start", "target": "end"}
        ]
    )
    
    # 模拟 generate_workflow 返回成功保存的结果
    mock_workflow_service.generate_workflow.return_value = {
        "workflow": valid_workflow,
        "workflow_id": "test-workflow-id-123",
        "status": "success",
        "metadata": {}
    }
    
    # 模拟对话记录创建
    mock_conversation = Mock()
    mock_conversation.id = "test-conversation-id-456"
    mock_conversation_repo.create_conversation.return_value = mock_conversation
    
    # 创建服务实例
    service = AIConversationService(workflow_service=mock_workflow_service)
    service.conversation_repo = mock_conversation_repo
    
    # 执行测试
    try:
        result = service.start_conversation(
            user_intent="创建一个测试工作流",
            workflow_type="test"
        )
        
        # 验证结果
        assert "workflow_id" in result, "结果中缺少 workflow_id 字段"
        assert result["workflow_id"] == "test-workflow-id-123", "workflow_id 值不正确"
        assert "workflow" in result, "结果中缺少 workflow 字段"
        assert "conversation_id" in result, "结果中缺少 conversation_id 字段"
        
        print("✅ 测试通过！")
        print(f"   workflow_id: {result['workflow_id']}")
        print(f"   conversation_id: {result['conversation_id']}")
        print(f"   workflow 名称: {result['workflow'].name}")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False
    
    # 测试场景2: generate_workflow 返回没有 workflow_id 的结果（保存失败）
    print("\n测试场景2: 异常情况 - 工作流保存失败")
    print("-" * 60)
    
    # 模拟 generate_workflow 返回没有 workflow_id 的结果（保存失败）
    mock_workflow_service.generate_workflow.return_value = {
        "workflow": valid_workflow,
        "status": "success",  # 虽然返回 success，但没有 workflow_id
        "metadata": {}
        # 缺少 "workflow_id" 字段
    }
    
    # 执行测试
    try:
        result = service.start_conversation(
            user_intent="创建另一个测试工作流",
            workflow_type="test"
        )
        
        # 应该抛出错误
        print("❌ 测试失败: 应该抛出错误但没有抛出")
        return False
        
    except ValueError as e:
        # 预期的错误
        if "workflow_id 为空" in str(e) or "工作流保存失败" in str(e):
            print("✅ 测试通过！正确抛出了错误:")
            print(f"   错误信息: {str(e)}")
        else:
            print(f"❌ 测试失败: 错误信息不正确 - {str(e)}")
            return False
    except Exception as e:
        print(f"❌ 测试失败: 抛出了意外的错误类型 - {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_workflow_id_error_handling()
    sys.exit(0 if success else 1)