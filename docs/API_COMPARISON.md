# 三种过滤 API 对比

## 📊 快速对比表

| 特性 | 一站式 API | 两步式 API | 三层过滤 API |
|------|-----------|-----------|-------------|
| **端点** | `/api/filter/complete` | `/api/filter/auto` + `/api/sessions/{id}/results` | `/api/filter/three-layer` |
| **请求次数** | 1 次 ✅ | 2 次 | 1 次 ✅ |
| **输入内容** | 自动从 DB 读取 ✅ | 自动从 DB 读取 ✅ | 手动传入 |
| **返回数据** | 直接返回 post_data ✅ | 需二次查询 | 直接返回 post_data ✅ |
| **Session 管理** | 可选 | 自动保存 ✅ | 可选 |
| **适用场景** | 🌟 **日常查询（推荐）** | Session 管理 | 手动测试 |

---

## 🎯 使用场景推荐

### ✅ 推荐：一站式 API

**适用场景**：
- 一次性查询，立即使用结果
- 不需要保存 session
- 代码简洁优先

**代码**：
```python
response = requests.post("/api/filter/complete", json={"query": "丽江旅游"})
posts = response.json()["posts"]
```

**优势**：
- ✅ 1 次请求
- ✅ 直接返回数据
- ✅ 无需管理 session_id
- ✅ 代码最简洁

---

### ⚙️ 特殊场景：两步式 API

**适用场景**：
- 需要多次查询同一批数据（避免重复过滤）
- 需要查看 Layer-2 规则匹配详情
- 需要 Web 界面查看结果
- 需要持久化 Session（如分享链接）

**代码**：
```python
# Step 1: 过滤并保存 Session
resp1 = requests.post("/api/filter/auto", json={"query": "丽江旅游"})
session_id = resp1.json()["session_id"]

# Step 2: 多次查询同一 Session
resp2 = requests.get(f"/api/sessions/{session_id}/results?limit=10")
resp3 = requests.get(f"/api/sessions/{session_id}/results?limit=50")

# 或访问 Web 界面
web_url = resp1.json()["access"]["web_url"]
```

**优势**：
- ✅ Session 持久化
- ✅ 可重复查询（无需重新过滤）
- ✅ Web 界面可视化
- ✅ 可查看元数据（规则、场景）

---

### 🧪 测试场景：三层过滤 API

**适用场景**：
- 手动测试特定内容
- 不依赖数据库
- 快速验证规则

**代码**：
```python
response = requests.post(
    "/api/filter/three-layer",
    json={
        "query": "丽江旅游",
        "contents": [
            "丽江古城深度游攻略",
            "今天天气真好",
            "丽江美食推荐"
        ]
    }
)
```

**优势**：
- ✅ 不依赖数据库
- ✅ 快速测试
- ✅ 手动控制输入

---

## 📝 详细对比

### 1. 一站式 API

#### 端点
```
POST /api/filter/complete
```

#### 请求
```json
{
  "query": "丽江旅游攻略",
  "limit": 10
}
```

#### 响应
```json
{
  "query": "丽江旅游攻略",
  "session_id": "sess_xxx",
  "stats": {...},
  "posts": [
    {
      "id": "post_xxx",
      "title": "丽江古城攻略",
      "relevance_score": 0.92,
      "comments": [...]
    }
  ],
  "performance": {...}
}
```

#### 特点
- ✅ **1 次请求**直接返回 post_data
- ✅ 自动从 `filtered_posts` 读取 Layer-1 数据
- ✅ 自动执行 Layer-2 + Layer-3
- ✅ 自动读取评论
- ⚠️ 不保存 Session（响应中有 session_id 但不写入数据库）

---

### 2. 两步式 API

#### Step 1: 自动过滤
```
POST /api/filter/auto
```

**请求**：
```json
{
  "query": "丽江旅游攻略"
}
```

**响应**：
```json
{
  "session_id": "sess_xxx",
  "query": "丽江旅游攻略",
  "stats": {...},
  "performance": {...},
  "access": {
    "api_url": "http://localhost:8081/api/sessions/sess_xxx/results",
    "web_url": "http://localhost:8081/dashboard?session_id=sess_xxx"
  }
}
```

