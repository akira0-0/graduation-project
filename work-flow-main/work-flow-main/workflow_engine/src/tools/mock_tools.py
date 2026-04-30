"""
Mock 工具集
提供模拟数据收集、过滤、情感分析和报告生成的工具函数
"""
import json
import random
from typing import List, Dict, Any


def mock_collect_data(topic: str) -> List[Dict[str, Any]]:
    """
    模拟[数据收集]智能体
    输入: 话题 (str)
    输出: 包含评论数据的列表
    """
    print(f"DEBUG: [Mock Collector] Collecting data for topic: {topic}")
    return [
        {"id": 1, "content": f"{topic} is amazing! I love it.", "source": "twitter"},
        {"id": 2, "content": f"I had a terrible experience with {topic}.", "source": "reddit"},
        {"id": 3, "content": f"{topic} is okay, but could be better.", "source": "facebook"},
        {"id": 4, "content": f"Why is everyone talking about {topic}?", "source": "news"},
        {"id": 5, "content": f"Best {topic} ever!", "source": "twitter"},
        {"id": 6, "content": f"{topic}这事已上报联合国", "source": "小红书"}
    ]

def mock_filter_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    模拟[数据筛选]智能体
    输入: 原始数据列表
    输出: 筛选后的数据列表 (去除短文本)
    """
    print(f"DEBUG: [Mock Filter] Filtering {len(data)} items")
    return [item for item in data if len(item['content']) > 10]

def mock_sentiment_analysis(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    模拟[情感分析]智能体
    输入: 数据列表
    输出: 带有情感标签的数据列表
    """
    print(f"DEBUG: [Mock Analyst] Analyzing sentiment for {len(data)} items")
    results = []
    for item in data:
        new_item = item.copy()
        # 简单的随机情感模拟
        sentiment = random.choice(["positive", "negative", "neutral"])
        if "amazing" in item['content'] or "Best" in item['content']:
            sentiment = "positive"
        elif "terrible" in item['content']:
            sentiment = "negative"
            
        new_item['sentiment'] = sentiment
        results.append(new_item)
    return results

def mock_compile_report(analyzed_data: List[Dict[str, Any]]) -> str:
    """
    模拟[报告编排]智能体
    输入: 分析后的数据列表
    输出: Markdown 格式的报告
    """
    print(f"DEBUG: [Mock Reporter] Compiling report")
    positive = sum(1 for x in analyzed_data if x['sentiment'] == 'positive')
    negative = sum(1 for x in analyzed_data if x['sentiment'] == 'negative')
    neutral = sum(1 for x in analyzed_data if x['sentiment'] == 'neutral')
    
    report = f"""
# Opinion Analysis Report

## Summary
- Total Items: {len(analyzed_data)}
- Positive: {positive}
- Negative: {negative}
- Neutral: {neutral}

## Details
"""
    for item in analyzed_data:
        report += f"- [{item['sentiment'].upper()}] {item['content']} (Source: {item['source']})\n"
        
    return report