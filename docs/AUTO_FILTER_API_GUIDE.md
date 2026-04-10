# 端到端自动过滤 API 使用指南

## 🎯 核心优势

**一句话总结**：只需输入 `query`，自动从数据库读取数据并完成三层过滤，无需手动传入 `contents`。

---

## 🚀 快速开始

### 最简请求

```bash
curl -X POST "http://localhost:8081/api/filter/auto" \
  -H "Content-Type: application/json" \
  -d '{"query": "丽江旅游攻略"}'
```

**就这么简单！** API 会自动：
1. 从 `filtered_posts` 表读取 Layer-1 已过滤数据
2. 执行 Layer-2 场景规则过滤
3. 执行 Layer-3 语义相关性过滤
4. 保存结果到 Session 临时表
5. 返回 API 访问地址

---

## 📝 完整示例

### Python 调用

```python
import requests

# Step 1: 启动过滤任务（只需输入 query）
response = requests.post(
    "http://localhost:8081/api/filter/auto",
    json={
        "query": "丽江旅游攻略",
        "platform": "xhs",      # 可选：只处理小红书
        "max_posts": 500,       # 可选：最多处理 500 条
    }
)

result = response.json()
session_id = result["session_id"]

print(f"✅ 过滤完成")
print(f"  Session ID: {session_id}")
print(f"  L3 通过: {result['stats']['l3_passed_posts']} 条")
print(f"  API 访问: {result['access']['web_url']}")

# Step 2: 获取过滤结果
results = requests.get(
    f"http://localhost:8081/api/sessions/{session_id}/results?limit=50"
).json()

for item in results["results"]:
    post = item["post"]
    print(f"- {post['title']} (相关性: {post['relevance_score']:.2f})")
```

---

## 📚 API 参考

### 请求地址

```
POST /api/filter/auto
```

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| **基础参数** | | | | |
| `query` | string | ✅ | - | 用户查询，如"丽江旅游攻略" |
| **数据源控制** | | | | |
| `platform` | string | ❌ | `null` | 平台过滤（xhs/weibo），不填则全平台 |
| `max_posts` | integer | ❌ | `500` | 最多处理帖子数（10-2000） |
| `max_comments_per_post` | integer | ❌ | `50` | 每个帖子最多处理评论数（0-200） |
| **Layer-2 控制** | | | | |
| `force_scenario` | string | ❌ | `null` | 强制指定场景（normal/ecommerce/news...） |
| `save_gap_rules` | boolean | ❌ | `false` | 是否保存 LLM 生成的补充规则 |
| **Layer-3 控制** | | | | |
| `min_relevance` | string | ❌ | `"medium"` | 最低相关性（high/medium/low） |
| `llm_only` | boolean | ❌ | `true` | Layer-3 是否完全依赖 LLM |
| **Session 控制** | | | | |
| `session_id` | string | ❌ | 自动生成 | 指定 Session ID（可选） |
| `auto_save` | boolean | ❌ | `true` | 自动保存到 session 临时表 |

### 响应格式

```json
{
  "session_id": "sess_20260410_123456_abcd",
  "query": "丽江旅游攻略",
  "stats": {
    "l1_total_posts": 500,
    "l1_total_comments": 1234,
    "l2_passed_posts": 234,
    "l2_passed_comments": 567,
    "l3_passed_posts": 89
  },
  "performance": {
    "layer1": 1.2,
    "layer2": 15.6,
    "layer3": 12.3,
    "total": 29.1
  },
  "access": {
    "api_url": "/api/sessions/sess_xxx/results",
    "web_url": "http://localhost:8081/api/sessions/sess_xxx/results",
    "metadata_url": "/api/sessions/sess_xxx/metadata"
  },
  "metadata": {
    "scenario": "social",
    "min_relevance": "medium",
    "platform": "xhs"
  }
}
```

---

## 🎯 使用场景

### 场景 1: 最简使用（推荐）

```python
# 只需输入 query，其他都是默认值
response = requests.post(
    "http://localhost:8081/api/filter/auto",
    json={"query": "丽江旅游攻略"}
)
```

**适用于**：快速过滤，不需要特殊配置

---

### 场景 2: 指定平台

```python
# 只处理小红书数据
response = requests.post(
    "http://localhost:8081/api/filter/auto",
    json={
        "query": "丽江旅游攻略",
        "platform": "xhs"
    }
)
```

**适用于**：单平台数据分析

---

### 场景 3: 大批量处理

```python
# 处理更多数据
response = requests.post(
    "http://localhost:8081/api/filter/auto",
    json={
        "query": "电商好评返现",
        "max_posts": 2000,           # 处理 2000 条帖子
        "max_comments_per_post": 100 # 每帖 100 条评论
    }
)
```

**适用于**：全量数据分析

---

### 场景 4: 高质量过滤

```python
# 高相关性要求
response = requests.post(
    "http://localhost:8081/api/filter/auto",
    json={
        "query": "深度旅游攻略",
        "min_relevance": "high",  # 高相关性
        "llm_only": True,         # 完全 LLM 判断
    }
)
```

**适用于**：需要高质量内容

---

### 场景 5: 指定场景

```python
# 强制使用电商场景规则
response = requests.post(
    "http://localhost:8081/api/filter/auto",
    json={
        "query": "好评返现",
        "force_scenario": "ecommerce",
        "save_gap_rules": True  # 保存 LLM 生成的规则
    }
)
```

**适用于**：明确场景，需要保存规则

---

## 🔄 完整工作流

### 流程图

