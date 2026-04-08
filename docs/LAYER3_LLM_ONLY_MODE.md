# Layer-3 完全依赖 LLM 判断模式

## 📋 概述

Layer-3 现在支持 **完全依赖 LLM** 进行语义相关性判断，跳过关键词匹配逻辑，直接使用通义千问 API 判断内容与查询的相关性。

## 🎯 设计目标

- **最高准确度**: 让 LLM 直接理解语义，而不是简单的关键词匹配
- **灵活判断**: LLM 可以理解同义词、隐含意图、上下文关系
- **统一接口**: 通过 `--llm-only` 参数简单开启

## 🔧 实现原理

### 1. RelevanceFilter 改进

**位置**: `filter_engine/core/relevance_filter.py`

**新增参数**: `llm_only: bool = False`

```python
def filter_by_relevance(
    self,
    query: str,
    texts: List[str],
    min_relevance: RelevanceLevel = RelevanceLevel.MEDIUM,
    use_llm_for_uncertain: bool = True,
    llm_only: bool = False,  # 新增
) -> Dict[str, Any]:
```

**判断逻辑**:

```python
if llm_only:
    # 完全使用 LLM 判断模式
    result = self._llm_judge_relevance(text, query, core_entity)
    if result is None:
        # LLM 调用失败，返回低相关
        result = RelevanceResult(
            content=text,
            relevance=RelevanceLevel.LOW,
            score=0.3,
            reason="LLM 调用失败，默认低相关",
        )
else:
    # 混合模式（关键词 + LLM）
    result = self._judge_relevance(...)
```

### 2. LLM 判断提示词

**位置**: `filter_engine/core/relevance_filter.py` 第 349-375 行

```python
def _llm_judge_relevance(self, text: str, query: str, core_entity: str):
    prompt = f"""判断以下内容与用户查询的相关性。

用户查询: {query}
核心主题: {core_entity}

待判断内容:
{text[:500]}

请用JSON格式回答:
{{
    "relevance": "high/medium/low/irrelevant",
    "score": 0.0-1.0,
    "reason": "简要说明原因"
}}

只返回JSON，不要其他内容。"""
```

**LLM 调用**:
```python
response = self.llm_engine.client.chat_sync(
    messages=messages,
    temperature=0.1,
    max_tokens=200,
)
```

### 3. 通义千问 API 集成

**位置**: `filter_engine/llm/client.py` 第 125-175 行

```python
class QwenClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "qwen-turbo"):
        self.api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
    
    def chat_sync(self, messages, temperature=0.1, max_tokens=500):
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # POST 请求到通义千问 API
        response = client.post(url, json=payload, headers=self.headers)
        return LLMResponse(content=data["choices"][0]["message"]["content"], ...)
```

## 📦 使用方式

### 1. 独立运行 Layer-3 脚本

```bash
# 完全依赖 LLM 判断（推荐）
uv run python scripts/batch_llm_filter.py \
  --session-id sess_20260409_123456 \
  --query "丽江有什么好玩的景点和美食" \
  --llm-only

# 混合模式（关键词 + LLM，默认）
uv run python scripts/batch_llm_filter.py \
  --session-id sess_20260409_123456 \
  --query "丽江有什么好玩的景点和美食"

# 只用关键词（快速模式）
uv run python scripts/batch_llm_filter.py \
  --session-id sess_20260409_123456 \
  --query "丽江有什么好玩的景点和美食" \
  --no-llm
```

### 2. Layer-2 自动链接到 Layer-3

**位置**: `scripts/batch_scene_filter_smart.py` 第 870-890 行

```python
if not args.skip_layer3 and not args.dry_run:
    print(f"🚀 自动启动 Layer-3 语义相关性过滤")
    rf = RelevanceFilter(use_llm=use_llm_layer3)
    await run_layer3_filter(
        supabase=supabase,
        rf=rf,
        session_id=session_id,
        query=query_text,
        min_relevance=min_rel_layer3,
        use_llm=use_llm_layer3,
    )
```

**Layer-3 调用逻辑**（第 966 行）:
```python
# 默认使用 LLM Only 模式
result = rf.filter_by_relevance(
    query=query,
    texts=texts,
    min_relevance=min_relevance,
    use_llm_for_uncertain=use_llm,
    llm_only=True,  # Layer-3 完全依赖 LLM
)
```