#### Step 2: 查询结果
```
GET /api/sessions/{session_id}/results
```

**参数**：
- `limit`: 返回数量（默认 50）
- `min_score`: 最低分数（可选）
- `include_comments`: 是否包含评论（默认 true）

**响应**：
```json
{
  "session_id": "sess_xxx",
  "query": "丽江旅游攻略",
  "total_results": 89,
  "returned_count": 50,
  "results": [
    {
      "post": {...},
      "comments": [...]
    }
  ]
}
```

#### 特点
- ✅ 保存 Session 到数据库（`session_metadata`, `session_l2_results`, `session_l3_results`）
- ✅ 可多次查询同一 Session（避免重复过滤）
- ✅ 提供 Web 界面访问
- ✅ 可查看元数据（场景、规则）
- ⚠️ 需要 2 次请求

---

### 3. 三层过滤 API

#### 端点
```
POST /api/filter/three-layer
```

#### 请求
```json
{
  "query": "丽江旅游攻略",
  "contents": [
    "丽江古城深度游攻略",
    "今天天气真好",
    "丽江美食推荐"
  ],
  "enable_layer1": false,
  "enable_layer2": true,
  "enable_layer3": true
}
```

#### 响应
```json
{
  "session_id": null,
  "query": "丽江旅游攻略",
  "stats": {...},
  "results": [
    {
      "index": 0,
      "content": "丽江古城深度游攻略",
      "layer2_pass": true,
      "layer3_relevance": "high",
      "layer3_score": 0.92
    }
  ],
  "performance": {...}
}
```

#### 特点
- ✅ 手动传入内容（不依赖数据库）
- ✅ 快速测试
- ✅ 可控制各层开关
- ⚠️ 不读取评论
- ⚠️ 不保存 Session

---

## 🔄 迁移示例

### 从两步式迁移到一站式

#### 场景1: 简单查询

**旧代码（两步式）**：
```python
# Step 1
resp1 = requests.post(
    "http://localhost:8081/api/filter/auto",
    json={"query": "丽江旅游攻略"}
)
session_id = resp1.json()["session_id"]

# Step 2
resp2 = requests.get(
    f"http://localhost:8081/api/sessions/{session_id}/results",
    params={"limit": 10}
)

posts = resp2.json()["results"]

for item in posts:
    print(item["post"]["title"])
```

**新代码（一站式）**：
```python
# 一步搞定
response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={
        "query": "丽江旅游攻略",
        "limit": 10
    }
)

posts = response.json()["posts"]

for post in posts:
    print(post["title"])
```

#### 场景2: 多次查询

**如果需要多次查询同一批数据，仍建议使用两步式**：

```python
# 过滤一次
resp1 = requests.post("/api/filter/auto", json={"query": "丽江旅游"})
session_id = resp1.json()["session_id"]

# 多次查询不同条件
top10 = requests.get(f"/api/sessions/{session_id}/results?limit=10").json()
high_score = requests.get(f"/api/sessions/{session_id}/results?min_score=0.8").json()
all_results = requests.get(f"/api/sessions/{session_id}/results?limit=1000").json()
```

---

## ⚡ 性能对比

### 测试场景
- Query: "丽江旅游攻略"
- Layer-1 数据: 500 条
- Layer-2 通过: 234 条
- Layer-3 通过: 89 条

### 结果

| 指标 | 一站式 | 两步式 | 三层过滤 |
|------|--------|--------|----------|
| 请求次数 | 1 | 2 | 1 |
| Layer-1 | 1.2s | 1.2s | - |
| Layer-2 | 15.6s | 15.6s | 15.6s |
| Layer-3 | 12.3s | 12.3s | 12.3s |
| 评论读取 | 0.5s | 0.5s | - |
| 网络延迟 | 0 | +50ms | 0 |
| **总耗时** | **29.6s** | **29.65s** | **27.9s** |

### 分析

- **一站式 vs 两步式**：几乎无差别（多一次请求仅增加 ~50ms）
- **一站式 vs 三层过滤**：一站式多 ~1.7s（因为读取 Layer-1 + 评论）
- **结论**：性能差异可忽略，选择基于**功能需求**而非性能

