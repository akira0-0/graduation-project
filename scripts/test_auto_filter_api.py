# -*- coding: utf-8 -*-
"""
端到端自动过滤 API 测试脚本

测试只需输入 query，自动从数据库读取并过滤的接口
"""
import requests
import json
import time

# API 基础 URL
BASE_URL = "http://localhost:8081"

def test_auto_filter():
    """测试端到端自动过滤 API"""
    print("\n" + "="*80)
    print("🧪 测试端到端自动过滤 API")
    print("="*80)
    
    # 准备请求
    request_data = {
        "query": "丽江旅游攻略",
        "platform": "xhs",           # 只处理小红书数据
        "max_posts": 500,            # 最多处理 500 条帖子
        "max_comments_per_post": 50, # 每个帖子最多 50 条评论
        "min_relevance": "medium",   # 中等相关性
        "llm_only": True,            # Layer-3 完全依赖 LLM
        "save_gap_rules": False,     # 不保存补充规则
        "auto_save": True,           # 自动保存到 session 表
    }
    
    print(f"\n📝 请求配置:")
    print(f"  Query: {request_data['query']}")
    print(f"  Platform: {request_data['platform']}")
    print(f"  Max Posts: {request_data['max_posts']}")
    print(f"  Min Relevance: {request_data['min_relevance']}")
    print(f"  LLM Only: {request_data['llm_only']}")
    print(f"  Auto Save: {request_data['auto_save']}")
    
    # 发送请求
    print(f"\n🚀 发送请求到 {BASE_URL}/api/filter/auto ...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/filter/auto",
            json=request_data,
            timeout=300,  # 5 分钟超时
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✅ 请求成功 (耗时 {elapsed:.2f}s)")
            result = response.json()
            
            # 打印 Session ID
            session_id = result['session_id']
            print(f"\n🆔 Session ID: {session_id}")
            
            # 打印统计信息
            print(f"\n📊 统计信息:")
            stats = result['stats']
            print(f"  Layer-1 总帖子: {stats['l1_total_posts']} 条")
            print(f"  Layer-1 总评论: {stats['l1_total_comments']} 条")
            print(f"  Layer-2 通过帖子: {stats['l2_passed_posts']} 条 ({stats['l2_passed_posts']/stats['l1_total_posts']*100:.1f}%)")
            print(f"  Layer-2 通过评论: {stats['l2_passed_comments']} 条")
            print(f"  Layer-3 通过帖子: {stats['l3_passed_posts']} 条 ({stats['l3_passed_posts']/stats['l1_total_posts']*100:.1f}%)")
            
            # 打印性能信息
            print(f"\n⚡ 性能分析:")
            perf = result['performance']
            print(f"  Layer-1 读取: {perf['layer1']:.2f}s")
            print(f"  Layer-2 过滤: {perf['layer2']:.2f}s")
            print(f"  Layer-3 过滤: {perf['layer3']:.2f}s")
            print(f"  总耗时: {perf['total']:.2f}s")
            
            # 打印数据访问方式
            print(f"\n🔗 数据访问:")
            access = result['access']
            print(f"  API 路径: {access.get('api_url', 'N/A')}")
            print(f"  完整 URL: {access.get('web_url', 'N/A')}")
            if access.get('metadata_url'):
                print(f"  元数据: {access['metadata_url']}")
            
            # 打印元数据
            print(f"\n📌 元数据:")
            metadata = result.get('metadata', {})
            if metadata.get('scenario'):
                print(f"  检测场景: {metadata['scenario']}")
            if metadata.get('platform'):
                print(f"  平台: {metadata['platform']}")
            if metadata.get('early_stop'):
                print(f"  ⚠️  早停: {metadata['early_stop']} - {metadata.get('reason', '')}")
            
            # Step 2: 测试获取结果
            if stats['l3_passed_posts'] > 0:
                print(f"\n{'─'*80}")
                print(f"📥 Step 2: 获取过滤结果")
                print(f"{'─'*80}")
                
                results_url = f"{BASE_URL}{access['api_url']}?limit=5"
                print(f"请求: GET {results_url}")
                
                results_resp = requests.get(results_url, timeout=30)
                
                if results_resp.status_code == 200:
                    results_data = results_resp.json()
                    print(f"\n✅ 成功获取 {len(results_data['results'])} 条结果（前 5 条）\n")
                    
                    for i, item in enumerate(results_data['results'], 1):
                        post = item['post']
                        title = post.get('title', '无标题')
                        score = post.get('relevance_score', 0)
                        level = post.get('relevance_level', 'unknown')
                        likes = post.get('metrics_likes', 0)
                        comments = item.get('comment_count', 0)
                        
                        # 截断标题
                        if len(title) > 40:
                            title = title[:40] + "..."
                        
                        print(f"  {i}. [{level} | {score:.3f}] {title}")
                        print(f"     👍 {likes} | 💬 {comments} 条评论")
                    
                    print(f"\n💡 提示: 完整结果请访问 {access['web_url']}")
                else:
                    print(f"❌ 获取结果失败: {results_resp.status_code}")
            
            # 保存完整结果
            output_file = "test_auto_filter_result.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 完整响应已保存到: {output_file}")
            
            return result
            
        elif response.status_code == 404:
            print(f"❌ 数据不存在: {response.json().get('detail', '')}")
            print(f"\n💡 提示: 请先运行 Layer-1 过滤脚本:")
            print(f"   uv run python scripts/batch_filter.py --data-type posts --platform xhs")
            return None
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（超过 300 秒）")
        return None
    except Exception as e:
        print(f"❌ 请求出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_minimal_request():
    """测试最简请求（仅 query）"""
    print("\n" + "="*80)
    print("🧪 测试最简请求（仅输入 query）")
    print("="*80)
    
    # 最简请求
    request_data = {
        "query": "西安美食推荐",
        # 其他参数使用默认值
    }
    
    print(f"\n📝 请求配置:")
    print(f"  Query: {request_data['query']}")
    print(f"  其他参数: 使用默认值")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/filter/auto",
            json=request_data,
            timeout=300,
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 请求成功")
            print(f"  Session ID: {result['session_id']}")
            print(f"  L3 通过: {result['stats']['l3_passed_posts']} 条")
            print(f"  总耗时: {result['performance']['total']:.2f}s")
            print(f"  API 访问: {result['access']['api_url']}")
        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            print(f"  {response.json().get('detail', '')}")
            
    except Exception as e:
        print(f"\n❌ 请求出错: {e}")


def test_query_comparison():
    """对比不同 query 的过滤效果"""
    print("\n" + "="*80)
    print("🔬 对比不同 Query 的过滤效果")
    print("="*80)
    
    queries = [
        ("丽江旅游攻略", "旅游场景"),
        ("电商好评返现", "电商场景"),
        ("手机推荐", "通用场景"),
    ]
    
    results_comparison = []
    
    for query, scenario_desc in queries:
        print(f"\n{'─'*60}")
        print(f"📝 测试 Query: {query} ({scenario_desc})")
        print(f"{'─'*60}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/filter/auto",
                json={
                    "query": query,
                    "max_posts": 100,  # 小批量测试
                },
                timeout=180,
            )
            
            if response.status_code == 200:
                result = response.json()
                stats = result['stats']
                perf = result['performance']
                
                results_comparison.append({
                    "query": query,
                    "scenario": result['metadata'].get('scenario', 'unknown'),
                    "l1_posts": stats['l1_total_posts'],
                    "l2_posts": stats['l2_passed_posts'],
                    "l3_posts": stats['l3_passed_posts'],
                    "pass_rate": f"{stats['l3_passed_posts']/stats['l1_total_posts']*100:.1f}%" if stats['l1_total_posts'] > 0 else "0%",
                    "time": f"{perf['total']:.1f}s",
                })
                
                print(f"  ✅ 完成")
                print(f"     场景: {result['metadata'].get('scenario')}")
                print(f"     通过率: {stats['l3_passed_posts']}/{stats['l1_total_posts']} ({stats['l3_passed_posts']/stats['l1_total_posts']*100:.1f}%)")
                print(f"     耗时: {perf['total']:.1f}s")
            else:
                print(f"  ❌ 失败: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ 出错: {e}")
    
    # 打印对比表格
    if results_comparison:
        print(f"\n{'='*80}")
        print(f"📊 对比结果汇总")
        print(f"{'='*80}")
        print(f"{'Query':<20} {'场景':<15} {'L1':<8} {'L2':<8} {'L3':<8} {'通过率':<10} {'耗时'}")
        print(f"{'-'*80}")
        for r in results_comparison:
            print(f"{r['query']:<20} {r['scenario']:<15} {r['l1_posts']:<8} {r['l2_posts']:<8} {r['l3_posts']:<8} {r['pass_rate']:<10} {r['time']}")


if __name__ == "__main__":
    print("\n" + "🎯 " * 20)
    print("端到端自动过滤 API 测试")
    print("🎯 " * 20)
    
    # 测试 1: 标准功能测试
    test_auto_filter()
    
    # 测试 2: 最简请求测试
    # test_minimal_request()
    
    # 测试 3: Query 对比测试
    # test_query_comparison()
    
    print("\n" + "="*80)
    print("✅ 测试完成")
    print("="*80)
    
    print("\n💡 使用建议:")
    print("  1. 确保已运行 Layer-1 过滤: uv run python scripts/batch_filter.py")
    print("  2. 只需输入 query 即可: {'query': '丽江旅游'}")
    print("  3. 通过返回的 API URL 获取结果")
    print("  4. Session 数据默认保留 2 小时")
