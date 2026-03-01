# -*- coding: utf-8 -*-
"""测试热搜获取"""
import requests

def test_hot_search():
    url = "https://weibo.com/ajax/side/hotSearch"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://weibo.com/",
    }
    
    print("正在获取微博热搜...")
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"状态码: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            realtime = data.get('data', {}).get('realtime', [])
            print(f"获取到 {len(realtime)} 个热搜")
            
            for i, item in enumerate(realtime[:15], 1):
                word = item.get('word', '')
                print(f"  {i}. {word}")
        else:
            print(f"请求失败: {r.text[:200]}")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    test_hot_search()