**运行 Layer-2 时自动触发 Layer-3**:
```bash
uv run python scripts/batch_scene_filter_smart.py \
  --query "保留关于贵金属、黄金分析、投资建议的财经内容"
```

## 🎨 三种模式对比

| 模式 | 参数 | 判断逻辑 | 准确度 | 速度 | 成本 |
|------|------|----------|--------|------|------|
| **LLM Only** | `--llm-only` | 每条都调 LLM | ⭐⭐⭐⭐⭐ | 慢 | 高 |
| **混合模式** | 默认 | 关键词 0.15-0.7 → LLM | ⭐⭐⭐⭐ | 中 | 中 |
| **关键词模式** | `--no-llm` | 只用关键词匹配 | ⭐⭐⭐ | 快 | 低 |

### LLM Only 模式优势

**场景 1: 同义词识别**
- Query: "丽江有什么好玩的"
- Content: "丽江的景色太美了，每个角落都值得探索"
- 关键词: 只匹配到"丽江" (score=0.5)
- **LLM**: 识别"景色美"、"探索" 暗示"好玩" → high (score=0.85)

**场景 2: 隐含意图**
- Query: "黄金投资建议"
- Content: "最近黄金价格波动很大，建议观望，等回调后再入场"
- 关键词: 匹配"黄金" (score=0.5)
- **LLM**: 识别"价格波动"、"建议观望" 是投资建议 → high (score=0.92)

**场景 3: 上下文理解**
- Query: "成都美食推荐"
- Content: "火锅是成都的灵魂，一定要去宽窄巷子体验"
- 关键词: 只匹配"成都" (score=0.5)
- **LLM**: 识别"火锅"、"宽窄巷子" 与美食相关 → high (score=0.88)

## 🔍 日志输出

启用 LLM Only 模式后，会看到如下日志：

```
============================================================
  Layer-3 LLM 语义过滤
  session_id : sess_20260409_123456
  query      : 丽江有什么好玩的
  min_rel    : medium
  use_llm    : True
  llm_only   : True  ← 关键标识
  dry_run    : False
  clear_old  : False
============================================================

── Step 1-2: 帖子相关性过滤 ──
  从 session_l2_posts 读取 150 条帖子
  🤖 调用 LLM 判断相关性...  ← LLM 调用日志
  ✅ LLM 响应: {"relevance": "high", "score": 0.87, "reason": "内容详细介绍了丽江的景点"}...
  🤖 调用 LLM 判断相关性...
  ✅ LLM 响应: {"relevance": "medium", "score": 0.65, "reason": "提到丽江但主要讲交通"}...
  ...

  帖子过滤完成：总计 150 条，通过 68 条 (45.3%)，耗时 120.5s
```

## ⚙️ 配置说明

### API Key 配置

**位置**: `filter_engine/config.py` 或环境变量

```python
LLM_PROVIDER = "qwen"
LLM_API_KEY = "sk-xxx"  # 通义千问 API Key
LLM_MODEL = "qwen-turbo"
```

或通过环境变量:
```bash
export LLM_API_KEY="sk-xxx"
export LLM_MODEL="qwen-turbo"
```

### 相关性级别

```python
class RelevanceLevel(Enum):
    HIGH = "high"           # 0.7-1.0: 高度相关
    MEDIUM = "medium"       # 0.4-0.7: 中等相关
    LOW = "low"             # 0.2-0.4: 低相关
    IRRELEVANT = "irrelevant"  # 0.0-0.2: 不相关
```

**--min-relevance 参数**:
- `high`: 只保留 HIGH 级别
- `medium`: 保留 HIGH + MEDIUM（默认）
- `low`: 保留 HIGH + MEDIUM + LOW

## 📊 性能考虑

### API 调用次数

- **LLM Only 模式**: 每条内容调用 1 次 LLM
- **混合模式**: 约 30-50% 内容调用 LLM（关键词 0.15-0.7 区间）
- **关键词模式**: 0 次 LLM 调用

### 示例计算

假设 Layer-2 输出 **1000 条帖子**:

| 模式 | LLM 调用次数 | 耗时 (估算) | 成本 (估算) |
|------|--------------|-------------|-------------|
| LLM Only | ~1000 次 | ~200s | ¥0.20 |
| 混合模式 | ~400 次 | ~80s | ¥0.08 |
| 关键词 | 0 次 | ~5s | ¥0.00 |

*假设通义千问 qwen-turbo 模型: ¥0.0002/次, 每次 0.2s*

### 优化建议

1. **分批处理**: 如果数据量太大，可以分批运行
   ```bash
   # 分批读取 Layer-2 数据
   SELECT * FROM session_l2_posts WHERE session_id='xxx' LIMIT 500 OFFSET 0;
   ```

2. **缓存结果**: 相同内容+查询的判断结果可以缓存
   
3. **异步调用**: 未来可改为 `async` 并发调用 LLM，提升速度

## 🐛 错误处理

### LLM 调用失败

```python
if result is None:
    # LLM 调用失败，返回低相关
    result = RelevanceResult(
        content=text,
        relevance=RelevanceLevel.LOW,
        score=0.3,
        reason="LLM 调用失败，默认低相关",
    )
```

**日志输出**:
```
  ⚠️ LLM 调用失败: Connection timeout
```

### 降级策略

如果 LLM 多次失败，可以：
1. 检查 API Key 是否正确
2. 检查网络连接
3. 切换到混合模式 (去掉 `--llm-only`)
4. 使用关键词模式 (`--no-llm`) 快速处理

## 📝 测试示例

### 测试命令

```bash
# 1. 先运行 Layer-2（SmartRuleMatcher）
uv run python scripts/batch_scene_filter_smart.py \
  --query "保留关于丽江旅游、景点、美食的真实体验分享" \
  --skip-layer3  # 先跳过 Layer-3

# 2. 单独测试 Layer-3 LLM Only 模式
uv run python scripts/batch_llm_filter.py \
  --session-id sess_20260409_143022_a1b2 \
  --query "丽江旅游景点美食体验" \
  --llm-only \
  --dry-run  # 先试运行

# 3. 确认无误后正式运行
uv run python scripts/batch_llm_filter.py \
  --session-id sess_20260409_143022_a1b2 \
  --query "丽江旅游景点美食体验" \
  --llm-only
```

### 预期结果

```sql
-- 查看 Layer-3 结果
SELECT 
    post_id,
    (post_data->>'title') as title,
    (post_data->>'relevance_score')::float as score,
    (post_data->>'relevance_level') as level,
    comment_count
FROM session_l3_results
WHERE session_id = 'sess_20260409_143022_a1b2'
ORDER BY (post_data->>'relevance_score')::float DESC;
```

**示例输出**:
```
post_id     | title                        | score | level  | comment_count
------------|------------------------------|-------|--------|---------------
6a7b8c9d... | 丽江古城深度游攻略           | 0.92  | high   | 15
7b8c9d0e... | 束河古镇vs丽江古城，哪个好玩  | 0.88  | high   | 8
8c9d0e1f... | 丽江必吃美食TOP10            | 0.85  | high   | 12
9d0e1f2g... | 云南旅游路线规划             | 0.68  | medium | 5
```

## 🔗 相关文档

- **Layer-2 规则优化**: `docs/LAYER2_RULE_RELAXATION.md`
- **SmartRuleMatcher**: `docs/LAYER2_SMART_LLM_ONLY.md`
- **自动化流水线**: `docs/LAYER2_LAYER3_AUTO_PIPELINE.md`
- **数据格式规范**: `docs/DATA_FORMAT_STANDARD.md`

## 📅 更新日志

**2026-04-09**
- ✅ 新增 `llm_only` 参数到 `filter_by_relevance()`
- ✅ 修改 `batch_llm_filter.py` 支持 `--llm-only`
- ✅ 更新 `batch_scene_filter_smart.py` 默认使用 LLM Only
- ✅ 添加 LLM 调用日志输出
- ✅ 完善错误处理和降级策略

---

**总结**: Layer-3 现在完全依赖通义千问 LLM 进行语义判断，提供最高准确度的相关性过滤！🎉