---

## 📋 选择指南

### 决策树

```
开始
  |
  ├── 需要多次查询同一批数据？
  |     ├── 是 → 使用 **两步式 API**
  |     └── 否 → 继续
  |
  ├── 需要 Web 界面查看？
  |     ├── 是 → 使用 **两步式 API**
  |     └── 否 → 继续
  |
  ├── 手动测试/不依赖数据库？
  |     ├── 是 → 使用 **三层过滤 API**
  |     └── 否 → 继续
  |
  └── 一次性查询，立即使用？
        └── 是 → 使用 **一站式 API** ✅
```

### 简化建议

**90% 场景**：使用 **一站式 API** 🌟

**特殊场景**：
- Session 管理 → 两步式
- 手动测试 → 三层过滤

---

## 🔧 实际案例

### 案例1: 数据分析脚本（推荐一站式）

```python
import requests

queries = ["丽江旅游", "杭州美食", "成都周边游"]

for query in queries:
    response = requests.post(
        "http://localhost:8081/api/filter/complete",
        json={"query": query, "limit": 50}
    )
    
    posts = response.json()["posts"]
    
    # 直接分析数据
    avg_likes = sum(p.get("metrics_likes", 0) for p in posts) / len(posts)
    print(f"{query}: {len(posts)} 条, 平均点赞 {avg_likes:.0f}")
```

### 案例2: 用户查询服务（推荐两步式）

```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route("/search", methods=["POST"])
def search():
    query = request.json["query"]
    
    # Step 1: 过滤并保存 Session
    resp = requests.post(
        "http://localhost:8081/api/filter/auto",
        json={"query": query}
    )
    
    session_id = resp.json()["session_id"]
    
    # 返回 session_id 和 Web 链接
    return jsonify({
        "session_id": session_id,
        "web_url": f"http://localhost:8081/dashboard?session_id={session_id}",
        "api_url": f"http://localhost:8081/api/sessions/{session_id}/results"
    })

@app.route("/results/<session_id>", methods=["GET"])
def get_results(session_id):
    # Step 2: 多次查询同一 Session
    limit = request.args.get("limit", 50)
    
    resp = requests.get(
        f"http://localhost:8081/api/sessions/{session_id}/results",
        params={"limit": limit}
    )
    
    return resp.json()
```

### 案例3: 规则测试（推荐三层过滤）

```python
import requests

# 测试规则对特定内容的效果
test_contents = [
    "丽江古城深度游攻略",
    "今天天气真好",
    "丽江美食推荐",
    "北京景点介绍"
]

response = requests.post(
    "http://localhost:8081/api/filter/three-layer",
    json={
        "query": "丽江旅游攻略",
        "contents": test_contents,
        "enable_layer2": True,
        "enable_layer3": True
    }
)

results = response.json()["results"]

print("Layer-2 规则测试:")
for r in results:
    status = "✅ 通过" if r["layer2_pass"] else "❌ 不通过"
    print(f"{status} | {r['content'][:30]}")

print("\nLayer-3 相关性测试:")
for r in results:
    if r["layer2_pass"]:
        print(f"{r['layer3_score']:.3f} ({r['layer3_relevance']}) | {r['content'][:30]}")
```

---

## 📚 相关文档

- [COMPLETE_FILTER_API_GUIDE.md](COMPLETE_FILTER_API_GUIDE.md) - 一站式 API 详细指南
- [AUTO_FILTER_API_GUIDE.md](AUTO_FILTER_API_GUIDE.md) - 两步式 API 详细指南
- [SESSION_API_GUIDE.md](SESSION_API_GUIDE.md) - Session 管理详细指南
- [FILTER_WORKFLOW.md](FILTER_WORKFLOW.md) - 三层过滤原理

---

## 🎯 总结

| API | 推荐度 | 适用场景 |
|-----|--------|----------|
| **一站式** | ⭐⭐⭐⭐⭐ | 日常查询（推荐） |
| **两步式** | ⭐⭐⭐⭐ | Session 管理、Web 界面 |
| **三层过滤** | ⭐⭐⭐ | 手动测试、快速验证 |

**90% 场景推荐使用一站式 API！** 🚀
