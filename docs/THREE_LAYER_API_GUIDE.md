# 三层过滤 API 使用指南

## 📖 概述

新的三层过滤 API 提供了一个**高效、简洁**的接口来处理内容过滤任务。相比原有的分散式 API，新接口具有以下优势：

### ✨ 核心特性

1. **统一接口** - 一个 API 完成三层过滤，无需多次调用
2. **性能优化** - 批量处理、早停策略、并发优化
3. **灵活控制** - 每层可独立开关，参数细粒度可调
4. **详细追踪** - 返回每层统计、性能数据和通过路径
5. **会话管理** - 支持 Session ID 追踪过滤任务

---

## 🚀 快速开始

### 基础用法

```bash
curl -X POST "http://localhost:8081/api/filter/three-layer" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "丽江旅游攻略",
    "contents": [
      "丽江古城深度游攻略，推荐这几个景点...",
      "加微信xxx，低价代购旅游套餐！！！",
      "今天天气真好"
    ]
  }'
```

### Python 示例

```python
import requests

response = requests.post(
    "http://localhost:8081/api/filter/three-layer",
    json={
        "query": "丽江旅游攻略",
        "contents": [
            "丽江古城深度游攻略...",
            "广告：加微信...",
        ],
        "enable_layer1": True,
        "enable_layer2": True,
        "enable_layer3": True,
        "min_relevance": "medium",
        "llm_only": True,
    }
)

result = response.json()
print(f"通过 {result['stats']['final_count']} 条内容")
```

---

## 📝 API 参考

### 请求地址

```
POST /api/filter/three-layer
```

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 用户查询，如"丽江旅游攻略" |
| `contents` | array[string] | ✅ | - | 待过滤内容列表（最多 1000 条） |
| `session_id` | string | ❌ | 自动生成 | Session ID（用于追踪） |
| `platform` | string | ❌ | null | 平台标识（xhs/weibo） |
| **Layer-1 控制** | | | | |
| `enable_layer1` | boolean | ❌ | `true` | 是否启用 Layer-1 基础规则过滤 |
| `min_content_length` | integer | ❌ | `4` | 最小内容长度（字符数） |
| **Layer-2 控制** | | | | |
| `enable_layer2` | boolean | ❌ | `true` | 是否启用 Layer-2 场景规则过滤 |
| `force_scenario` | string | ❌ | null | 强制指定场景（normal/ecommerce/news...） |
| `save_gap_rules` | boolean | ❌ | `false` | 是否保存 LLM 生成的补充规则 |
| **Layer-3 控制** | | | | |
| `enable_layer3` | boolean | ❌ | `true` | 是否启用 Layer-3 语义相关性过滤 |
| `min_relevance` | string | ❌ | `"medium"` | 最低相关性（high/medium/low） |
| `llm_only` | boolean | ❌ | `true` | Layer-3 是否完全依赖 LLM 判断 |
| **性能优化** | | | | |
| `batch_size` | integer | ❌ | `100` | 批处理大小（10-500） |
| `max_workers` | integer | ❌ | `3` | 并发处理线程数（1-10） |

### 响应格式

```json
{
  "session_id": "sess_1712345678_100",
  "query": "丽江旅游攻略",
  "stats": {
    "total_input": 100,
    "layer1_passed": 85,
    "layer2_passed": 42,
    "layer3_passed": 28,
    "final_count": 28
  },
  "results": [
    {
      "index": 0,
      "content": "丽江古城深度游攻略...",
      "relevance_score": 0.92,
      "relevance_level": "high",
      "layers_passed": ["layer1_passed", "layer2_passed", "layer3_passed"]
    }
  ],
  "performance": {
    "layer1": 0.5,
    "layer2": 12.3,
    "layer3": 8.7,
    "total": 21.5
  },
  "metadata": {
    "scenario": "social",
    "min_relevance": "medium"
  }
}
```

---

## 🎯 使用场景

### 场景 1: 标准三层过滤

```python
# 适用于：需要完整过滤的内容（帖子、评论等）
response = requests.post(url, json={
    "query": "丽江旅游推荐",
    "contents": raw_contents,
    # 使用默认配置即可
})
```

