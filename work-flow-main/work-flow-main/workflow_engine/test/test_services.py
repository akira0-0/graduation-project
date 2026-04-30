#!/usr/bin/env python3
"""
Service 层单元测试
测试 PlannerService、WorkflowService、ExecutionService、AgentService 的核心功能
"""
import os
import sys
import types
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# 添加项目根目录到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from workflow_engine.src.services import PlannerService, WorkflowService, ExecutionService, AgentService
from workflow_engine.src.services.workflow_service import (
    WorkflowSaveError,
    ERROR_CODE_WORKFLOW_SAVE_FAILED
)
from workflow_engine.src.core.schema import WorkflowDefinition, NodeDefinition, EdgeDefinition, NodeConfig
from workflow_engine.src.planner.llm_planner import (
    parse_workflow_json_output,
    WorkflowJSONProcessingError
)


# ==================== 测试数据 ====================

def create_sample_workflow():
    """创建示例工作流定义"""
    return WorkflowDefinition(
        name="测试工作流",
        description="用于测试的示例工作流",
        nodes=[
            NodeDefinition(
                id="start_1",
                type="Start",
                config=NodeConfig(title="开始", description="开始节点")
            ),
            NodeDefinition(
                id="end_1",
                type="End",
                config=NodeConfig(title="结束", description="结束节点")
            )
        ],
        edges=[
            EdgeDefinition(id="edge_1", source="start_1", target="end_1")
        ]
    )


# ==================== PlannerService 测试 ====================

class TestPlannerService:
    """PlannerService 单元测试"""
    
    def test_init_default_model(self):
        """测试默认模型初始化"""
        service = PlannerService()
        assert service.model_name == "deepseek-chat"
    
    def test_init_custom_model(self):
        """测试自定义模型初始化"""
        service = PlannerService(model_name="gpt-4")
        assert service.model_name == "gpt-4"
    
    def test_validate_workflow_valid(self):
        """测试验证有效工作流"""
        service = PlannerService()
        workflow = create_sample_workflow()
        assert service.validate_workflow(workflow) is True
    
    def test_validate_workflow_no_nodes(self):
        """测试验证无节点工作流"""
        service = PlannerService()
        workflow = WorkflowDefinition(
            name="空工作流",
            description="无节点",
            nodes=[],
            edges=[]
        )
        assert service.validate_workflow(workflow) is False
    
    def test_validate_workflow_no_start(self):
        """测试验证无开始节点工作流"""
        service = PlannerService()
        workflow = WorkflowDefinition(
            name="无开始节点",
            description="无开始节点",
            nodes=[
                NodeDefinition(
                    id="end_1",
                    type="End",
                    config=NodeConfig(title="结束", description="结束节点")
                )
            ],
            edges=[]
        )
        assert service.validate_workflow(workflow) is False
    
    def test_validate_workflow_no_end(self):
        """测试验证无结束节点工作流"""
        service = PlannerService()
        workflow = WorkflowDefinition(
            name="无结束节点",
            description="无结束节点",
            nodes=[
                NodeDefinition(
                    id="start_1",
                    type="Start",
                    config=NodeConfig(title="开始", description="开始节点")
                )
            ],
            edges=[]
        )
        assert service.validate_workflow(workflow) is False
    
    @patch('workflow_engine.src.services.planner_service.LLMPlanner')
    def test_generate_workflow_mock(self, mock_planner_class):
        """测试生成工作流（Mock）"""
        # 设置 Mock
        mock_planner = Mock()
        mock_workflow = create_sample_workflow()
        mock_planner.plan.return_value = mock_workflow
        mock_planner_class.return_value = mock_planner
        
        service = PlannerService()
        result = service.generate_workflow("测试意图", "test-model")
        
        assert result is not None
        assert result.name == "测试工作流"


# ==================== JSON 解析与修复测试 ====================

