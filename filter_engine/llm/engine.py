# -*- coding: utf-8 -*-
# ⚠️  [半必要 - 待审查能否合并]
# 原因：LLMEngine 封装了"构建 prompt → 调用 LLM → 解析输出"的垃圾过滤流程，
#       被 pipeline.py（遗留）、dynamic_pipeline.py（遗留）使用，
#       同时也被 relevance_filter.py（核心，L3 相关性）直接依赖。
#       因此不能和 pipeline.py/dynamic_pipeline.py 一起删除。
#       优化方向：relevance_filter.py 中的 LLM 调用可直接改用 llm/client.py，
#                 届时 engine.py + prompts.py + parser.py 才能一起移除。
"""
LLM过滤引擎
集成LLM客户端、提示词和解析器
"""
import asyncio
from typing import List, Optional, Dict, Any

from ..config import settings
from ..rules.models import LLMResult
from .client import create_llm_client, BaseLLMClient, LLMResponse
from .prompts import build_filter_prompt, build_batch_filter_prompt, build_context_filter_prompt
from .parser import parse_llm_output, parse_batch_output


class LLMEngine:
    """
    LLM过滤引擎
    
    负责:
    - 调用LLM进行语义分析
    - 处理单条和批量过滤请求
    - 管理LLM调用的错误处理和重试
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 2,
    ):
        """
        初始化LLM引擎
        
        Args:
            provider: LLM提供商
            api_key: API密钥
            model: 模型名称
            max_retries: 最大重试次数
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.max_retries = max_retries
        
        self._client: Optional[BaseLLMClient] = None
    
    @property
    def client(self) -> BaseLLMClient:
        """懒加载LLM客户端"""
        if self._client is None:
            self._client = create_llm_client(
                provider=self.provider,
                api_key=self.api_key,
                model=self.model,
            )
        return self._client
    
    def is_available(self) -> bool:
        """检查LLM是否可用"""
        return bool(self.api_key) or self.provider == "ollama"
    
    def filter(
        self,
        text: str,
        context: Optional[str] = None,
        rule_hints: Optional[List[str]] = None,
    ) -> LLMResult:
        """
        同步过滤文本
        
        Args:
            text: 待过滤文本
            context: 上下文信息
            rule_hints: 规则提示
            
        Returns:
            LLMResult
        """
        if not self.is_available():
            return LLMResult(
                is_spam=False,
                confidence=0.0,
                reason="LLM不可用",
            )
        
        try:
            # 构建提示词
            if context or rule_hints:
                messages = build_context_filter_prompt(text, context, rule_hints)
            else:
                messages = build_filter_prompt(text, with_examples=True)
            
            # 调用LLM
            response = self._call_with_retry_sync(messages)
            
            # 解析结果
            return parse_llm_output(response.content)
            
        except Exception as e:
            return LLMResult(
                is_spam=False,
                confidence=0.0,
                reason=f"LLM调用失败: {str(e)[:100]}",
            )
    
    async def filter_async(
        self,
        text: str,
        context: Optional[str] = None,
        rule_hints: Optional[List[str]] = None,
    ) -> LLMResult:
        """
        异步过滤文本
        
        Args:
            text: 待过滤文本
            context: 上下文信息
            rule_hints: 规则提示
            
        Returns:
            LLMResult
        """
        if not self.is_available():
            return LLMResult(
                is_spam=False,
                confidence=0.0,
                reason="LLM不可用",
            )
        
        try:
            # 构建提示词
            if context or rule_hints:
                messages = build_context_filter_prompt(text, context, rule_hints)
            else:
                messages = build_filter_prompt(text, with_examples=True)
            
            # 调用LLM
            response = await self._call_with_retry_async(messages)
            
            # 解析结果
            return parse_llm_output(response.content)
            
        except Exception as e:
            return LLMResult(
                is_spam=False,
                confidence=0.0,
                reason=f"LLM调用失败: {str(e)[:100]}",
            )
    
    def filter_batch(self, texts: List[str]) -> List[LLMResult]:
        """
        同步批量过滤
        
        Args:
            texts: 文本列表
            
        Returns:
            LLMResult列表
        """
        if not self.is_available():
            return [LLMResult(is_spam=False, confidence=0.0, reason="LLM不可用") for _ in texts]
        
        if not texts:
            return []
        
        # 分批处理（每批最多10条）
        batch_size = 10
        all_results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                messages = build_batch_filter_prompt(batch)
                response = self._call_with_retry_sync(messages)
                results = parse_batch_output(response.content)
                
                # 确保结果数量匹配
                while len(results) < len(batch):
                    results.append(LLMResult(is_spam=False, confidence=0.0))
                
                all_results.extend(results[:len(batch)])
                
            except Exception as e:
                # 批量失败时，逐条处理
                for text in batch:
                    all_results.append(self.filter(text))
        
        return all_results
    
    async def filter_batch_async(self, texts: List[str]) -> List[LLMResult]:
        """
        异步批量过滤
        
        Args:
            texts: 文本列表
            
        Returns:
            LLMResult列表
        """
        if not self.is_available():
            return [LLMResult(is_spam=False, confidence=0.0, reason="LLM不可用") for _ in texts]
        
        if not texts:
            return []
        
        # 并发处理每条文本
        tasks = [self.filter_async(text) for text in texts]
        return await asyncio.gather(*tasks)
    
    def _call_with_retry_sync(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """同步调用LLM（带重试）"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return self.client.chat_sync(
                    messages=messages,
                    temperature=0.1,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    import time
                    time.sleep(1 * (attempt + 1))  # 指数退避
        
        raise last_error
    
    async def _call_with_retry_async(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """异步调用LLM（带重试）"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await self.client.chat(
                    messages=messages,
                    temperature=0.1,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(1 * (attempt + 1))
        
        raise last_error
