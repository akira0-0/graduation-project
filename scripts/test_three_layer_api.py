# -*- coding: utf-8 -*-
"""
三层过滤 API 测试脚本

测试新的优化版三层过滤接口
"""
import requests
import json
import time

# API 基础 URL
BASE_URL = "http://localhost:8081"

# 测试数据
TEST_CONTENTS = [
    # 高相关性内容（应该通过）
    "丽江古城深度游攻略，推荐这几个景点必去：玉龙雪山、束河古镇...",
    "丽江三日游完整攻略，包含住宿、美食、景点推荐",
    
    # 中等相关性（应该通过）
    "云南旅游推荐，丽江是个不错的选择，风景很美",
    
    # 低相关性（可能被过滤）
    "今天天气真好，适合出去玩",
    
    # 垃圾广告（Layer-1 应该拦截）
    "加微信 xxx，低价代购丽江旅游套餐，全网最低价！！！",
    "【广告】丽江旅游找我，保证低价，微信：xxxxx",
    
    # 无关内容（Layer-3 应该拦截）
    "北京的烤鸭真好吃，推荐大家去试试",
    "上海迪士尼乐园门票多少钱？",
    
    # 短内容（Layer-1 应该拦截）
    "好",
    "👍",
]

def test_three_layer_filter():
    """测试三层过滤 API"""
    print("\n" + "="*80)
    print("🧪 测试三层过滤 API (优化版)")
    print("="*80)
    
    # 准备请求
    request_data = {
        "query": "丽江旅游攻略",
        "contents": TEST_CONTENTS,
        "enable_layer1": True,
        "enable_layer2": True,
        "enable_layer3": True,
        "min_content_length": 4,
        "min_relevance": "medium",
        "llm_only": True,  # Layer-3 完全依赖 LLM
        "save_gap_rules": False,
    }
    
    print(f"\n📝 请求配置:")
    print(f"  Query: {request_data['query']}")
    print(f"  内容数: {len(request_data['contents'])} 条")
    print(f"  Layer-1: {request_data['enable_layer1']}")
    print(f"  Layer-2: {request_data['enable_layer2']}")
    print(f"  Layer-3: {request_data['enable_layer3']} (LLM Only: {request_data['llm_only']})")
    print(f"  最低相关性: {request_data['min_relevance']}")
    
    # 发送请求
    print(f"\n🚀 发送请求到 {BASE_URL}/api/filter/three-layer ...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/filter/three-layer",
            json=request_data,
            timeout=120,  # 2 分钟超时
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✅ 请求成功 (耗时 {elapsed:.2f}s)")
            result = response.json()
            
            # 打印统计信息
            print(f"\n📊 统计信息:")
            stats = result['stats']
            print(f"  总输入: {stats['total_input']} 条")
            print(f"  Layer-1 通过: {stats['layer1_passed']} 条 ({stats['layer1_passed']/stats['total_input']*100:.1f}%)")
            print(f"  Layer-2 通过: {stats['layer2_passed']} 条 ({stats['layer2_passed']/stats['total_input']*100:.1f}%)")
            print(f"  Layer-3 通过: {stats['layer3_passed']} 条 ({stats['layer3_passed']/stats['total_input']*100:.1f}%)")
            print(f"  最终结果: {stats['final_count']} 条")
            
            # 打印性能信息
            print(f"\n⚡ 性能分析:")
            perf = result['performance']
            print(f"  Layer-1 耗时: {perf['layer1']:.2f}s")
            print(f"  Layer-2 耗时: {perf['layer2']:.2f}s")
            print(f"  Layer-3 耗时: {perf['layer3']:.2f}s")
            print(f"  总耗时: {perf['total']:.2f}s")
            
            # 打印元数据
            print(f"\n📌 元数据:")
            metadata = result.get('metadata', {})
            if metadata.get('scenario'):
                print(f"  检测场景: {metadata['scenario']}")
            print(f"  Session ID: {result.get('session_id', 'N/A')}")
            
            # 打印最终结果
            print(f"\n✨ 最终通过的内容 ({len(result['results'])} 条):")
            for i, item in enumerate(result['results'][:5], 1):  # 只显示前5条
                content = item['content']
                score = item.get('relevance_score', 0)
                level = item.get('relevance_level', 'unknown')
                layers = ' → '.join(item.get('layers_passed', []))
                
                # 截断长文本
                if len(content) > 60:
                    content = content[:60] + "..."
                
                print(f"  {i}. [{level} | {score:.3f}] {content}")
                print(f"     通过路径: {layers}")
            
            if len(result['results']) > 5:
                print(f"  ... (还有 {len(result['results']) - 5} 条)")
            
            # 保存完整结果
            output_file = "test_three_layer_result.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 完整结果已保存到: {output_file}")
            
            return result
            
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（超过 120 秒）")
        return None
    except Exception as e:
        print(f"❌ 请求出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_compare_with_original():
    """对比新旧接口性能"""
    print("\n" + "="*80)
    print("🔬 性能对比测试（新版 vs 旧版）")
    print("="*80)
    
    # 新版接口
    print("\n🆕 测试新版接口 /api/filter/three-layer ...")
    new_start = time.time()
    new_result = test_three_layer_filter()
    new_elapsed = time.time() - new_start
    
    # 旧版接口
    print("\n📜 测试旧版接口 /api/pipeline/run ...")
    old_start = time.time()
    
    old_request = {
        "query": "丽江旅游攻略",
        "contents": TEST_CONTENTS,
        "enable_base_filter": True,
        "enable_scene_filter": True,
        "enable_relevance_filter": True,
        "min_relevance": "medium",
        "apply_gap_rules": True,
    }
    
    try:
        old_response = requests.post(
            f"{BASE_URL}/api/pipeline/run",
            json=old_request,
            timeout=120,
        )
        old_elapsed = time.time() - old_start
        
        if old_response.status_code == 200:
            old_result = old_response.json()
            print(f"✅ 旧版请求成功 (耗时 {old_elapsed:.2f}s)")
            
            # 性能对比
            print(f"\n📈 性能对比:")
            print(f"  新版总耗时: {new_elapsed:.2f}s")
            print(f"  旧版总耗时: {old_elapsed:.2f}s")
            
            if new_elapsed < old_elapsed:
                speedup = (old_elapsed - new_elapsed) / old_elapsed * 100
                print(f"  ✅ 新版更快，提速 {speedup:.1f}%")
            else:
                slowdown = (new_elapsed - old_elapsed) / old_elapsed * 100
                print(f"  ⚠️ 新版较慢，慢了 {slowdown:.1f}%")
            
            # 结果一致性检查
            if new_result:
                new_count = new_result['stats']['final_count']
                old_count = len(old_result.get('final_results', []))
                print(f"\n🎯 结果对比:")
                print(f"  新版通过: {new_count} 条")
                print(f"  旧版通过: {old_count} 条")
                
                if new_count == old_count:
                    print(f"  ✅ 结果数量一致")
                else:
                    diff = abs(new_count - old_count)
                    print(f"  ⚠️ 结果数量差异: {diff} 条")
        else:
            print(f"❌ 旧版请求失败: {old_response.status_code}")
            
    except Exception as e:
        print(f"❌ 旧版接口测试出错: {e}")


if __name__ == "__main__":
    print("\n" + "🎯 " * 20)
    print("三层过滤 API 测试")
    print("🎯 " * 20)
    
    # 测试 1: 基础功能测试
    test_three_layer_filter()
    
    # 测试 2: 性能对比（可选）
    # test_compare_with_original()
    
    print("\n" + "="*80)
    print("✅ 测试完成")
    print("="*80)