class TestWorkflowJsonProcessing:
    """工作流 JSON 提取、修复、结构校验测试"""

    def test_malformed_json_repair_success(self):
        """测试 malformed JSON 在有限修复后成功解析"""
        malformed_output = """这里是结果：
```json
{
  “name”: “测试工作流”,
  “description”: “测试描述”,
  “nodes”: [
    {
      “id”: “start_1”,
      “type”: “Start”,
      “config”: {“title”: “开始”, “description”: “开始节点”,}
    },
    {
      “id”: “end_1”,
      “type”: “End”,
      “config”: {“title”: “结束”, “description”: “结束节点”,}
    },
  ],
  “edges”: [
    {“source”: “start_1”, “target”: “end_1”,},
  ],
}
```
"""
        parsed = parse_workflow_json_output(malformed_output)

        assert parsed["name"] == "测试工作流"
        assert len(parsed["nodes"]) == 2
        assert len(parsed["edges"]) == 1
        assert parsed["nodes"][0]["id"] == "start_1"
        assert parsed["edges"][0]["target"] == "end_1"

    def test_malformed_json_repair_failed(self):
        """测试 malformed JSON 修复失败可被识别"""
        invalid_output = """```json
{
  "name": "坏工作流",
  "description": "缺少核心字段"
}
```"""
        with pytest.raises(WorkflowJSONProcessingError) as exc_info:
            parse_workflow_json_output(invalid_output)

        assert exc_info.value.stage == "structure_validation"
        assert "缺少核心字段" in str(exc_info.value)


# ==================== WorkflowService 测试 ====================

class TestWorkflowService:
    """WorkflowService 单元测试"""
    
    def test_init_with_repos(self):
        """测试带仓储初始化"""
        mock_workflow_repo = Mock()
        mock_conversation_repo = Mock()
        mock_planner_service = Mock()
        
        service = WorkflowService(
            workflow_repo=mock_workflow_repo,
            conversation_repo=mock_conversation_repo,
            planner_service=mock_planner_service
        )
        
        assert service.workflow_repo is mock_workflow_repo
        assert service.conversation_repo is mock_conversation_repo
        assert service._planner_service is mock_planner_service
    
    def test_init_without_repos(self):
        """测试无仓储初始化（懒加载）"""
        service = WorkflowService(workflow_repo=None)
        assert service.workflow_repo is None
        # planner_service 应该懒加载
        assert service._planner_service is None
    
    def test_get_workflow(self):
        """测试获取工作流"""
        mock_workflow_repo = Mock()
        mock_workflow = Mock()
        mock_workflow.id = "test-id"
        mock_workflow_repo.get_by_id.return_value = mock_workflow
        
        service = WorkflowService(workflow_repo=mock_workflow_repo)
        result = service.get_workflow("test-id")
        
        mock_workflow_repo.get_by_id.assert_called_once_with("test-id")
        assert result is mock_workflow
    
    def test_get_workflows(self):
        """测试获取工作流列表"""
        mock_workflow_repo = Mock()
        mock_workflows = [Mock(id="1"), Mock(id="2")]
        mock_workflow_repo.get_all.return_value = mock_workflows
        
        service = WorkflowService(workflow_repo=mock_workflow_repo)
        result = service.get_workflows(skip=0, limit=10)
        
        mock_workflow_repo.get_all.assert_called_once_with(skip=0, limit=10)
        assert len(result) == 2
    
    def test_delete_workflow(self):
        """测试删除工作流"""
        mock_workflow_repo = Mock()
        mock_workflow_repo.delete.return_value = True
        
        service = WorkflowService(workflow_repo=mock_workflow_repo)
        result = service.delete_workflow("test-id", soft_delete=True)
        
        mock_workflow_repo.delete.assert_called_once_with("test-id")
        assert result is True
    
    def test_workflow_exists(self):
        """测试检查工作流是否存在"""
        mock_workflow_repo = Mock()
        mock_workflow_repo.get_by_id.return_value = Mock()
        
        service = WorkflowService(workflow_repo=mock_workflow_repo)
        result = service.workflow_exists("test-id")
        
        assert result is True
        
        mock_workflow_repo.get_by_id.return_value = None
        result = service.workflow_exists("non-existent")
        assert result is False

    def test_save_workflow_failure_returns_structured_error(self):
        """测试保存失败时抛出结构化错误"""
        mock_workflow_repo = Mock()
        mock_workflow_repo.create_from_dict.side_effect = RuntimeError("db down")

        mock_planner_service = Mock()
        mock_planner_service.validate_workflow.return_value = True

        service = WorkflowService(
            workflow_repo=mock_workflow_repo,
            planner_service=mock_planner_service
        )

        with pytest.raises(WorkflowSaveError) as exc_info:
            service.save_workflow(
                create_sample_workflow(),
                request_id="req-1",
                conversation_id="conv-1"
            )

        err = exc_info.value
        assert err.code == ERROR_CODE_WORKFLOW_SAVE_FAILED
        assert err.message == "保存工作流失败"
        assert err.details["workflow_name"] == "测试工作流"
        assert err.details["error_type"] == "database_save_error"
        assert err.details["stage"] == "save_workflow"
        assert err.details["request_id"] == "req-1"
        assert err.details["conversation_id"] == "conv-1"
        assert "RuntimeError: db down" in err.details["error_summary"]

    @patch("workflow_engine.src.services.workflow_service.logger")
    def test_save_workflow_failure_logs_observability_fields(self, mock_logger):
        """测试保存失败时日志包含可观测字段"""
        mock_workflow_repo = Mock()
        mock_workflow_repo.create_from_dict.side_effect = RuntimeError("db down")

        mock_planner_service = Mock()
        mock_planner_service.validate_workflow.return_value = True

        service = WorkflowService(
            workflow_repo=mock_workflow_repo,
            planner_service=mock_planner_service
        )

        with pytest.raises(WorkflowSaveError):
            service.save_workflow(
                create_sample_workflow(),
                request_id="req-2",
                conversation_id="conv-2"
            )

        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args.kwargs
        assert call_kwargs["workflow_name"] == "测试工作流"
        assert call_kwargs["error_type"] == "database_save_error"
        assert "RuntimeError: db down" in call_kwargs["error_summary"]
        assert call_kwargs["request_id"] == "req-2"
        assert call_kwargs["conversation_id"] == "conv-2"


