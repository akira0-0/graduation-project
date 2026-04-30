"""
会话上下文恢复 - 真实数据库集成测试（SQLite）
覆盖迁移/脏数据场景，禁止 mock ConversationRepository/ConversationManager
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from types import MethodType

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
import types

# 兼容部分环境缺失旧版 langchain 模块路径（仅用于测试导入）
if "langchain.memory" not in sys.modules:
    memory_module = types.ModuleType("langchain.memory")

    class _DummyConversationBufferMemory:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            pass

    memory_module.ConversationBufferMemory = _DummyConversationBufferMemory
    sys.modules["langchain.memory"] = memory_module

if "langchain.chains" not in sys.modules:
    chains_module = types.ModuleType("langchain.chains")

    class _DummyConversationChain:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            pass

        def predict(self, **kwargs):
            return kwargs.get("input", "")

    chains_module.ConversationChain = _DummyConversationChain
    sys.modules["langchain.chains"] = chains_module

from workflow_engine.src.database.models import Base, Workflow, Conversation
from workflow_engine.src.database.repositories import ConversationRepository, WorkflowRepository
from workflow_engine.src.services.conversation_manager import ConversationManager


def _minimal_workflow_definition(name: str = "恢复测试工作流") -> dict:
    return {
        "name": name,
        "description": "用于会话恢复测试",
        "nodes": [
            {"id": "start", "type": "Start", "config": {"title": "开始", "params": {}}},
            {"id": "end", "type": "End", "config": {"title": "结束", "params": {}}}
        ],
        "edges": [{"source": "start", "target": "end"}],
        "variables": {}
    }


def _insert_workflow(db_session, workflow_id: str, definition: dict) -> str:
    workflow_repo = WorkflowRepository(db_session)
    workflow_repo.create(
        Workflow(
            id=workflow_id,
            name=definition.get("name", "测试工作流"),
            description=definition.get("description"),
            definition=definition,
            is_active=True
        )
    )
    return workflow_id


def _insert_conversation(
    db_session,
    workflow_id: str,
    user_message: str,
    assistant_response: str,
    context: dict | None,
    timestamp: datetime
) -> None:
    repo = ConversationRepository(db_session)
    repo.create(
        Conversation(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_message=user_message,
            assistant_response=assistant_response,
            context=context,
            timestamp=timestamp
        )
    )


def _build_manager(db_session) -> ConversationManager:
    """构造可用的 ConversationManager 实例（不走 __init__，避免外部 LLM 依赖）"""
    manager = ConversationManager.__new__(ConversationManager)
    manager.conversation_repo = ConversationRepository(db_session)
    manager.workflow_repo = WorkflowRepository(db_session)
    manager.contexts = {}
    manager.memory = None
    manager.llm = None
    manager.planning_agent = None
    manager.orchestrator = None

    def _fake_general(self, context, user_input):
        return {"type": "general", "message": f"general:{user_input}"}

    manager._handle_general = MethodType(_fake_general, manager)
    return manager


@pytest.fixture
def sqlite_db_session(tmp_path):
    db_file = tmp_path / "conversation_recovery_integration.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.mark.integration
class TestConversationContextRecoveryDB:
    def test_restore_after_migration_and_continue_success(self, sqlite_db_session):
        """
        场景A:
        正常迁移后数据可恢复（至少两条同会话记录），清空内存后 continue 触发恢复成功
        """
        workflow_id = "wf_a"
        conversation_id = "conv_a"
        _insert_workflow(sqlite_db_session, workflow_id, _minimal_workflow_definition("A工作流"))

        base_ts = datetime.utcnow()
        _insert_conversation(
            sqlite_db_session,
            workflow_id=workflow_id,
            user_message="第一次用户消息",
            assistant_response='{"message":"第一次助手回复"}',
            context={"conversation_id": conversation_id},
            timestamp=base_ts
        )
        _insert_conversation(
            sqlite_db_session,
            workflow_id=workflow_id,
            user_message="第二次用户消息",
            assistant_response='{"message":"第二次助手回复"}',
            context={
                "conversation_id": conversation_id,
                "task_plan": {
                    "main_task": "迁移后恢复验证",
                    "subtasks": [],
                    "workflow_type": "custom",
                    "required_agents": [],
                    "estimated_steps": 2,
                    "complexity": "simple"
                }
            },
            timestamp=base_ts + timedelta(seconds=1)
        )

        manager = _build_manager(sqlite_db_session)
        assert conversation_id not in manager.contexts

        response = manager.continue_conversation(conversation_id, "继续往下聊")

        assert response["type"] == "general"
        restored = manager.contexts[conversation_id]
        assert restored.workflow_id == workflow_id
        assert restored.current_workflow is not None
        assert restored.task_plan is not None
        assert restored.task_plan.main_task == "迁移后恢复验证"

        restored_records = manager.conversation_repo.get_by_context_conversation_id(conversation_id)
        assert len(restored_records) == 3  # 2条历史 + 1条continue新增

    def test_dirty_context_missing_keys_fallback_or_recognizable_error(self, sqlite_db_session):
        """
        场景B:
        1) context 缺少/异常 workflow 信息 -> 走 general_fallback
        2) context 缺失 conversation_id -> 抛出可识别错误(ValueError)
        """
        manager = _build_manager(sqlite_db_session)
        base_ts = datetime.utcnow()

        # B1: workflow 定义损坏 + context 字段类型异常，触发 fallback
        bad_workflow_id = "wf_b1"
        _insert_workflow(
            sqlite_db_session,
            bad_workflow_id,
            {"name": "坏工作流", "description": "损坏定义"}  # 故意字段不全，无法恢复 WorkflowDefinition
        )
        _insert_conversation(
            sqlite_db_session,
            workflow_id=bad_workflow_id,
            user_message="请改一下流程",
            assistant_response='{"message":"历史回复"}',
            context={
                "conversation_id": "conv_b1",
                "workflow_id": {"invalid": True},
                "current_workflow": "not-a-dict"
            },
            timestamp=base_ts
        )

        fallback_response = manager.continue_conversation("conv_b1", "请修改流程")
        assert fallback_response["type"] == "general_fallback"
        assert "缺少可用工作流信息" in fallback_response["message"]

        # B2: context 缺失 conversation_id，恢复查询不到会话，返回可识别错误
        valid_workflow_id = "wf_b2"
        _insert_workflow(sqlite_db_session, valid_workflow_id, _minimal_workflow_definition("B2工作流"))
        _insert_conversation(
            sqlite_db_session,
            workflow_id=valid_workflow_id,
            user_message="没有conversation_id",
            assistant_response="纯文本历史",
            context={"workflow_id": valid_workflow_id},  # 故意缺失 conversation_id
            timestamp=base_ts + timedelta(seconds=1)
        )

        with pytest.raises(ValueError, match="对话不存在"):
            manager.continue_conversation("conv_b2_missing", "你好")

    def test_dirty_assistant_response_plain_text_and_broken_json_tolerated(self, sqlite_db_session):
        """
        场景C:
        assistant_response 为纯文本/损坏 JSON 时，恢复链路不中断并保留可用内容
        """
        workflow_id = "wf_c"
        conversation_id = "conv_c"
        _insert_workflow(sqlite_db_session, workflow_id, _minimal_workflow_definition("C工作流"))

        base_ts = datetime.utcnow()
        _insert_conversation(
            sqlite_db_session,
            workflow_id=workflow_id,
            user_message="用户消息1",
            assistant_response="这是纯文本助手回复",
            context={"conversation_id": conversation_id},
            timestamp=base_ts
        )
        _insert_conversation(
            sqlite_db_session,
            workflow_id=workflow_id,
            user_message="用户消息2",
            assistant_response='{"message":"损坏JSON"',  # 故意破损
            context={"conversation_id": conversation_id},
            timestamp=base_ts + timedelta(seconds=1)
        )

        manager = _build_manager(sqlite_db_session)
        context = manager._load_context_from_db(conversation_id)

        assert context is not None
        assistant_messages = [m["content"] for m in context.messages if m["role"] == "assistant"]
        assert "这是纯文本助手回复" in assistant_messages
        assert '{"message":"损坏JSON"' in assistant_messages

        response = manager.continue_conversation(conversation_id, "继续")
        assert response["type"] == "general"

    def test_migration_compat_old_records_without_task_plan_and_user_intent(self, sqlite_db_session):
        """
        场景D:
        旧记录缺少 task_plan/user_intent 时，能恢复最小上下文并继续流程
        """
        workflow_id = "wf_d"
        conversation_id = "conv_d"
        _insert_workflow(sqlite_db_session, workflow_id, _minimal_workflow_definition("D工作流"))

        base_ts = datetime.utcnow()
        _insert_conversation(
            sqlite_db_session,
            workflow_id=workflow_id,
            user_message="旧版本首条消息",
            assistant_response="旧版本首条回复",
            context={"conversation_id": conversation_id},  # 无 task_plan / user_intent
            timestamp=base_ts
        )
        _insert_conversation(
            sqlite_db_session,
            workflow_id=workflow_id,
            user_message="旧版本第二条消息",
            assistant_response="旧版本第二条回复",
            context={"conversation_id": conversation_id},  # 仍无 task_plan / user_intent
            timestamp=base_ts + timedelta(seconds=1)
        )

        manager = _build_manager(sqlite_db_session)
        restored = manager._load_context_from_db(conversation_id)

        assert restored is not None
        assert restored.task_plan is None
        assert restored.user_intent == "旧版本首条消息"  # 按当前实现回落到首条 user_message
        assert restored.current_workflow is not None

        response = manager.continue_conversation(conversation_id, "继续处理这个任务")
        assert response["type"] == "general"