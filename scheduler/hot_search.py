# -*- coding: utf-8 -*-
"""
微博热搜获取模块
"""
import requests
import json
import re
from typing import List, Set
import jieba
import jieba.posseg as pseg
from .logger import get_logger

logger = get_logger(__name__)

# 停用词列表
STOP_WORDS: Set[str] = {
    '的', '是', '在', '了', '和', '与', '或', '等', '也', '都', '就', '而', '及',
    '着', '到', '把', '被', '让', '给', '从', '向', '为', '对', '以', '将', '能',
    '会', '可', '要', '想', '应', '该', '这', '那', '之', '其', '它', '他', '她',
    '我', '你', '们', '什么', '怎么', '如何', '为什么', '哪', '谁', '多少',
    '已', '曾', '正', '又', '再', '还', '却', '但', '因', '所', '如', '若',
    '后', '前', '上', '下', '中', '内', '外', '间', '时', '年', '月', '日',
    '确认', '宣布', '表示', '称', '说', '认为', '指出', '强调', '透露',
    '或将', '可能', '疑似', '据称', '据悉', '曝光', '回应', '引发', '导致',
}

# 保留的词性（名词、人名、地名、机构名、其他专名）
KEEP_POS: Set[str] = {'n', 'nr', 'ns', 'nt', 'nz', 'vn', 'an', 'eng'}


def extract_keywords(text: str, max_keywords: int = 2) -> List[str]:
    """
    从热搜文本中提取核心关键词
    
    Args:
        text: 热搜原文，如 "伊朗确认继任者后或将扩大反击"
        max_keywords: 最多提取的关键词数量
        
    Returns:
        核心关键词列表，如 ["伊朗"]
    """
    if not text:
        return []
    
    # jieba 分词 + 词性标注
    words = pseg.cut(text)
    
    keywords = []
    for word, pos in words:
        # 跳过停用词
        if word in STOP_WORDS:
            continue
        
        # 跳过单字（除非是专有名词）
        if len(word) < 2 and pos not in {'nr', 'ns', 'nt', 'nz'}:
            continue
        
        # 只保留特定词性
        if pos in KEEP_POS:
            keywords.append(word)
            if len(keywords) >= max_keywords:
                break
    
    # 如果没有提取到，返回原文前几个字
    if not keywords:
        # 尝试取前4个字作为关键词
        keywords = [text[:4]] if len(text) >= 4 else [text]
    
    return keywords


def simplify_hot_words(hot_words: List[str], max_keywords_per_word: int = 1) -> List[str]:
    """
    简化热搜词列表，提取核心关键词
    
    Args:
        hot_words: 原始热搜词列表
        max_keywords_per_word: 每个热搜词提取的关键词数量
        
    Returns:
        简化后的关键词列表（去重）
    """
    simplified = []
    seen = set()
    
    for word in hot_words:
        keywords = extract_keywords(word, max_keywords=max_keywords_per_word)
        for kw in keywords:
            if kw not in seen and len(kw) >= 2:
                seen.add(kw)
                simplified.append(kw)
    
    return simplified


def get_weibo_hot_search(count: int = 15, simplify: bool = True) -> List[str]:
    """
    获取微博热搜词
    
    Args:
        count: 获取热搜词数量
        simplify: 是否简化热搜词（提取核心关键词）
        
    Returns:
        热搜词列表
    """
    hot_words = []
    
    try:
        # 使用微博热搜榜 API (无需登录)
        url = "https://weibo.com/ajax/side/hotSearch"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://weibo.com/",
        }
        
        logger.info("正在获取微博热搜...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # 解析热搜数据
        realtime = data.get('data', {}).get('realtime', [])
        for item in realtime:
            word = item.get('word', '')
            if word:
                clean_word = clean_hot_word(word)
                if clean_word and clean_word not in hot_words:
                    hot_words.append(clean_word)
                    if len(hot_words) >= count * 2:  # 多取一些，简化后会去重
                        break
        
        # 如果上面的方式获取失败，尝试备用方式
        if not hot_words:
            hot_words = get_hot_search_backup(count)
        
        # 显示原始热搜词
        logger.info(f"获取到 {len(hot_words)} 个原始热搜词")
        for i, word in enumerate(hot_words[:5], 1):
            logger.info(f"  {i}. {word}")
        if len(hot_words) > 5:
            logger.info(f"  ... 还有 {len(hot_words) - 5} 个")
        
        # 简化热搜词
        if simplify:
            original_words = hot_words.copy()
            # 为每个原词提取关键词，用于日志显示
            keyword_mapping = []
            for word in original_words[:10]:
                kws = extract_keywords(word, max_keywords=1)
                keyword_mapping.append((word, kws[0] if kws else word))
            
            hot_words = simplify_hot_words(hot_words, max_keywords_per_word=1)
            logger.info(f"简化后得到 {len(hot_words)} 个核心关键词:")
            for i, (orig, simp) in enumerate(keyword_mapping, 1):
                logger.info(f"  {i}. {orig} → {simp}")
            
    except Exception as e:
        logger.error(f"获取微博热搜失败: {e}")
        # 返回备用关键词
        hot_words = get_fallback_keywords()
        logger.warning(f"使用备用关键词: {hot_words}")
    
    return hot_words[:count]


def get_hot_search_backup(count: int) -> List[str]:
    """
    备用方式获取热搜（从网页解析）
    """
    try:
        url = "https://s.weibo.com/top/summary"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cookie": ""  # 可能需要 Cookie
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # 简单正则提取热搜词
        pattern = r'<td class="td-02">.*?<a.*?>(.+?)</a>'
        matches = re.findall(pattern, response.text)
        
        hot_words = []
        for match in matches:
            word = clean_hot_word(match)
            if word and word not in hot_words:
                hot_words.append(word)
                if len(hot_words) >= count:
                    break
        
        return hot_words
        
    except Exception as e:
        logger.warning(f"备用方式获取热搜失败: {e}")
        return []


def clean_hot_word(word: str) -> str:
    """
    清理热搜词
    """
    if not word:
        return ""
    
    # 去除 HTML 标签
    word = re.sub(r'<[^>]+>', '', word)
    
    # 去除特殊标记（如 [沸]、[热]、[新] 等）
    word = re.sub(r'\[.+?\]', '', word)
    
    # 去除首尾空白
    word = word.strip()
    
    # 过滤太短或太长的词
    if len(word) < 2 or len(word) > 30:
        return ""
    
    # 过滤广告词
    ad_keywords = ['广告', '推广', '赞助']
    for ad in ad_keywords:
        if ad in word:
            return ""
    
    return word


def get_fallback_keywords() -> List[str]:
    """
    获取备用关键词（当热搜获取失败时使用）
    """
    return [
        "人工智能",
        "科技新闻",
        "热点事件",
        "社会民生",
        "娱乐八卦",
    ]


if __name__ == "__main__":
    # 测试
    keywords = get_weibo_hot_search(15)
    print(f"\n获取到 {len(keywords)} 个热搜词:")
    for i, kw in enumerate(keywords, 1):
        print(f"  {i}. {kw}")