# ==================== ConversationManager 测试 ====================

class TestConversationManagerContextRecovery:
    """ConversationManager 会话上下文恢复测试"""

    def _build_manager_with_mocks(self):
        fake_memory_module = types.ModuleType("langchain.memory")
        fake_memory_module.ConversationBufferMemory = Mock
        fake_chains_module = types.ModuleType("langchain.chains")
        fake_chains_module.ConversationChain = Mock

        with patch.dict(
            sys.modules,
            {
                "langchain.memory": fake_memory_module,
                "langchain.chains": fake_chains_module
            }
        ):
            from workflow_engine.src.services.conversation_manager import ConversationManager

            manager = ConversationManager.__new__(ConversationManager)
            manager.contexts = {}
            manager.conversation_repo = Mock()
            manager.workflow_repo = Mock()
            manager._handle_general = Mock(return_value={"type": "general", "message": "好的，继续"})
            return manager

    def _sample_workflow_definition(self):
        return {
            "name": "恢复测试工作流",
            "description": "用于上下文恢复测试",
            "nodes": [
                {"id": "start", "type": "Start", "config": {"title": "开始", "params": {}}},
                {"id": "end", "type": "End", "config": {"title": "结束", "params": {}}}
            ],
            "edges": [
                {"source": "start", "target": "end"}
            ],
            "variables": {}
        }

    def test_continue_recovers_from_db_when_memory_missing(self):
        """内存缺失但 DB 有记录时，可恢复并继续对话"""
        manager = self._build_manager_with_mocks()

        first_record = Mock()
        first_record.id = "rec-1"
        first_record.workflow_id = "wf-1"
        first_record.user_message = "请帮我分析某产品舆情"
        first_record.assistant_response = "已创建工作流"
        first_record.context = {
            "conversation_id": "conv-recover",
            "task_plan": {
                "main_task": "分析产品舆情",
                "subtasks": [],
                "workflow_type": "public_opinion_analysis",
                "required_agents": ["DataCollectionAgent"],
                "estimated_steps": 1,
                "complexity": "simple"
            }
        }
        first_record.timestamp = datetime(2026, 1, 1, 10, 0, 0)

        second_record = Mock()
        second_record.id = "rec-2"
        second_record.workflow_id = "wf-1"
        second_record.user_message = "补充一点来源"
        second_record.assistant_response = "收到"
        second_record.context = {"conversation_id": "conv-recover"}
        second_record.timestamp = datetime(2026, 1, 1, 10, 5, 0)

        manager.conversation_repo.get_by_context_conversation_id.return_value = [first_record, second_record]

        workflow_entity = Mock()
        workflow_entity.definition = self._sample_workflow_definition()
        manager.workflow_repo.get_by_id.return_value = workflow_entity

        result = manager.continue_conversation("conv-recover", "继续推进")

        assert result["message"] == "好的，继续"
        assert "conv-recover" in manager.contexts
        restored_context = manager.contexts["conv-recover"]
        assert restored_context.workflow_id == "wf-1"
        assert restored_context.current_workflow is not None
        assert len(restored_context.messages) >= 4

        manager.conversation_repo.create_conversation.assert_called_once()
        persist_kwargs = manager.conversation_repo.create_conversation.call_args.kwargs
        assert persist_kwargs["workflow_id"] == "wf-1"

    def test_continue_fallback_when_db_record_incomplete(self):
        """DB 记录残缺时可安全降级，不直接崩溃"""
        manager = self._build_manager_with_mocks()
        manager._handle_general.return_value = {"type": "general", "message": "降级继续"}

        incomplete_record = Mock()
        incomplete_record.id = "rec-incomplete"
        incomplete_record.workflow_id = None
        incomplete_record.user_message = "历史问题"
        incomplete_record.assistant_response = None
        incomplete_record.context = {"conversation_id": "conv-incomplete"}
        incomplete_record.timestamp = datetime(2026, 1, 1, 11, 0, 0)

        manager.conversation_repo.get_by_context_conversation_id.return_value = [incomplete_record]

        result = manager.continue_conversation("conv-incomplete", "请修改一下流程")

        assert result["type"] == "general_fallback"
        assert "缺少可用工作流信息" in result["message"]
        manager.conversation_repo.create_conversation.assert_not_called()

    def test_continue_raises_when_db_has_no_record(self):
        """DB 无记录时返回可识别错误"""
        manager = self._build_manager_with_mocks()
        manager.conversation_repo.get_by_context_conversation_id.return_value = []

        with pytest.raises(ValueError, match="对话不存在"):
            manager.continue_conversation("conv-missing", "继续")

        manager.conversation_repo.create_conversation.assert_not_called()


