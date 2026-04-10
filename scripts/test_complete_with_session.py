"""
测试一站式过滤 API 的 Session 保存功能
"""
import requests
import json

BASE_URL = "http://localhost:8081"


def test_without_save():
    """测试不保存 Session（默认）"""
    print("\n" + "="*80)
    print("🧪 测试1: 不保存 Session（默认行为）")
    print("="*80 + "\n")
    
    response = requests.post(
        f"{BASE_URL}/api/filter/complete",
        json={
            "query": "丽江旅游攻略",
            "limit": 5,
            # save_session 默认为 False
        },
        timeout=300
    )
    
    if response.status_code == 200:
        result = response.json()
        session_id = result["session_id"]
        
        print(f"✅ 过滤成功")
        print(f"   Session ID: {session_id}")
        print(f"   返回帖子: {len(result['posts'])} 条")
        print(f"   Session 保存: {result['metadata'].get('session_saved', False)}")
        
        # 尝试查询 Session
        print(f"\n🔍 验证 Session 是否存在...")
        check_resp = requests.get(f"{BASE_URL}/api/sessions/{session_id}/results")
        
        if check_resp.status_code == 404:
            print(f"   ✅ 正确：Session 未保存（预期行为）")
        else:
            print(f"   ⚠️  意外：Session 已存在（{check_resp.status_code}）")
    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)


def test_with_save():
    """测试保存 Session"""
    print("\n" + "="*80)
    print("🧪 测试2: 保存 Session")
    print("="*80 + "\n")
    
    response = requests.post(
        f"{BASE_URL}/api/filter/complete",
        json={
            "query": "杭州美食推荐",
            "limit": 5,
            "save_session": True  # 🔑 关键参数
        },
        timeout=300
    )
    
    if response.status_code == 200:
        result = response.json()
        session_id = result["session_id"]
        
        print(f"✅ 过滤成功")
        print(f"   Session ID: {session_id}")
        print(f"   返回帖子: {len(result['posts'])} 条")
        print(f"   Session 保存: {result['metadata'].get('session_saved', False)}")
        
        # 验证 Session 是否真的保存了
        print(f"\n🔍 验证 Session 是否存在...")
        check_resp = requests.get(f"{BASE_URL}/api/sessions/{session_id}/results")
        
        if check_resp.status_code == 200:
            session_data = check_resp.json()
            print(f"   ✅ 成功：Session 已保存")
            print(f"   Session 元数据:")
            print(f"     - Query: {session_data['query']}")
            print(f"     - 总结果: {session_data['total_results']} 条")
            print(f"     - 场景: {session_data.get('scenario', 'N/A')}")
            
            # 对比数据一致性
            print(f"\n📊 数据一致性检查:")
            print(f"   Complete API 返回: {len(result['posts'])} 条")
            print(f"   Session API 查询: {session_data['total_results']} 条")
            
            if session_data['total_results'] >= len(result['posts']):
                print(f"   ✅ 一致（Session 保存了所有 L3 结果）")
            else:
                print(f"   ⚠️  不一致")
        else:
            print(f"   ❌ 失败：Session 未找到（{check_resp.status_code}）")
            print(check_resp.text)
    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)


def test_query_saved_session():
    """测试保存后多次查询同一 Session"""
    print("\n" + "="*80)
    print("🧪 测试3: 多次查询同一 Session")
    print("="*80 + "\n")
    
    # 先保存 Session
    print("Step 1: 创建并保存 Session...")
    response = requests.post(
        f"{BASE_URL}/api/filter/complete",
        json={
            "query": "成都周边自驾游",
            "limit": 10,
            "save_session": True
        },
        timeout=300
    )
    
    if response.status_code != 200:
        print(f"❌ 创建失败: {response.status_code}")
        return
    
    result = response.json()
    session_id = result["session_id"]
    print(f"   ✅ Session 已创建: {session_id}")
    print(f"   返回: {len(result['posts'])} 条\n")
    
    # 多次查询
    print("Step 2: 多次查询同一 Session（不同参数）...")
    
    queries = [
        {"limit": 5, "desc": "Top 5"},
        {"limit": 20, "desc": "Top 20"},
        {"min_score": 0.8, "desc": "高分（≥0.8）"},
    ]
    
    for i, params in enumerate(queries, 1):
        desc = params.pop("desc")
        print(f"\n  查询 {i}: {desc}")
        
        resp = requests.get(
            f"{BASE_URL}/api/sessions/{session_id}/results",
            params=params
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"    ✅ 返回: {data['returned_count']} 条")
        else:
            print(f"    ❌ 失败: {resp.status_code}")
    
    print(f"\n💡 优势: 一次过滤，多次查询（避免重复计算）")