### 场景 2: 只过滤垃圾内容（Layer-1）

```python
# 适用于：快速清洗明显垃圾（广告、涉黄涉政）
response = requests.post(url, json={
    "query": "任意查询",
    "contents": raw_contents,
    "enable_layer1": True,
    "enable_layer2": False,  # 🔴 关闭 Layer-2
    "enable_layer3": False,  # 🔴 关闭 Layer-3
})
```

### 场景 3: 只用场景规则（Layer-1 + Layer-2）

```python
# 适用于：需要场景过滤但不需要语义判断
response = requests.post(url, json={
    "query": "电商好评返现",
    "contents": raw_contents,
    "enable_layer1": True,
    "enable_layer2": True,
    "enable_layer3": False,  # 🔴 关闭 Layer-3（省时间）
    "force_scenario": "ecommerce",
})
```

### 场景 4: 只用语义过滤（Layer-3）

```python
# 适用于：数据已预清洗，只需相关性判断
response = requests.post(url, json={
    "query": "丽江有什么好玩的",
    "contents": pre_filtered_contents,
    "enable_layer1": False,  # 🔴 已预处理
    "enable_layer2": False,  # 🔴 已预处理
    "enable_layer3": True,
    "llm_only": True,
    "min_relevance": "high",  # 高相关性要求
})
```

### 场景 5: 高性能批量处理

```python
# 适用于：大批量内容（500+ 条）
response = requests.post(url, json={
    "query": "旅游攻略",
    "contents": large_contents[:1000],  # 最多 1000 条
    "batch_size": 200,      # 🚀 增大批次
    "max_workers": 5,       # 🚀 增加并发
    "llm_only": False,      # 🚀 混合模式（减少 LLM 调用）
})
```

---

## ⚡ 性能优化建议

### 1. 早停策略

API 自动检测各层通过率，若某层无内容通过则直接返回，避免无效计算：

```python
# 示例：100 条内容全被 Layer-1 拦截
{
  "stats": {"layer1_passed": 0, "final_count": 0},
  "results": [],
  "metadata": {
    "early_stop": "layer1",
    "reason": "no_content_passed"
  }
}
```

### 2. 批量处理

合理设置 `batch_size` 可减少网络开销：

| 内容数量 | 推荐 batch_size |
|---------|----------------|
| < 50    | 50             |
| 50-200  | 100（默认）     |
| 200-500 | 200            |
| 500+    | 300-500        |

### 3. 并发控制

`max_workers` 控制并发线程数（当前版本预留，后续支持）：

```python
# 大批量任务
"max_workers": 5  # 增加并发
```

### 4. Layer 选择性启用

根据需求关闭不必要的层：

```python
# 只需基础过滤 → 关闭 Layer-2/3
"enable_layer2": False,
"enable_layer3": False,

# 只需相关性 → 关闭 Layer-1/2
"enable_layer1": False,
"enable_layer2": False,
```

---

## 📊 与旧版接口对比

| 特性 | 新接口 `/api/filter/three-layer` | 旧接口 `/api/pipeline/run` |
|------|--------------------------------|---------------------------|
| **统一性** | ✅ 单一接口 | ❌ 功能分散 |
| **性能** | ✅ 批量+早停+并发 | ⚠️ 逐条处理 |
| **灵活性** | ✅ 细粒度参数控制 | ⚠️ 参数较少 |
| **追踪** | ✅ 详细性能+通过路径 | ⚠️ 统计较简单 |
| **返回格式** | ✅ 结构化+索引 | ⚠️ 嵌套复杂 |
| **Session** | ✅ 支持 Session ID | ✅ 支持 |

**推荐**：新项目使用新接口，旧项目逐步迁移。

---

## 🔧 测试与调试

### 运行测试脚本

```bash
# 确保 API 服务已启动
uv run uvicorn filter_engine.api:app --host 0.0.0.0 --port 8081

# 运行测试
uv run python scripts/test_three_layer_api.py
```

### 测试输出示例

