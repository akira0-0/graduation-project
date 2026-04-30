#!/usr/bin/env python3
"""
API 接口测试
测试 FastAPI 路由和依赖注入功能
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from workflow_engine.api.server import app, get_ai_conversation_service
from workflow_engine.api.dependencies import (
    get_planner_service,
    get_workflow_service_dep,
    get_execution_service_dep
)
from workflow_engine.src.core.schema import WorkflowDefinition, NodeDefinition, EdgeDefinition, NodeConfig
from workflow_engine.src.planner.llm_planner import WorkflowJSONProcessingError
from workflow_engine.src.services.workflow_service import (
    WorkflowSaveError,
    ERROR_CODE_WORKFLOW_SAVE_FAILED
)


# ==================== 测试客户端 ====================

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_workflow_dict():
    """创建示例工作流字典（用于API请求）"""
    return {
        "name": "测试工作流",
        "description": "用于测试的示例工作流",
        "variables": {},
        "nodes": [
            {
                "id": "start_1",
                "type": "Start",
                "config": {
                    "title": "开始",
                    "description": "开始节点"
                }
            },
            {
                "id": "end_1",
                "type": "End",
                "config": {
                    "title": "结束",
                    "description": "结束节点"
                }
            }
        ],
        "edges": [
            {
                "id": "edge_1",
                "source": "start_1",
                "target": "end_1"
            }
        ]
    }


# ==================== 基础端点测试 ====================

class TestBasicEndpoints:
    """基础端点测试"""
    
    def test_root_endpoint(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "2.1.0"
        assert "architecture" in data
    
    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


# ==================== 工作流生成 API 测试 ====================

class TestWorkflowGenerationAPI:
    """工作流生成 API 测试"""
    
    @patch('workflow_engine.api.server.get_planner_service')
    def test_generate_workflow_success(self, mock_get_planner, client):
        """测试生成工作流成功"""
        # 设置 Mock
        mock_planner = Mock()
        mock_workflow = WorkflowDefinition(
            name="测试工作流",
            description="测试描述",
            nodes=[
                NodeDefinition(id="start_1", type="Start", config=NodeConfig(title="开始", description="开始")),
                NodeDefinition(id="end_1", type="End", config=NodeConfig(title="结束", description="结束"))
            ],
            edges=[EdgeDefinition(id="e1", source="start_1", target="end_1")]
        )
        mock_planner.generate_workflow.return_value = mock_workflow
        mock_get_planner.return_value = mock_planner
        
        response = client.post(
            "/api/v1/workflows/generate",
            json={
                "intent": "创建一个简单的数据处理流程",
                "model": "deepseek-chat"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "workflow" in data
        assert "metadata" in data
    
    def test_generate_workflow_with_error(self, client):
        """测试生成工作流失败返回结构化错误码"""
        mock_planner_service = Mock()
        mock_planner_service.generate_workflow.side_effect = Exception("测试错误")

        app.dependency_overrides[get_planner_service] = lambda: mock_planner_service
        try:
            response = client.post(
                "/api/v1/workflows/generate",
                json={
                    "intent": "创建工作流",
                    "model": "deepseek-chat"
                }
            )
        finally:
            app.dependency_overrides.pop(get_planner_service, None)

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "WORKFLOW_GENERATION_FAILED"
        assert data["detail"]["message"] == "生成工作流失败"
        assert data["detail"]["details"]["stage"] == "generate_workflow"


# ==================== 舆论分析 API 测试 ====================

class TestPublicOpinionAPI:
    """舆论分析 API 测试"""
    
    @patch('workflow_engine.api.server.get_planner_service')
    def test_generate_public_opinion_workflow_success(self, mock_get_planner, client):
        """测试生成舆论分析工作流成功"""
        # 设置 Mock
        mock_planner = Mock()
        mock_workflow = WorkflowDefinition(
            name="舆论分析工作流",
            description="分析舆论",
            nodes=[
                NodeDefinition(id="start_1", type="Start", config=NodeConfig(title="开始", description="开始")),
                NodeDefinition(id="data_1", type="DataCollectionAgent", config=NodeConfig(title="数据收集", description="收集数据")),
                NodeDefinition(id="end_1", type="End", config=NodeConfig(title="结束", description="结束"))
            ],
            edges=[
                EdgeDefinition(id="e1", source="start_1", target="data_1"),
                EdgeDefinition(id="e2", source="data_1", target="end_1")
            ]
        )
        mock_planner.generate_public_opinion_workflow.return_value = mock_workflow
        mock_get_planner.return_value = mock_planner
        
        response = client.post(
            "/api/v1/workflows/generate-public-opinion",
            json={
                "topic": "人工智能发展",
                "model": "deepseek-chat"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "workflow" in data
        assert data["metadata"]["workflow_type"] == "public_opinion_analysis"

    def test_generate_public_opinion_workflow_json_error(self, client):
        """测试舆论分析工作流 JSON 解析失败结构化错误码"""
        mock_planner_service = Mock()
        mock_planner_service.generate_public_opinion_workflow.side_effect = WorkflowJSONProcessingError(
            "JSON 解析失败",
            stage="parse_json"
        )

        app.dependency_overrides[get_planner_service] = lambda: mock_planner_service
        try:
            response = client.post(
                "/api/v1/workflows/generate-public-opinion",
                json={
                    "topic": "人工智能发展",
                    "model": "deepseek-chat"
                }
            )
        finally:
            app.dependency_overrides.pop(get_planner_service, None)

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "INVALID_LLM_WORKFLOW_JSON"
        assert data["detail"]["message"] == "LLM 返回的工作流 JSON 无效"
        assert data["detail"]["details"]["stage"] == "generate_public_opinion_workflow"
        assert data["detail"]["details"]["llm_stage"] == "parse_json"


class TestConversationAPI:
    """对话 API 测试"""

    def test_start_conversation_json_error(self, client):
        """测试 start 接口 JSON 异常返回结构化错误码"""
        mock_conversation_service = Mock()
        mock_conversation_service.start_conversation.side_effect = WorkflowJSONProcessingError(
            "JSON 解析失败",
            stage="parse_json"
        )

        app.dependency_overrides[get_ai_conversation_service] = lambda: mock_conversation_service
        try:
            response = client.post(
                "/api/v1/conversations/start",
                json={
                    "user_intent": "生成一个工作流",
                    "workflow_type": "general"
                }
            )
        finally:
            app.dependency_overrides.pop(get_ai_conversation_service, None)

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "INVALID_LLM_WORKFLOW_JSON"
        assert data["detail"]["message"] == "LLM 返回的工作流 JSON 无效"
        assert data["detail"]["details"]["stage"] == "start_conversation"
        assert data["detail"]["details"]["llm_stage"] == "parse_json"

    def test_continue_conversation_json_error(self, client):
        """测试 continue 接口 JSON 异常返回结构化错误码"""
        mock_conversation_service = Mock()
        mock_conversation_service.continue_conversation.side_effect = WorkflowJSONProcessingError(
            "结构校验失败",
            stage="structure_validation"
        )

        app.dependency_overrides[get_ai_conversation_service] = lambda: mock_conversation_service
        try:
            response = client.post(
                "/api/v1/conversations/continue",
                json={
                    "workflow_id": "wf-test",
                    "user_message": "请调整流程"
                }
            )
        finally:
            app.dependency_overrides.pop(get_ai_conversation_service, None)

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "INVALID_LLM_WORKFLOW_JSON"
        assert data["detail"]["message"] == "LLM 返回的工作流 JSON 无效"
        assert data["detail"]["details"]["stage"] == "continue_conversation"
        assert data["detail"]["details"]["llm_stage"] == "structure_validation"

    def test_continue_conversation_not_found_error(self, client):
        """测试 continue 接口会话不存在错误码"""
        mock_conversation_service = Mock()
        mock_conversation_service.continue_conversation.side_effect = ValueError("工作流不存在: wf-test")

        app.dependency_overrides[get_ai_conversation_service] = lambda: mock_conversation_service
        try:
            response = client.post(
                "/api/v1/conversations/continue",
                json={
                    "workflow_id": "wf-test",
                    "user_message": "请调整流程"
                }
            )
        finally:
            app.dependency_overrides.pop(get_ai_conversation_service, None)

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "CONVERSATION_NOT_FOUND"
        assert data["detail"]["message"] == "会话不存在"
        assert data["detail"]["details"]["stage"] == "continue_conversation"
        assert data["detail"]["details"]["workflow_id"] == "wf-test"


# ==================== 工作流执行 API 测试 ====================

class TestWorkflowExecutionAPI:
    """工作流执行 API 测试"""
    
    @patch('workflow_engine.api.server.get_execution_service_dep')
    def test_execute_workflow_success(self, mock_get_service, client, sample_workflow_dict):
        """测试执行工作流成功"""
        # 设置 Mock
        mock_service = Mock()
        mock_service.execute_workflow.return_value = {
            "status": "completed",
            "execution_id": "test-exec-123",
            "result": {"node1": "output1"},
            "summary": {"total_nodes": 2},
            "report_path": "/logs/report.json"
        }
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/v1/workflows/execute",
            json={
                "workflow": sample_workflow_dict,
                "engine": "langgraph",
                "enable_monitoring": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["execution_id"] == "test-exec-123"
    
    def test_execute_workflow_with_error(self, client, sample_workflow_dict):
        """测试执行工作流失败返回结构化错误码"""
        mock_service = Mock()
        mock_service.execute_workflow.side_effect = Exception("执行错误")

        app.dependency_overrides[get_execution_service_dep] = lambda: mock_service
        try:
            response = client.post(
                "/api/v1/workflows/execute",
                json={
                    "workflow": sample_workflow_dict,
                    "engine": "langgraph",
                    "enable_monitoring": False
                }
            )
        finally:
            app.dependency_overrides.pop(get_execution_service_dep, None)

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "WORKFLOW_EXECUTION_FAILED"
        assert data["detail"]["message"] == "工作流执行失败"
        assert data["detail"]["details"]["stage"] == "execute_workflow"


# ==================== 执行查询与报告 API 测试 ====================

class TestExecutionQueryAPI:
    """执行查询与报告 API 测试"""

    def test_get_execution_detail_found(self, client):
        """测试查询执行详情（存在）"""
        mock_service = Mock()
        mock_service.get_execution_by_id.return_value = {
            "execution_id": "exec-1",
            "workflow_id": "wf-1",
            "status": "completed",
            "started_at": "2026-03-13T10:00:00",
            "completed_at": "2026-03-13T10:00:02",
            "duration_ms": 2000,
            "trigger_source": "api",
            "error_message": None,
            "final_report_path": "logs/execution_report_exec-1.json",
            "created_at": "2026-03-13T10:00:00",
            "updated_at": "2026-03-13T10:00:02",
            "node_traces": [
                {
                    "execution_id": "exec-1",
                    "node_id": "n1",
                    "node_type": "ReportAgent",
                    "status": "completed",
                    "input_payload": {},
                    "output_payload": {"report_content": "ok"},
                    "error_message": None,
                    "started_at": "2026-03-13T10:00:00",
                    "completed_at": "2026-03-13T10:00:01",
                    "duration_ms": 1000,
                    "created_at": "2026-03-13T10:00:00"
                }
            ]
        }

        app.dependency_overrides[get_execution_service_dep] = lambda: mock_service
        try:
            response = client.get("/api/v1/executions/exec-1")
        finally:
            app.dependency_overrides.pop(get_execution_service_dep, None)

        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == "exec-1"
        assert data["workflow_id"] == "wf-1"
        assert isinstance(data["node_traces"], list)
        assert data["node_traces"][0]["node_id"] == "n1"

    def test_get_execution_detail_not_found(self, client):
        """测试查询执行详情（不存在）"""
        mock_service = Mock()
        mock_service.get_execution_by_id.return_value = None

        app.dependency_overrides[get_execution_service_dep] = lambda: mock_service
        try:
            response = client.get("/api/v1/executions/not-found")
        finally:
            app.dependency_overrides.pop(get_execution_service_dep, None)

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "EXECUTION_NOT_FOUND"
        assert data["detail"]["details"]["execution_id"] == "not-found"

    def test_list_workflow_executions_structure(self, client):
        """测试工作流执行历史列表结构"""
        mock_service = Mock()
        mock_service.list_workflow_executions.return_value = {
            "workflow_id": "wf-1",
            "total": 1,
            "limit": 20,
            "offset": 0,
            "items": [
                {
                    "execution_id": "exec-1",
                    "workflow_id": "wf-1",
                    "status": "completed",
                    "started_at": "2026-03-13T10:00:00",
                    "completed_at": "2026-03-13T10:00:02",
                    "duration_ms": 2000,
                    "trigger_source": "api",
                    "error_message": None,
                    "final_report_path": None,
                    "created_at": "2026-03-13T10:00:00",
                    "updated_at": "2026-03-13T10:00:02",
                    "node_traces": []
                }
            ]
        }

        app.dependency_overrides[get_execution_service_dep] = lambda: mock_service
        try:
            response = client.get("/api/v1/workflows/wf-1/executions?limit=20&offset=0")
        finally:
            app.dependency_overrides.pop(get_execution_service_dep, None)

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "wf-1"
        assert data["total"] == 1
        assert isinstance(data["items"], list)
        assert data["items"][0]["execution_id"] == "exec-1"

    def test_get_execution_report_found_and_not_found(self, client):
        """测试执行报告读取（存在与不存在）"""
        mock_service = Mock()
        mock_service.get_execution_report.side_effect = [
            {
                "execution_id": "exec-1",
                "report_path": "logs/execution_report_exec-1.json",
                "report_content": {"summary": "ok"},
                "source": "logs_default_path"
            },
            None
        ]

        app.dependency_overrides[get_execution_service_dep] = lambda: mock_service
        try:
            found_response = client.get("/api/v1/executions/exec-1/report")
            not_found_response = client.get("/api/v1/executions/exec-404/report")
        finally:
            app.dependency_overrides.pop(get_execution_service_dep, None)

        assert found_response.status_code == 200
        found_data = found_response.json()
        assert found_data["execution_id"] == "exec-1"
        assert "report_content" in found_data

        assert not_found_response.status_code == 404
        not_found_data = not_found_response.json()
        assert not_found_data["detail"]["code"] == "EXECUTION_REPORT_NOT_FOUND"
        assert not_found_data["detail"]["details"]["execution_id"] == "exec-404"


# ==================== 智能体模板 API 测试 ====================

class TestAgentTemplatesAPI:
    """智能体模板 API 测试"""
    
    @patch('workflow_engine.api.server.get_agent_service_dep')
    def test_get_agent_templates_success(self, mock_get_service, client):
        """测试获取智能体模板成功"""
        # 设置 Mock
        mock_service = Mock()
        mock_service.get_agent_templates.return_value = {
            "DataCollectionAgent": {
                "role": "数据收集专家",
                "goal": "从多种来源收集数据"
            },
            "SentimentAgent": {
                "role": "情感分析专家",
                "goal": "分析文本情感倾向"
            }
        }
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/agents/templates")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "templates" in data
        assert "DataCollectionAgent" in data["templates"]


# ==================== 工作流管理 API 测试 ====================

class TestWorkflowManagementAPI:
    """工作流管理 API 测试"""
    
    @patch('workflow_engine.api.server.get_workflow_service_dep')
    def test_get_workflows_success(self, mock_get_service, client):
        """测试获取工作流列表成功"""
        # 设置 Mock
        mock_service = Mock()
        mock_workflow1 = Mock()
        mock_workflow1.id = "wf-1"
        mock_workflow1.name = "工作流1"
        mock_workflow1.description = "描述1"
        mock_workflow1.created_at = None
        mock_workflow1.updated_at = None
        
        mock_workflow2 = Mock()
        mock_workflow2.id = "wf-2"
        mock_workflow2.name = "工作流2"
        mock_workflow2.description = "描述2"
        mock_workflow2.created_at = None
        mock_workflow2.updated_at = None
        
        mock_service.get_workflows.return_value = [mock_workflow1, mock_workflow2]
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/workflows")
        
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
    
    @patch('workflow_engine.api.server.get_workflow_service_dep')
    def test_get_workflows_empty(self, mock_get_service, client):
        """测试获取空工作流列表"""
        # 设置 Mock
        mock_service = Mock()
        mock_service.get_workflows.side_effect = Exception("数据库未初始化")
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/v1/workflows")
        
        # 即使出错也应该返回空列表
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert data["workflows"] == []
    
    def test_save_workflow_failure_returns_structured_error(self, client):
        """测试保存失败时返回统一结构化错误"""
        mock_service = Mock()
        mock_service.get_workflow.return_value = Mock(id="wf-1")
        mock_service.update_workflow_definition.side_effect = WorkflowSaveError(
            message="保存工作流失败",
            details={
                "error_type": "database_update_error",
                "error_summary": "RuntimeError: db down",
                "workflow_name": "测试工作流",
                "stage": "update_workflow_definition"
            }
        )

        app.dependency_overrides[get_workflow_service_dep] = lambda: mock_service
        try:
            response = client.put(
                "/api/v1/workflows/wf-1",
                json={"name": "测试工作流"},
                headers={
                    "X-Request-ID": "req-api-1",
                    "X-Conversation-ID": "conv-api-1"
                }
            )
        finally:
            app.dependency_overrides.pop(get_workflow_service_dep, None)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"]["code"] == ERROR_CODE_WORKFLOW_SAVE_FAILED
        assert data["detail"]["message"] == "保存工作流失败"
        assert data["detail"]["details"]["workflow_name"] == "测试工作流"
        assert data["detail"]["details"]["error_type"] == "database_update_error"
        assert data["detail"]["details"]["error_summary"] == "RuntimeError: db down"
        assert data["detail"]["details"]["request_id"] == "req-api-1"
        assert data["detail"]["details"]["conversation_id"] == "conv-api-1"

    @patch('workflow_engine.api.server.get_workflow_service_dep')
    def test_delete_workflow_success(self, mock_get_service, client):
        """测试删除工作流成功"""
        # 设置 Mock
        mock_service = Mock()
        mock_service.delete_workflow.return_value = True
        mock_get_service.return_value = mock_service
        
        response = client.delete("/api/v1/workflows/test-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["id"] == "test-id"
    
    @patch('workflow_engine.api.server.get_workflow_service_dep')
    def test_delete_workflow_not_found(self, mock_get_service, client):
        """测试删除不存在的工作流"""
        # 设置 Mock
        mock_service = Mock()
        mock_service.delete_workflow.return_value = False
        mock_get_service.return_value = mock_service
        
        response = client.delete("/api/v1/workflows/non-existent")
        
        assert response.status_code == 404


# ==================== 依赖注入测试 ====================

class TestDependencyInjection:
    """依赖注入测试"""
    
    def test_get_planner_service_singleton(self):
        """测试规划服务单例"""
        from workflow_engine.api.dependencies import get_planner_service
        
        service1 = get_planner_service()
        service2 = get_planner_service()
        
        # 应该返回同一个实例（因为使用了 lru_cache）
        assert service1 is service2
    
    def test_get_workflow_service_no_db(self):
        """测试无数据库的工作流服务"""
        from workflow_engine.api.dependencies import get_workflow_service_no_db
        
        service = get_workflow_service_no_db()
        
        assert service is not None
        assert service.workflow_repo is None
        assert service.conversation_repo is None
    
    def test_get_execution_service_no_db(self):
        """测试无数据库的执行服务"""
        from workflow_engine.api.dependencies import get_execution_service_no_db
        
        service = get_execution_service_no_db()
        
        assert service is not None
        assert service.workflow_repo is None
        assert service.audit_log_repo is None
    
    def test_get_agent_service_no_db(self):
        """测试无数据库的智能体服务"""
        from workflow_engine.api.dependencies import get_agent_service_no_db
        
        service = get_agent_service_no_db()
        
        assert service is not None
        assert service.memory_repo is None


# ==================== 运行测试 ====================

def run_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("运行 API 接口测试")
    print("="*60)
    
    # 运行 pytest
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    return exit_code


if __name__ == "__main__":
    run_tests()