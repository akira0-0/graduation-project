"""
pytest配置文件
包含所有测试的共享fixtures和配置
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / "workflow_engine") not in sys.path:
    sys.path.insert(0, str(project_root / "workflow_engine"))


@pytest.fixture(scope="session")
def event_loop_policy():
    """设置事件循环策略"""
    import asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def base_url():
    """返回基础URL"""
    return "http://localhost:8000"


@pytest.fixture
def api_client(base_url):
    """返回API测试客户端"""
    from fastapi.testclient import TestClient
    try:
        from workflow_engine.api.server import app
        return TestClient(app, base_url=base_url)
    except ImportError:
        pytest.skip("API server not available")


@pytest.fixture
def test_workflow_data():
    """返回测试工作流数据"""
    return {
        "id": "test_workflow",
        "name": "测试工作流",
        "description": "用于测试的工作流",
        "nodes": [
            {
                "id": "start",
                "type": "Start",
                "config": {
                    "title": "开始节点",
                    "params": {}
                }
            },
            {
                "id": "task1",
                "type": "Code",
                "config": {
                    "title": "任务1",
                    "params": {
                        "code": "def main():\n    return {'result': 'success'}"
                    }
                }
            },
            {
                "id": "end",
                "type": "End",
                "config": {
                    "title": "结束节点",
                    "params": {}
                }
            }
        ],
        "edges": [
            {"source": "start", "target": "task1"},
            {"source": "task1", "target": "end"}
        ],
        "variables": {}
    }