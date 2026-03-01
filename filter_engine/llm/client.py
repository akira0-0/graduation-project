# -*- coding: utf-8 -*-
"""
LLM API客户端
支持多种LLM提供商的统一接口
"""
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

import httpx

from ..config import settings


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    usage: Dict[str, int]
    raw_response: Optional[Dict] = None


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """发送聊天请求"""
        pass
    
    @abstractmethod
    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """同步发送聊天请求"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI兼容API客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_key = api_key or settings.LLM_API_KEY
        self.api_base = (api_base or settings.LLM_API_BASE or "https://api.openai.com/v1").rstrip("/")
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """异步发送聊天请求"""
        url = f"{self.api_base}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            raw_response=data,
        )
    
    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """同步发送聊天请求"""
        url = f"{self.api_base}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            raw_response=data,
        )


class QwenClient(OpenAIClient):
    """通义千问客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen-turbo",
        timeout: int = 30,
    ):
        super().__init__(
            api_key=api_key,
            api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=model,
            timeout=timeout,
        )


class GLMClient(OpenAIClient):
    """智谱GLM客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "glm-4-flash",
        timeout: int = 30,
    ):
        super().__init__(
            api_key=api_key,
            api_base="https://open.bigmodel.cn/api/paas/v4",
            model=model,
            timeout=timeout,
        )


class OllamaClient(BaseLLMClient):
    """Ollama本地模型客户端"""
    
    def __init__(
        self,
        api_base: str = "http://localhost:11434",
        model: str = "llama2",
        timeout: int = 60,
    ):
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.timeout = timeout
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """异步发送聊天请求"""
        url = f"{self.api_base}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        
        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=self.model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            raw_response=data,
        )
    
    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """同步发送聊天请求"""
        url = f"{self.api_base}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        
        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=self.model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            raw_response=data,
        )


def create_llm_client(
    provider: Optional[str] = None,
    **kwargs
) -> BaseLLMClient:
    """
    创建LLM客户端
    
    Args:
        provider: 提供商名称 (openai, qwen, glm, ollama)
        **kwargs: 客户端参数
    
    Returns:
        LLM客户端实例
    """
    provider = provider or settings.LLM_PROVIDER
    
    clients = {
        "openai": OpenAIClient,
        "qwen": QwenClient,
        "glm": GLMClient,
        "ollama": OllamaClient,
    }
    
    client_class = clients.get(provider.lower(), OpenAIClient)
    return client_class(**kwargs)
