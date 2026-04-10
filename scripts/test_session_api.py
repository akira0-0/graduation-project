#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Session API 测试脚本
用于验证 API 接口是否正常工作
"""
import requests
from typing import Optional

API_BASE_URL = "http://localhost:8081"


def test_list_sessions():
    """测试：列出所有 Session"""
    print("\n" + "="*60)
    print("测试 1: 列出所有 Session")
    print("="*60)
    
    url = f"{API_BASE_URL}/api/sessions"
    response = requests.get(url, params={"limit": 5})
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功！找到 {data['total']} 个 Session")
        
        if data['sessions']:
            print("\n最近的 Session:")
            for session in data['sessions'][:3]:
                print(f"  - ID: {session['session_id']}")
                print(f"    Query: {session['query_text']}")
                print(f"    Status: {session['status']}")
                print(f"    Created: {session['created_at']}")
        else:
            print("⚠️  当前没有 Session 数据")
            print("   请先运行过滤脚本:")
            print("   uv run python scripts/batch_scene_filter_smart.py --query '...'")
        
        return data['sessions'][0]['session_id'] if data['sessions'] else None
    else:
        print(f"❌ 失败！状态码: {response.status_code}")
        print(f"   错误: {response.text}")
        return None


def test_get_metadata(session_id: str):
    """测试：获取 Session 元数据"""
    print("\n" + "="*60)
    print(f"测试 2: 获取 Session 元数据")
    print("="*60)
    
    url = f"{API_BASE_URL}/api/sessions/{session_id}/metadata"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功！")
        print(f"\nSession 信息:")
        print(f"  - Query: {data['query_text']}")
        print(f"  - Layer-1 帖子: {data['l1_total_posts']} 条")
        print(f"  - Layer-2 通过: {data['l2_passed_posts']} 条")
        print(f"  - Layer-3 通过: {data['l3_passed_posts']} 条")
        print(f"  - 状态: {data['status']}")
    else:
        print(f"❌ 失败！状态码: {response.status_code}")
        print(f"   错误: {response.text}")


def test_get_results(session_id: str, limit: int = 5, min_score: Optional[float] = None):
    """测试：获取 Session 结果"""
    print("\n" + "="*60)
    print(f"测试 3: 获取 Session 结果（前 {limit} 条）")
    print("="*60)
    
    url = f"{API_BASE_URL}/api/sessions/{session_id}/results"
    params = {"limit": limit}
    if min_score is not None:
        params["min_score"] = min_score
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功！")
        print(f"\n结果统计:")
        print(f"  - 总结果数: {data['total_results']} 条")
        print(f"  - Query: {data['query_text']}")
        
        if data['results']:
            print(f"\n前 {min(3, len(data['results']))} 条帖子:")
            for i, item in enumerate(data['results'][:3], 1):
                post = item['post']
                print(f"\n  {i}. {post.get('title') or '(无标题)'}")
                print(f"     内容: {post['content'][:80]}...")
                print(f"     相关性: {post.get('relevance_score', 'N/A')} ({post.get('relevance_level', 'N/A')})")
                print(f"     点赞: {post.get('metrics_likes', 0)} | 评论: {item['comment_count']}")
                print(f"     平台: {post['platform']} | 作者: {post.get('author_nickname', 'Unknown')}")
        else:
            print("\n⚠️  该 Session 没有通过 Layer-3 的数据")
            print("   可能原因:")
            print("   1. Layer-3 过滤标准太严格")
            print("   2. Layer-2 数据质量较低")
            print("   3. 相关性分数都低于阈值")
    else:
        print(f"❌ 失败！状态码: {response.status_code}")
        print(f"   错误: {response.text}")


def test_api_docs():
    """测试：API 文档是否可访问"""
    print("\n" + "="*60)
    print("测试 4: API 文档可访问性")
    print("="*60)
    
    docs_url = f"{API_BASE_URL}/docs"
    response = requests.get(docs_url)
    
    if response.status_code == 200:
        print(f"✅ Swagger UI 可访问！")
        print(f"   URL: {docs_url}")
        print(f"   提示: 在浏览器中打开查看完整文档")
    else:
        print(f"❌ 文档不可访问！状态码: {response.status_code}")


def main():
    """主测试流程"""
    print("\n🚀 Session API 测试")
    print("="*60)
    print(f"API 地址: {API_BASE_URL}")
    
    # 测试 1: 列出 Session
    session_id = test_list_sessions()
    
    if not session_id:
        print("\n" + "="*60)
        print("⚠️  无法继续测试：没有可用的 Session")
        print("="*60)
        print("\n请先运行过滤脚本创建 Session:")
        print("  uv run python scripts/batch_scene_filter_smart.py \\")
        print("    --query '保留关于丽江旅游、景点、美食的真实体验分享'")
        return
    
    # 测试 2: 获取元数据
    test_get_metadata(session_id)
    
    # 测试 3: 获取结果
    test_get_results(session_id, limit=5)
    
    # 测试 4: API 文档
    test_api_docs()
    
    # 总结
    print("\n" + "="*60)
    print("✅ 所有测试完成！")
    print("="*60)
    print("\n📌 给同学的调用示例:")
    print(f"\n# Python 调用")
    print(f"import requests")
    print(f"url = '{API_BASE_URL}/api/sessions/{session_id}/results'")
    print(f"response = requests.get(url, params={{'limit': 100, 'min_score': 0.7}})")
    print(f"data = response.json()")
    print(f"print(f'获取到 {{data[\"total_results\"]}} 条结果')")
    
    print(f"\n# cURL 调用")
    print(f"curl '{API_BASE_URL}/api/sessions/{session_id}/results?limit=100&min_score=0.7'")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到 API 服务！")
        print("请确保 API 服务已启动:")
        print("  uv run uvicorn filter_engine.api:app --host 0.0.0.0 --port 8081")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
