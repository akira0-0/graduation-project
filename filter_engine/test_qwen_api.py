# -*- coding: utf-8 -*-
"""测试千问 API 连接"""
import asyncio
from llm.client import get_llm_client
from config import settings

async def test_qwen():
    print(f"配置信息:")
    print(f"  Provider: {settings.LLM_PROVIDER}")
    print(f"  Model: {settings.LLM_MODEL}")
    print(f"  API Base: {settings.LLM_API_BASE}")
    print(f"  API Key: {settings.LLM_API_KEY[:20]}..." if settings.LLM_API_KEY else "  API Key: None")
    print()
    
    client = get_llm_client()
    
    messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己"}
    ]
    
    print("发送测试请求...")
    try:
        response = await client.chat(messages, temperature=0.7, max_tokens=100)
        print(f"\n✅ 成功!")
        print(f"回复: {response.content}")
        print(f"模型: {response.model}")
        print(f"用量: {response.usage}")
    except Exception as e:
        print(f"\n❌ 失败!")
        print(f"错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_qwen())
