from fastapi.testclient import TestClient
from workflow_engine.api.server import app
from unittest.mock import MagicMock, patch

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch('workflow_engine.api.server.LLMPlanner')
def test_generate_workflow(MockLLMPlanner):
    # Mock planner response
    mock_planner_instance = MockLLMPlanner.return_value
    mock_workflow = {
        "name": "Test Workflow",
        "description": "A test workflow",
        "nodes": [],
        "edges": [],
        "variables": {}
    }
    mock_planner_instance.plan.return_value = mock_workflow

    response = client.post(
        "/api/v1/workflows/generate",
        json={"intent": "create a test workflow", "model": "test-model"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["workflow"]["name"] == "Test Workflow"
    assert data["metadata"]["model"] == "test-model"

@patch('workflow_engine.api.server.LLMPlanner')
def test_generate_workflow_error(MockLLMPlanner):
    # Mock planner exception
    mock_planner_instance = MockLLMPlanner.return_value
    mock_planner_instance.plan.side_effect = Exception("Planning failed")

    response = client.post(
        "/api/v1/workflows/generate",
        json={"intent": "trigger error"}
    )
    
    assert response.status_code == 500
    assert "Planning failed" in response.json()["detail"]["error"]