```
用户输入 query
    ↓
API 自动从 filtered_posts 读取 Layer-1 数据
    ↓
Layer-2: 场景规则过滤（LLM 分析 + 规则匹配）
    ↓
写入 session_l2_posts
    ↓
从 filtered_comments 读取有效帖子的评论
    ↓
Layer-2: 评论过滤（复用规则）
    ↓
写入 session_l2_comments
    ↓
Layer-3: LLM 语义相关性过滤
    ↓
写入 session_l3_results（帖子 + 评论嵌套）
    ↓
更新 session_metadata
    ↓
返回 Session ID 和 API 访问地址
```

### 数据表关系

```
filtered_posts (Layer-1 输出)
    ↓ 读取
session_l2_posts (Layer-2 输出)
    ↓ 关联
filtered_comments (Layer-1 评论)
    ↓ 过滤
session_l2_comments (Layer-2 评论)
    ↓ 组合
session_l3_results (Layer-3 最终结果)
    ↓ 记录
session_metadata (元数据)
```

---

## 📊 与手动传入 contents 对比

| 特性 | `/api/filter/auto` | `/api/filter/three-layer` |
|------|-------------------|--------------------------|
| **输入** | 只需 `query` | 需要 `query` + `contents` |
| **数据源** | 自动从数据库读取 | 手动传入数组 |
| **数据量** | 支持大批量（2000+） | 限制 1000 条 |
| **Session 保存** | ✅ 自动保存 | ❌ 不保存 |
| **评论关联** | ✅ 自动关联 | ❌ 需手动处理 |
| **适用场景** | **生产环境** | 测试/小批量 |

**推荐**：生产环境使用 `/api/filter/auto`

---

## ⚡ 性能优化

### 1. 控制数据量

```python
# 小批量快速测试
{"query": "...", "max_posts": 100}

# 中等批量
{"query": "...", "max_posts": 500}  # 默认

# 大批量分析
{"query": "...", "max_posts": 2000}
```

### 2. 平台过滤

```python
# 只处理小红书（减少数据量）
{"query": "...", "platform": "xhs"}
```

### 3. 调整相关性

```python
# 宽松（通过更多）
{"query": "...", "min_relevance": "low"}

# 严格（通过更少，更快）
{"query": "...", "min_relevance": "high"}
```

---

## 🔍 结果查询

### 方式 1: 通过返回的 API URL

```python
# Step 1: 启动过滤
response = requests.post("/api/filter/auto", json={"query": "..."})
api_url = response.json()["access"]["web_url"]

# Step 2: 获取结果
results = requests.get(api_url).json()
```

### 方式 2: 通过 Session ID

```python
session_id = response.json()["session_id"]

# 获取结果（支持分页、过滤）
results = requests.get(
    f"/api/sessions/{session_id}/results",
    params={
        "limit": 50,
        "offset": 0,
        "min_score": 0.7  # 只要高分结果
    }
).json()

# 获取元数据
metadata = requests.get(
    f"/api/sessions/{session_id}/metadata"
).json()
```

---

## 🐛 常见问题

### Q1: 返回 404 错误？

**A**: 数据库中没有 Layer-1 过滤后的数据。

**解决方案**：
```bash
# 先运行 Layer-1 过滤
uv run python scripts/batch_filter.py --data-type posts --platform xhs
```

### Q2: 过滤结果为 0？

**A**: 可能原因：
1. Query 与数据库内容不匹配
2. Layer-2/3 规则太严格

**解决方案**：
```python
# 降低相关性要求
{"query": "...", "min_relevance": "low"}

# 检查元数据
metadata = requests.get(f"/api/sessions/{session_id}/metadata").json()
print(metadata)
```

### Q3: 耗时太长？

**A**: 优化建议：
```python
# 减少数据量
{"query": "...", "max_posts": 200}

# 使用混合模式（减少 LLM 调用）
{"query": "...", "llm_only": False}

# 只处理单平台
{"query": "...", "platform": "xhs"}
```

---

## 🎓 最佳实践

### 1. 生产环境推荐配置

```python
response = requests.post("/api/filter/auto", json={
    "query": "用户输入的查询",
    "platform": "xhs",           # 明确平台
    "max_posts": 500,            # 适中数量
    "min_relevance": "medium",   # 平衡质量和数量
    "llm_only": True,            # 高质量
    "auto_save": True,           # 保存结果
})
```

### 2. 快速测试配置

```python
response = requests.post("/api/filter/auto", json={
    "query": "测试查询",
    "max_posts": 50,             # 小批量
    "llm_only": False,           # 快速模式
})
```

### 3. 高质量内容配置

```python
response = requests.post("/api/filter/auto", json={
    "query": "深度分析需求",
    "min_relevance": "high",     # 高相关性
    "llm_only": True,            # 完全 LLM
    "save_gap_rules": True,      # 保存新规则
})
```

---

## 📞 技术支持

- **API 文档**: http://localhost:8081/docs
- **测试脚本**: `scripts/test_auto_filter_api.py`
- **相关文档**: 
  - `docs/SESSION_API_GUIDE.md` - Session 数据访问
  - `docs/THREE_LAYER_API_GUIDE.md` - 三层过滤详解

---

## 🔄 迁移指南

### 从脚本迁移到 API

**旧方式**（脚本）:
```bash
# 需要运行多个脚本
uv run python scripts/batch_scene_filter_smart.py --query "丽江旅游"
uv run python scripts/batch_llm_filter.py --session-id sess_xxx --query "丽江旅游"
```

**新方式**（API）:
```python
# 一个请求搞定
response = requests.post("/api/filter/auto", json={"query": "丽江旅游"})
```

**优势**：
- ✅ 无需手动管理 Session ID
- ✅ 无需多次调用
- ✅ 自动保存结果
- ✅ 跨网络访问

---

**文档更新时间**：2026年4月10日  
**API 版本**：v2.1.0
