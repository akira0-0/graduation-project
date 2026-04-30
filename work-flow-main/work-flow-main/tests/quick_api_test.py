"""
快速API验证脚本
快速测试后端API的核心功能
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8123"

def test_health():
    """测试健康检查"""
    print("1. 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        print(f"   ✓ 状态: {response.status_code}")
        print(f"   ✓ 响应: {data}")
        return True
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

def test_root():
    """测试根路径"""
    print("\n2. 测试根路径...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        data = response.json()
        print(f"   ✓ 状态: {response.status_code}")
        print(f"   ✓ 消息: {data.get('message')}")
        print(f"   ✓ 文档路径: {data.get('documentation')}")
        return True
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

def test_simple_workflow_execution():
    """测试简单工作流执行"""
    print("\n3. 测试简单工作流执行...")
    try:
        workflow = {
            "name": "快速测试工作流",
            "description": "快速验证用",
            "nodes": [
                {
                    "id": "start",
                    "type": "Start",
                    "config": {"title": "开始", "params": {}}
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
                    "config": {"title": "结束", "params": {}}
                }
            ],
            "edges": [
                {"source": "start", "target": "task"},
                {"source": "task", "target": "end"}
            ],
            "variables": {}
        }
        
        payload = {
            "workflow": workflow,
            "engine": "langgraph",
            "model": "deepseek-chat",
            "enable_monitoring": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/workflows/execute",
            json=payload,
            timeout=10
        )
        
        print(f"   ✓ 状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 执行状态: {data.get('status')}")
            print(f"   ✓ 执行ID: {data.get('execution_id')}")
            return True
        else:
            print(f"   ✗ 错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

def test_workflow_with_end_node():
    """测试带结束节点的工作流"""
    print("\n4. 测试带开始和结束节点的工作流...")
    try:
        workflow = {
            "name": "完整节点测试工作流",
            "description": "测试Start到End的连接",
            "nodes": [
                {
                    "id": "start",
                    "type": "Start",
                    "config": {"title": "开始", "params": {}}
                },
                {
                    "id": "end",
                    "type": "End",
                    "config": {"title": "结束", "params": {}}
                }
            ],
            "edges": [
                {"source": "start", "target": "end"}
            ],
            "variables": {}
        }
        
        payload = {
            "workflow": workflow,
            "engine": "langgraph",
            "model": "deepseek-chat",
            "enable_monitoring": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/workflows/execute",
            json=payload,
            timeout=10
        )
        
        print(f"   ✓ 状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 执行状态: {data.get('status')}")
            print(f"   ✓ 节点输出: {list(data.get('result', {}).keys())}")
            return True
        else:
            print(f"   ✗ 错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("=" * 60)
    print("后端API快速验证测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: 健康检查
    results.append(("健康检查", test_health()))
    
    # 测试2: 根路径
    results.append(("根路径", test_root()))
    
    # 测试3: 简单工作流执行
    results.append(("简单工作流执行", test_simple_workflow_execution()))
    
    # 测试4: 完整节点工作流
    results.append(("完整节点工作流", test_workflow_with_end_node()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！后端API功能正常。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())