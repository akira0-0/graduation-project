"""
测试一站式过滤 API
输入 query → 直接返回 post_data
"""
import requests
import json

BASE_URL = "http://localhost:8081"


def test_complete_filter():
    """测试完整流程"""
    print("\n" + "="*80)
    print("🎯 测试一站式过滤 API（Query → Post Data）")
    print("="*80 + "\n")
    
    # ═══════════════════════════════════════════════════════
    # 一个请求搞定
    # ═══════════════════════════════════════════════════════
    request_data = {
        "query": "丽江旅游攻略",
        "platform": "xhs",
        "max_posts": 500,
        "min_relevance": "medium",
        "limit": 10,
        "min_score": 0.6,
        "include_comments": True,
        "llm_only": True
    }
    
    print("📤 请求数据:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    print()
    
    print("⏳ 发送请求...\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/filter/complete",
            json=request_data,
            timeout=300
        )
        
        if response.status_code != 200:
            print(f"❌ 请求失败: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        
        # ═══════════════════════════════════════════════════════
        # 显示统计信息
        # ═══════════════════════════════════════════════════════
        print("="*80)
        print("📊 统计信息")
        print("="*80)
        print(f"Query: {result['query']}")
        print(f"Session ID: {result['session_id']}")
        print(f"场景: {result['metadata'].get('scenario', 'N/A')}")
        print()
        
        stats = result['stats']
        print("过滤流程:")
        print(f"  L1 总数: {stats['l1_total_posts']}")
        print(f"  L2 通过: {stats['l2_passed_posts']} ({stats['l2_passed_posts']/stats['l1_total_posts']*100:.1f}%)")
        print(f"  L3 通过: {stats['l3_passed_posts']} ({stats['l3_passed_posts']/stats['l1_total_posts']*100:.1f}%)")
        print(f"  最终返回: {stats['final_returned']} 条")
        print()
        
        perf = result['performance']
        print("性能:")
        print(f"  Layer-1 读取: {perf['layer1']:.2f}s")
        print(f"  Layer-2 规则: {perf['layer2']:.2f}s")
        print(f"  Layer-3 LLM: {perf['layer3']:.2f}s")
        print(f"  评论读取: {perf['fetch_results']:.2f}s")
        print(f"  总耗时: {perf['total']:.2f}s")
        print()
        
        # ═══════════════════════════════════════════════════════
        # 显示帖子数据
        # ═══════════════════════════════════════════════════════
        posts = result['posts']
        print("="*80)
        print(f"📝 帖子数据（共 {len(posts)} 条）")
        print("="*80)
        
        for i, post in enumerate(posts[:5], 1):
            print(f"\n{i}. {post.get('title') or '(无标题)'}")
            print(f"   ID: {post['id']}")
            print(f"   平台: {post.get('platform', 'N/A')}")
            print(f"   相关性: {post['relevance_score']:.3f} ({post['relevance_level']})")
            print(f"   点赞: {post.get('metrics_likes', 0)}")
            print(f"   评论数: {len(post.get('comments', []))}")
            
            # 显示内容片段
            content = post.get('content', '')
            if content:
                preview = content[:100] + ('...' if len(content) > 100 else '')
                print(f"   内容: {preview}")
            
            # 显示评论示例
            comments = post.get('comments', [])
            if comments:
                print(f"   评论示例:")
                for j, comment in enumerate(comments[:2], 1):
                    author = comment.get('author_nickname', '匿名')
                    text = comment.get('content', '')[:50]
                    print(f"     {j}) {author}: {text}...")
        
        if len(posts) > 5:
            print(f"\n... 还有 {len(posts) - 5} 条帖子")
        
        print("\n" + "="*80)
        print("✅ 测试完成！")
        print("="*80)
        
        # ═══════════════════════════════════════════════════════
        # 保存完整数据到文件
        # ═══════════════════════════════════════════════════════
        output_file = "complete_filter_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 完整结果已保存到: {output_file}")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时（>300s）")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_different_queries():
    """测试不同查询"""
    print("\n" + "="*80)
    print("🔄 测试多个查询")
    print("="*80 + "\n")
    
    test_cases = [
        {
            "query": "丽江旅游攻略",
            "limit": 5,
            "min_relevance": "high"
        },
        {
            "query": "杭州美食推荐",
            "limit": 5,
            "min_relevance": "medium"
        },
        {
            "query": "成都周边自驾游",
            "limit": 5,
            "min_relevance": "medium"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'─'*80}")
        print(f"测试 {i}: {case['query']}")
        print(f"{'─'*80}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/filter/complete",
                json=case,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                stats = result['stats']
                posts = result['posts']
                
                print(f"✅ Query: {result['query']}")
                print(f"   L1→L2→L3: {stats['l1_total_posts']} → {stats['l2_passed_posts']} → {stats['l3_passed_posts']}")
                print(f"   返回: {len(posts)} 条")
                print(f"   耗时: {result['performance']['total']:.2f}s")
                
                if posts:
                    avg_score = sum(p['relevance_score'] for p in posts) / len(posts)
                    print(f"   平均相关性: {avg_score:.3f}")
            else:
                print(f"❌ 失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 错误: {e}")


def test_with_filters():
    """测试各种过滤参数"""
    print("\n" + "="*80)
    print("🔧 测试过滤参数")
    print("="*80 + "\n")
    
    base_query = "丽江旅游"
    
    configs = [
        {"name": "高相关性 + 高分数", "min_relevance": "high", "min_score": 0.8, "limit": 5},
        {"name": "中相关性 + 中等分数", "min_relevance": "medium", "min_score": 0.6, "limit": 10},
        {"name": "低相关性 + 无分数限制", "min_relevance": "low", "min_score": None, "limit": 20},
    ]
    
    for config in configs:
        name = config.pop("name")
        print(f"\n{'─'*80}")
        print(f"配置: {name}")
        print(f"{'─'*80}")
        
        request_data = {
            "query": base_query,
            "platform": "xhs",
            "max_posts": 300,
            **config,
            "include_comments": False  # 加快测试速度
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/filter/complete",
                json=request_data,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                posts = result['posts']
                
                print(f"✅ 返回: {len(posts)} 条")
                if posts:
                    scores = [p['relevance_score'] for p in posts]
                    print(f"   分数范围: {min(scores):.3f} ~ {max(scores):.3f}")
                    print(f"   平均分数: {sum(scores)/len(scores):.3f}")
                    
                    # 统计相关性等级分布
                    levels = {}
                    for p in posts:
                        level = p['relevance_level']
                        levels[level] = levels.get(level, 0) + 1
                    print(f"   等级分布: {levels}")
            else:
                print(f"❌ 失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 错误: {e}")


def test_comparison():
    """对比两种方案"""
    print("\n" + "="*80)
    print("⚖️  对比测试：一站式 vs 两步式")
    print("="*80 + "\n")
    
    query = "丽江旅游攻略"
    
    # ═══════════════════════════════════════════════════════
    # 方案1: 一站式（新）
    # ═══════════════════════════════════════════════════════
    print("方案1: 一站式过滤（Complete API）")
    print("─"*80)
    
    import time
    start = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/filter/complete",
            json={"query": query, "limit": 10},
            timeout=300
        )
        
        one_step_time = time.time() - start
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 请求次数: 1")
            print(f"   返回帖子: {len(result['posts'])} 条")
            print(f"   总耗时: {one_step_time:.2f}s")
            print(f"   API 报告耗时: {result['performance']['total']:.2f}s")
        else:
            print(f"❌ 失败: {response.status_code}")
            one_step_time = None
    except Exception as e:
        print(f"❌ 错误: {e}")
        one_step_time = None
    
    # ═══════════════════════════════════════════════════════
    # 方案2: 两步式（旧）
    # ═══════════════════════════════════════════════════════
    print("\n方案2: 两步式过滤（Auto + Session API）")
    print("─"*80)
    
    start = time.time()
    
    try:
        # Step 1: Auto filter
        print("  Step 1: POST /api/filter/auto")
        resp1 = requests.post(
            f"{BASE_URL}/api/filter/auto",
            json={"query": query},
            timeout=300
        )
        
        if resp1.status_code != 200:
            print(f"  ❌ Step 1 失败: {resp1.status_code}")
            two_step_time = None
        else:
            session_id = resp1.json()["session_id"]
            print(f"  ✅ Session ID: {session_id}")
            
            # Step 2: Get results
            print("  Step 2: GET /api/sessions/{session_id}/results")
            resp2 = requests.get(
                f"{BASE_URL}/api/sessions/{session_id}/results",
                params={"limit": 10},
                timeout=60
            )
            
            two_step_time = time.time() - start
            
            if resp2.status_code == 200:
                result = resp2.json()
                print(f"✅ 请求次数: 2")
                print(f"   返回帖子: {len(result['results'])} 条")
                print(f"   总耗时: {two_step_time:.2f}s")
            else:
                print(f"❌ Step 2 失败: {resp2.status_code}")
                two_step_time = None
    except Exception as e:
        print(f"❌ 错误: {e}")
        two_step_time = None
    
    # ═══════════════════════════════════════════════════════
    # 对比结果
    # ═══════════════════════════════════════════════════════
    print("\n" + "="*80)
    print("📊 对比结果")
    print("="*80)
    
    if one_step_time and two_step_time:
        print(f"一站式: {one_step_time:.2f}s (1 次请求)")
        print(f"两步式: {two_step_time:.2f}s (2 次请求)")
        diff = two_step_time - one_step_time
        print(f"\n节省: {diff:.2f}s ({diff/two_step_time*100:.1f}%)")
    
    print("\n优势:")
    print("  ✅ 请求次数减少 50%（2→1）")
    print("  ✅ 无需管理 session_id")
    print("  ✅ 代码更简洁")
    print("  ✅ 直接返回可用数据")


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*80)
    print("🚀 一站式过滤 API 测试")
    print("="*80)
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == "basic":
            test_complete_filter()
        elif test_type == "multi":
            test_different_queries()
        elif test_type == "filter":
            test_with_filters()
        elif test_type == "compare":
            test_comparison()
        else:
            print(f"未知测试类型: {test_type}")
            print("可用类型: basic, multi, filter, compare")
    else:
        # 默认运行基本测试
        test_complete_filter()
        
        # 可选：运行对比测试
        print("\n\n")
        user_input = input("是否运行对比测试？(y/n): ")
        if user_input.lower() == 'y':
            test_comparison()