def test_comparison():
    """对比：有/无保存 Session 的性能"""
    print("\n" + "="*80)
    print("⚖️  测试4: 性能对比")
    print("="*80 + "\n")
    
    query = "丽江旅游攻略"
    
    import time
    
    # 不保存 Session
    print("方案1: 不保存 Session")
    start = time.time()
    resp1 = requests.post(
        f"{BASE_URL}/api/filter/complete",
        json={"query": query, "limit": 10, "save_session": False},
        timeout=300
    )
    time1 = time.time() - start
    
    if resp1.status_code == 200:
        print(f"   ✅ 耗时: {time1:.2f}s")
        print(f"   返回: {len(resp1.json()['posts'])} 条")
    
    # 保存 Session
    print("\n方案2: 保存 Session")
    start = time.time()
    resp2 = requests.post(
        f"{BASE_URL}/api/filter/complete",
        json={"query": query, "limit": 10, "save_session": True},
        timeout=300
    )
    time2 = time.time() - start
    
    if resp2.status_code == 200:
        result = resp2.json()
        print(f"   ✅ 耗时: {time2:.2f}s")
        print(f"   返回: {len(result['posts'])} 条")
        
        # 后续查询
        session_id = result["session_id"]
        print(f"\n   后续查询 Session:")
        start = time.time()
        resp3 = requests.get(f"{BASE_URL}/api/sessions/{session_id}/results?limit=10")
        time3 = time.time() - start
        
        if resp3.status_code == 200:
            print(f"   ✅ 耗时: {time3:.2f}s (无需重新过滤)")
    
    # 对比
    print(f"\n{'='*80}")
    print(f"📊 对比结果:")
    print(f"   不保存: {time1:.2f}s (一次性使用)")
    print(f"   保存:   {time2:.2f}s (可重复查询)")
    print(f"   差异:   {time2-time1:.2f}s (保存 Session 的开销)")
    
    if time2 - time1 < 2:
        print(f"\n💡 结论: 保存开销很小（<2s），推荐需要重复查询时使用")


def check_database_records():
    """检查数据库记录"""
    print("\n" + "="*80)
    print("🔍 检查数据库 Session 记录")
    print("="*80 + "\n")
    
    # 创建一个带保存的 Session
    response = requests.post(
        f"{BASE_URL}/api/filter/complete",
        json={
            "query": "测试数据库保存",
            "limit": 3,
            "save_session": True
        },
        timeout=300
    )
    
    if response.status_code == 200:
        result = response.json()
        session_id = result["session_id"]
        
        print(f"✅ 创建 Session: {session_id}")
        print(f"\n查询各表记录...")
        
        # 查询 session_metadata
        resp = requests.get(f"{BASE_URL}/api/sessions/{session_id}/metadata")
        if resp.status_code == 200:
            metadata = resp.json()
            print(f"\n📋 session_metadata:")
            print(f"   - session_id: {metadata['session_id']}")
            print(f"   - query: {metadata['query']}")
            print(f"   - scenario: {metadata.get('scenario', 'N/A')}")
            print(f"   - l1_total_posts: {metadata.get('l1_total_posts', 0)}")
            print(f"   - l2_passed_posts: {metadata.get('l2_passed_posts', 0)}")
            print(f"   - l3_passed_posts: {metadata.get('l3_passed_posts', 0)}")
        
        # 查询 session_l3_results
        resp = requests.get(f"{BASE_URL}/api/sessions/{session_id}/results")
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n📊 session_l3_results:")
            print(f"   - 记录数: {data['total_results']}")
            
            if data['results']:
                print(f"   - 示例记录:")
                for i, item in enumerate(data['results'][:2], 1):
                    post = item['post']
                    print(f"     {i}. {post.get('title', 'N/A')[:30]}")
                    print(f"        相关性: {post.get('relevance_score', 0):.3f}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 一站式过滤 API - Session 保存功能测试")
    print("="*80)
    
    try:
        # 测试1: 默认不保存
        test_without_save()
        
        # 测试2: 显式保存
        test_with_save()
        
        # 测试3: 多次查询
        test_query_saved_session()
        
        # 测试4: 性能对比
        test_comparison()
        
        # 测试5: 数据库记录
        check_database_records()
        
        print("\n" + "="*80)
        print("✅ 所有测试完成")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
