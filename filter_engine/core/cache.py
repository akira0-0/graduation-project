# -*- coding: utf-8 -*-
# ⚠️  [REDUNDANT - 待审查是否删除]
# 原因：FilterCache 为旧管道提供 LRU + TTL 缓存，新架构不使用此缓存
#       （L2/L3 的 LLM 调用耗时以 Supabase session 表持久化替代）。
#       仅被 pipeline.py（遗留）和 dynamic_pipeline.py（遗留）使用。
#       删除条件：随 pipeline.py + dynamic_pipeline.py 一起删除即可。
"""
过滤结果缓存
支持相似文本去重和LRU缓存策略
"""
import hashlib
import time
from typing import Optional, Dict, Any, Tuple
from collections import OrderedDict
from dataclasses import dataclass

from ..config import settings
from ..rules.models import FilterResult


@dataclass
class CacheEntry:
    """缓存条目"""
    result: FilterResult
    timestamp: float
    hit_count: int = 0


class FilterCache:
    """
    过滤结果缓存
    
    特性:
    - LRU淘汰策略
    - TTL过期机制
    - 文本哈希去重
    - SimHash相似文本检测（可选）
    """
    
    def __init__(
        self,
        max_size: int = None,
        ttl: int = None,
        enabled: bool = None,
    ):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间(秒)
            enabled: 是否启用缓存
        """
        self.max_size = max_size or settings.CACHE_MAX_SIZE
        self.ttl = ttl or settings.CACHE_TTL
        self.enabled = enabled if enabled is not None else settings.CACHE_ENABLED
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
    
    def _hash_text(self, text: str) -> str:
        """计算文本哈希"""
        # 预处理：去除空白、转小写
        normalized = "".join(text.lower().split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def get(self, text: str) -> Optional[FilterResult]:
        """
        获取缓存结果
        
        Args:
            text: 文本内容
            
        Returns:
            缓存的FilterResult，未命中返回None
        """
        if not self.enabled:
            return None
        
        key = self._hash_text(text)
        
        if key not in self._cache:
            self._stats["misses"] += 1
            return None
        
        entry = self._cache[key]
        
        # 检查是否过期
        if time.time() - entry.timestamp > self.ttl:
            del self._cache[key]
            self._stats["misses"] += 1
            return None
        
        # 更新访问顺序（LRU）
        self._cache.move_to_end(key)
        entry.hit_count += 1
        self._stats["hits"] += 1
        
        return entry.result
    
    def set(self, text: str, result: FilterResult):
        """
        设置缓存
        
        Args:
            text: 文本内容
            result: 过滤结果
        """
        if not self.enabled:
            return
        
        key = self._hash_text(text)
        
        # 如果已存在，更新并移到末尾
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = CacheEntry(
                result=result,
                timestamp=time.time(),
            )
            return
        
        # 检查容量，必要时淘汰
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # 移除最老的
            self._stats["evictions"] += 1
        
        # 添加新条目
        self._cache[key] = CacheEntry(
            result=result,
            timestamp=time.time(),
        )
    
    def delete(self, text: str) -> bool:
        """删除缓存"""
        if not self.enabled:
            return False
        
        key = self._hash_text(text)
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0.0
        
        return {
            "enabled": self.enabled,
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "hit_rate": round(hit_rate, 4),
        }
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        now = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now - entry.timestamp > self.ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)


class SimHashCache(FilterCache):
    """
    SimHash相似文本缓存
    
    对于相似文本返回相同的缓存结果
    """
    
    def __init__(self, similarity_threshold: float = 0.9, **kwargs):
        super().__init__(**kwargs)
        self.similarity_threshold = similarity_threshold
        self._simhash_index: Dict[str, int] = {}  # key -> simhash
    
    def _compute_simhash(self, text: str, hash_bits: int = 64) -> int:
        """计算SimHash"""
        # 简化版SimHash实现
        features = self._extract_features(text)
        
        v = [0] * hash_bits
        for feature in features:
            h = hash(feature) & ((1 << hash_bits) - 1)
            for i in range(hash_bits):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1
        
        simhash = 0
        for i in range(hash_bits):
            if v[i] > 0:
                simhash |= (1 << i)
        
        return simhash
    
    def _extract_features(self, text: str) -> list:
        """提取文本特征（n-gram）"""
        normalized = "".join(text.lower().split())
        n = 3
        return [normalized[i:i+n] for i in range(len(normalized) - n + 1)]
    
    def _hamming_distance(self, h1: int, h2: int) -> int:
        """计算汉明距离"""
        return bin(h1 ^ h2).count('1')
    
    def _find_similar(self, text: str) -> Optional[str]:
        """查找相似文本的缓存键"""
        if not self._simhash_index:
            return None
        
        target_hash = self._compute_simhash(text)
        max_distance = int(64 * (1 - self.similarity_threshold))
        
        for key, h in self._simhash_index.items():
            if self._hamming_distance(target_hash, h) <= max_distance:
                return key
        
        return None
    
    def get(self, text: str) -> Optional[FilterResult]:
        """获取缓存（支持相似匹配）"""
        # 先精确匹配
        result = super().get(text)
        if result:
            return result
        
        # 相似匹配
        similar_key = self._find_similar(text)
        if similar_key and similar_key in self._cache:
            entry = self._cache[similar_key]
            if time.time() - entry.timestamp <= self.ttl:
                self._stats["hits"] += 1
                return entry.result
        
        return None
    
    def set(self, text: str, result: FilterResult):
        """设置缓存（同时更新SimHash索引）"""
        super().set(text, result)
        
        key = self._hash_text(text)
        self._simhash_index[key] = self._compute_simhash(text)
    
    def clear(self):
        """清空缓存"""
        super().clear()
        self._simhash_index.clear()