# ==================== ExecutionService 测试 ====================

class TestExecutionService:
    """ExecutionService 单元测试"""
    
    def test_init_with_repos(self):
        """测试带仓储初始化"""
        mock_workflow_repo = Mock()
        mock_audit_log_repo = Mock()
        
        service = ExecutionService(
            workflow_repo=mock_workflow_repo,
            audit_log_repo=mock_audit_log_repo
        )
        
        assert service.workflow_repo is mock_workflow_repo
        assert service.audit_log_repo is mock_audit_log_repo
    
    def test_init_without_repos(self):
        """测试无仓储初始化"""
        service = ExecutionService()
        assert service.workflow_repo is None
        assert service.audit_log_repo is None
    
    def test_validate_workflow_for_execution(self):
        """测试验证工作流可执行性"""
        service = ExecutionService()
        workflow = create_sample_workflow()
        
        result = service.validate_workflow_for_execution(workflow)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_workflow_no_nodes(self):
        """测试验证无节点工作流"""
        service = ExecutionService()
        workflow = WorkflowDefinition(
            name="空工作流",
            description="无节点",
            nodes=[],
            edges=[]
        )
        
        result = service.validate_workflow_for_execution(workflow)
        
        assert result["valid"] is False
        assert "没有定义任何节点" in result["errors"][0]
    
    def test_get_execution_report_not_found(self):
        """测试获取不存在的执行报告"""
        service = ExecutionService()
        result = service.get_execution_report("non-existent-id")
        assert result is None
    
    @patch('workflow_engine.src.services.execution_service.GraphBuilder')
    def test_execute_workflow_langgraph_mock(self, mock_builder_class):
        """测试执行工作流（Mock LangGraph）"""
        # 设置 Mock
        mock_builder = Mock()
        mock_graph = Mock()
        mock_graph.invoke.return_value = {"node_outputs": {"node1": "result1"}}
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder
        
        service = ExecutionService()
        workflow = create_sample_workflow()
        
        result = service.execute_workflow(
            workflow_def=workflow,
            engine="langgraph",
            enable_monitoring=False
        )
        
        assert result["status"] == "completed"
        assert "result" in result


