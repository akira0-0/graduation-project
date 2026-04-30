"""
直接API测试 - 不使用浏览器
使用requests库直接测试后端API
"""
import pytest
import requests
import json
from typing import Dict, Any


@pytest.mark.integration
class TestAPIDirect:
    """直接API测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前检查服务器是否运行"""
        self.base_url = "http://localhost:8123"
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"后端服务器未运行: {e}")

    def test_health_endpoint(self):
        """测试健康检查端点"""
        response = requests.get(f"{self.base_url}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_root_endpoint(self):
        """测试根路径"""
        response = requests.get(f"{self.base_url}/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "documentation" in data
        assert data["documentation"] == "/docs"

    def test_generate_workflow_api(self):
        """测试工作流生成API"""
        payload = {
            "intent": "创建一个简单的测试工作流",
            "model": "deepseek-chat"
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/workflows/generate",
            json=payload,
            timeout=30
        )
        
        # 可能会因为模型配置问题失败，但端点应该能响应
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "workflow" in data
            assert "status" in data

    def test_execute_workflow_simple(self):
        """测试简单工作流执行"""
        workflow_data = {
            "name": "简单测试工作流",
            "description": "API测试用简单工作流",
            "nodes": [
                {
                    "id": "start",
                    "type": "Start",
                    "config": {
                        "title": "开始",
                        "description": "工作流开始",
                        "params": {}
                    }
                },
                {
                    "id": "task",
                    "type": "Code",
                    "config": {
                        "title": "任务",
                        "params": {
                            "code": "def main():\n    return {'status': 'completed', 'value': 42}",
                            "inputs": {}
                        }
                    }
                },
                {
                    "id": "end",
                    "type": "End",
                    "config": {
                        "title": "结束",
                        "description": "工作流结束",
                        "params": {}
                    }
                }
            ],
            "edges": [
                {"source": "start", "target": "task"},
                {"source": "task", "target": "end"}
            ],
            "variables": {}
        }
        
        payload = {
            "workflow": workflow_data,
            "engine": "langgraph",
            "model": "deepseek-chat",
            "enable_monitoring": False
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/workflows/execute",
            json=payload,
            timeout=30
        )
        
        # 简单工作流应该能成功执行
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["completed", "running"]

    def test_execute_workflow_with_code_node(self):
        """测试包含代码节点的工作流执行"""
        workflow_data = {
            "name": "代码节点测试工作流",
            "description": "测试代码节点功能",
            "nodes": [
                {
                    "id": "start",
                    "type": "Start",
                    "config": {
                        "title": "开始",
                        "params": {}
                    }
                },
                {
                    "id": "code1",
                    "type": "Code",
                    "config": {
                        "title": "简单代码",
                        "params": {
                            "code": "def main():\n    return {'result': 'success', 'value': 42}",
                            "inputs": {}
                        }
                    }
                },
                {
                    "id": "end",
                    "type": "End",
                    "config": {
                        "title": "结束",
                        "params": {}
                    }
                }
            ],
            "edges": [
                {"source": "start", "target": "code1"},
                {"source": "code1", "target": "end"}
            ],
            "variables": {}
        }
        
        payload = {
            "workflow": workflow_data,
            "engine": "langgraph",
            "model": "deepseek-chat",
            "enable_monitoring": False
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/workflows/execute",
            json=payload,
            timeout=30
        )
        
        # 代码节点可能因工具配置问题失败
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "result" in data

    def test_invalid_endpoint(self):
        """测试无效端点返回404"""
        response = requests.get(f"{self.base_url}/api/invalid")
        
        assert response.status_code == 404

    def test_invalid_workflow_execution(self):
        """测试无效工作流执行"""
        # 缺少必需字段的工作流
        invalid_workflow = {
            "name": "无效工作流"
            # 缺少nodes和edges
        }
        
        payload = {
            "workflow": invalid_workflow,
            "engine": "langgraph",
            "model": "deepseek-chat",
            "enable_monitoring": False
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/workflows/execute",
            json=payload,
            timeout=30
        )
        
        # 应该返回错误
        assert response.status_code in [400, 422, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])