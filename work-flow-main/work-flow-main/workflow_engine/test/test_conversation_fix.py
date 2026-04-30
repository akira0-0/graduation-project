#!/usr/bin/env python3
"""
测试修复后的AI对话服务
验证 workflow_id 未定义错误是否已修复
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.ai_conversation_service import AIConversationService
from src.services.workflow_service import WorkflowService
from src.database.connection import get_session
from src.database.repositories import WorkflowRepository, ConversationRepository


def test_workflow_id_fix():
    """测试 workflow_id 错误修复"""
    print("=" * 60)
    print("测试修复后的AI对话服务")
    print("=" * 60)
    
    try:
        # 初始化服务
        print("\n步骤1: 初始化服务...")
        session = get_session()
        workflow_repo = WorkflowRepository(session)
        conversation_repo = ConversationRepository(session)
        workflow_service = WorkflowService(
            workflow_repo=workflow_repo, 
            conversation_repo=conversation_repo
        )
        
        service = AIConversationService(workflow_service=workflow_service)
        print("✅ 服务初始化成功")
        
        # 测试 start_conversation
        print("\n步骤2: 测试开始对话...")
        result = service.start_conversation(
            user_intent="创建一个简单的数据处理工作流",
            workflow_type="data_processing"
        )
        
        # 验证结果
        print("\n步骤3: 验证结果...")
        assert "workflow_id" in result, "结果中缺少 workflow_id 字段"
        assert result["workflow_id"] is not None, "workflow_id 为 None"
        assert "workflow" in result, "结果中缺少 workflow 字段"
        assert "conversation_id" in result, "结果中缺少 conversation_id 字段"
        
        print(f"✅ workflow_id: {result['workflow_id']}")
        print(f"✅ conversation_id: {result['conversation_id']}")
        print(f"✅ workflow 名称: {result['workflow'].name}")
        print(f"✅ message: {result['message']}")
        
        # 测试继续对话
        print("\n步骤4: 测试继续对话...")
        result2 = service.continue_conversation(
            workflow_id=result["workflow_id"],
            user_message="添加一个数据验证节点"
        )
        
        assert "workflow_id" in result2, "继续对话结果中缺少 workflow_id 字段"
        assert result2["workflow_id"] is not None, "继续对话的 workflow_id 为 None"
        print(f"✅ 继续对话成功，workflow_id: {result2['workflow_id']}")
        
        # 测试获取历史
        print("\n步骤5: 测试获取对话历史...")
        history = service.get_conversation_history(
            workflow_id=result["workflow_id"],
            limit=5
        )
        
        assert "conversations" in history, "历史记录中缺少 conversations 字段"
        print(f"✅ 获取到 {len(history['conversations'])} 条对话记录")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        return True
        
    except Exception as e:
        import traceback
        print("\n" + "=" * 60)
        print("❌ 测试失败:")
        print("=" * 60)
        print(f"错误: {str(e)}")
        print(traceback.format_exc())
        return False
    finally:
        if 'session' in locals():
            session.close()


if __name__ == "__main__":
    success = test_workflow_id_fix()
    sys.exit(0 if success else 1)