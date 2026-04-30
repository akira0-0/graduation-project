"""
测试辅助工具函数
提供测试中常用的工具函数
"""
import time
from typing import Dict, Any, Optional


def wait_for_condition(condition, timeout: int = 10, interval: float = 0.5) -> bool:
    """
    等待条件满足
    
    Args:
        condition: 条件函数，返回bool
        timeout: 超时时间（秒）
        interval: 检查间隔（秒）
    
    Returns:
        bool: 条件是否满足
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(interval)
    return False


def wait_for_api_response(response_func, expected_status: int = 200, timeout: int = 10) -> Dict[str, Any]:
    """
    等待API响应
    
    Args:
        response_func: API响应函数
        expected_status: 期望的HTTP状态码
        timeout: 超时时间（秒）
    
    Returns:
        Dict: API响应数据
    """
    start_time = time.time()
    last_error = None
    
    while time.time() - start_time < timeout:
        try:
            response = response_func()
            if response.status_code == expected_status:
                return response.json()
            last_error = f"Unexpected status: {response.status_code}"
        except Exception as e:
            last_error = str(e)
        
        time.sleep(0.5)
    
    raise TimeoutError(f"API response timeout: {last_error}")


def create_test_workflow(name: str = "test_workflow") -> Dict[str, Any]:
    """
    创建测试工作流数据
    
    Args:
        name: 工作流名称
    
    Returns:
        Dict: 工作流定义
    """
    return {
        "id": name,
        "name": f"测试工作流-{name}",
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


def create_test_node(node_id: str, node_type: str, title: str = "测试节点") -> Dict[str, Any]:
    """
    创建测试节点数据
    
    Args:
        node_id: 节点ID
        node_type: 节点类型
        title: 节点标题
    
    Returns:
        Dict: 节点定义
    """
    return {
        "id": node_id,
        "type": node_type,
        "config": {
            "title": title,
            "params": {}
        }
    }


def compare_workflows(workflow1: Dict[str, Any], workflow2: Dict[str, Any]) -> bool:
    """
    比较两个工作流是否相等
    
    Args:
        workflow1: 第一个工作流
        workflow2: 第二个工作流
    
    Returns:
        bool: 是否相等
    """
    required_keys = {"id", "name", "description", "nodes", "edges", "variables"}
    
    # 检查必需字段
    if not all(key in workflow1 and key in workflow2 for key in required_keys):
        return False
    
    # 比较节点和边
    if len(workflow1["nodes"]) != len(workflow2["nodes"]):
        return False
    if len(workflow1["edges"]) != len(workflow2["edges"]):
        return False
    
    return True


def sanitize_for_display(data: Any) -> str:
    """
    清理数据用于显示
    
    Args:
        data: 要显示的数据
    
    Returns:
        str: 清理后的字符串
    """
    if isinstance(data, (dict, list)):
        import json
        return json.dumps(data, ensure_ascii=False, indent=2)
    return str(data)


class MockResponse:
    """模拟API响应"""
    
    def __init__(self, status_code: int, data: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self._data = data or {}
    
    def json(self) -> Dict[str, Any]:
        """返回JSON数据"""
        return self._data
    
    def text(self) -> str:
        """返回文本数据"""
        import json
        return json.dumps(self._data)


def create_mock_response(success: bool = True, data: Optional[Dict[str, Any]] = None) -> MockResponse:
    """
    创建模拟响应
    
    Args:
        success: 是否成功
        data: 响应数据
    
    Returns:
        MockResponse: 模拟响应对象
    """
    status_code = 200 if success else 500
    response_data = data or {"status": "success" if success else "error"}
    
    return MockResponse(status_code, response_data)