# ==================== AgentService 测试 ====================

class TestAgentService:
    """AgentService 单元测试"""
    
    def test_init_with_repos(self):
        """测试带仓储初始化"""
        mock_memory_repo = Mock()
        mock_planner_service = Mock()
        
        service = AgentService(
            memory_repo=mock_memory_repo,
            planner_service=mock_planner_service
        )
        
        assert service.memory_repo is mock_memory_repo
        assert service._planner_service is mock_planner_service
    
    def test_init_without_repos(self):
        """测试无仓储初始化"""
        service = AgentService()
        assert service.memory_repo is None
        assert service._planner_service is None
    
    def test_get_agent_templates(self):
        """测试获取智能体模板"""
        mock_planner_service = Mock()
        mock_planner_service.get_agent_templates.return_value = {
            "DataCollectionAgent": {"role": "数据收集专家"},
            "SentimentAgent": {"role": "情感分析专家"}
        }
        
        service = AgentService(planner_service=mock_planner_service)
        result = service.get_agent_templates()
        
        assert "DataCollectionAgent" in result
        assert "SentimentAgent" in result
    
    def test_get_agent_template(self):
        """测试获取单个智能体模板"""
        mock_planner_service = Mock()
        mock_planner_service.get_agent_templates.return_value = {
            "DataCollectionAgent": {"role": "数据收集专家"}
        }
        
        service = AgentService(planner_service=mock_planner_service)
        result = service.get_agent_template("DataCollectionAgent")
        
        assert result is not None
        assert result["role"] == "数据收集专家"
    
    def test_get_agent_template_not_found(self):
        """测试获取不存在的智能体模板"""
        mock_planner_service = Mock()
        mock_planner_service.get_agent_templates.return_value = {}
        
        service = AgentService(planner_service=mock_planner_service)
        result = service.get_agent_template("NonExistentAgent")
        
        assert result is None
    
    def test_save_agent_memory_no_repo(self):
        """测试保存记忆（无仓储）"""
        service = AgentService(memory_repo=None)
        result = service.save_agent_memory(
            workflow_id="test-id",
            agent_type="TestAgent",
            memory_type="knowledge",
            key="test_key",
            value="test_value"
        )
        assert result is None
    
    def test_get_agent_memory_no_repo(self):
        """测试获取记忆（无仓储）"""
        service = AgentService(memory_repo=None)
        result = service.get_agent_memory(
            workflow_id="test-id",
            agent_type="TestAgent"
        )
        assert result == []


# ==================== 运行测试 ====================

def run_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("运行 Service 层单元测试")
    print("="*60)
    
    # 运行 pytest
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    return exit_code


if __name__ == "__main__":
    run_tests()