```
🧪 测试三层过滤 API (优化版)
============================================================
📝 请求配置:
  Query: 丽江旅游攻略
  内容数: 10 条
  Layer-1: True
  Layer-2: True
  Layer-3: True (LLM Only: True)

🚀 发送请求到 http://localhost:8081/api/filter/three-layer ...
✅ 请求成功 (耗时 15.23s)

📊 统计信息:
  总输入: 10 条
  Layer-1 通过: 7 条 (70.0%)
  Layer-2 通过: 5 条 (50.0%)
  Layer-3 通过: 3 条 (30.0%)
  最终结果: 3 条

⚡ 性能分析:
  Layer-1 耗时: 0.12s
  Layer-2 耗时: 8.45s
  Layer-3 耗时: 6.66s
  总耗时: 15.23s

✨ 最终通过的内容 (3 条):
  1. [high | 0.920] 丽江古城深度游攻略，推荐这几个景点必去...
     通过路径: layer1_passed → layer2_passed → layer3_passed
```

---

## 🐛 常见问题

### Q1: 内容过多导致超时？

**A**: 分批处理或增大 `batch_size`：

```python
# 分批处理
for i in range(0, len(all_contents), 1000):
    batch = all_contents[i:i+1000]
    response = requests.post(url, json={
        "contents": batch,
        "batch_size": 300,  # 增大批次
    })
```

### Q2: Layer-3 太慢？

**A**: 三种优化方案：

1. **关闭 Layer-3**（不需要语义判断时）
   ```python
   "enable_layer3": False
   ```

2. **使用混合模式**（减少 LLM 调用）
   ```python
   "llm_only": False  # 关键词+LLM 混合
   ```

3. **降低相关性要求**（减少过滤数量）
   ```python
   "min_relevance": "low"  # 更宽松
   ```

### Q3: 如何追踪过滤任务？

**A**: 使用 `session_id`：

```python
# 请求时指定
response = requests.post(url, json={
    "session_id": "my_task_001",
    # ...
})

# 后续查询（如果启用了 Session 存储）
GET /api/sessions/my_task_001/metadata
```

---

## 📚 完整示例

### Python Agent 集成

```python
class ContentFilterAgent:
    """内容过滤 Agent"""
    
    def __init__(self, api_url="http://localhost:8081"):
        self.api_url = api_url
    
    def filter_contents(self, query, contents, **kwargs):
        """三层过滤"""
        response = requests.post(
            f"{self.api_url}/api/filter/three-layer",
            json={
                "query": query,
                "contents": contents,
                **kwargs,
            },
            timeout=180,
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Filter failed: {response.text}")
    
    def get_high_quality_contents(self, query, raw_contents):
        """获取高质量内容（严格过滤）"""
        result = self.filter_contents(
            query=query,
            contents=raw_contents,
            enable_layer1=True,
            enable_layer2=True,
            enable_layer3=True,
            min_relevance="high",  # 高相关性
            llm_only=True,         # 完全 LLM 判断
        )
        
        return [
            item["content"]
            for item in result["results"]
            if item.get("relevance_score", 0) >= 0.8
        ]

# 使用示例
agent = ContentFilterAgent()
high_quality = agent.get_high_quality_contents(
    query="丽江旅游攻略",
    raw_contents=["内容1", "内容2", ...]
)
print(f"获取到 {len(high_quality)} 条高质量内容")
```

---

## 🎓 最佳实践

1. **分层使用**
   - 不确定内容质量 → 全开（Layer-1/2/3）
   - 已预清洗 → 只开 Layer-3
   - 只去垃圾 → 只开 Layer-1

2. **性能优先**
   - 批量处理 > 单条处理
   - 混合模式 > LLM Only（Layer-3）
   - 早停策略 > 全量处理

3. **质量优先**
   - LLM Only 模式（Layer-3）
   - 高相关性阈值（`min_relevance: "high"`）
   - 保存补充规则（`save_gap_rules: true`）

4. **成本控制**
   - 合理设置 `min_relevance`（避免过滤太多）
   - Layer-3 使用混合模式（减少 LLM 调用）
   - 先用 Layer-1/2 粗筛，再用 Layer-3 精筛

---

## 📞 技术支持

- 文档：`docs/QUICK_REFERENCE.md`
- API 文档：`http://localhost:8081/docs`（Swagger UI）
- 测试脚本：`scripts/test_three_layer_api.py`
