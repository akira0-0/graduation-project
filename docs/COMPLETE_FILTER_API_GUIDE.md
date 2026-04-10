# 一站式过滤 API 使用指南

## 📌 概述

**一站式过滤 API** 是将 **Auto Filter** 和 **Session API** 整合后的终极方案：

- **输入**：只需一个 `query`
- **输出**：直接返回可用的 `post_data`（帖子 + 评论）
- **特点**：一次请求搞定，无需手动管理 session_id

---

## 🆚 三种方案对比

| 方案 | 接口数量 | 输入 | 输出 | 适用场景 |
|------|---------|------|------|----------|
| **方案1: 一站式** | **1 个** | query | **post_data 直接返回** | ✅ **推荐：最简单** |
| 方案2: 两步式 | 2 个 | query → session_id | 需二次查询 | Session 管理场景 |
| 方案3: 三层过滤 | 1 个 | query + contents | post_data 返回 | 手动传入内容 |

### 代码对比

#### ✅ 方案1: 一站式（推荐）

```python
# 一个请求搞定
response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={"query": "丽江旅游攻略"}
)

result = response.json()

# 直接使用数据
for post in result["posts"]:
    print(f"标题: {post['title']}")
    print(f"相关性: {post['relevance_score']:.2f}")
    print(f"评论数: {len(post['comments'])}")
```

#### ❌ 方案2: 两步式（旧方式）

```python
# Step 1: 获取 session_id
resp1 = requests.post(
    "http://localhost:8081/api/filter/auto",
    json={"query": "丽江旅游攻略"}
)
session_id = resp1.json()["session_id"]

# Step 2: 用 session_id 查询数据
resp2 = requests.get(
    f"http://localhost:8081/api/sessions/{session_id}/results"
)
result = resp2.json()

# 使用数据
for post in result["results"]:
    print(post['title'])
```

---

## 🚀 快速开始

### 1. 启动 API 服务

```bash
uv run python filter_engine/api.py
```

### 2. 发送请求

```python
import requests

response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={
        "query": "丽江旅游攻略",
        "limit": 10
    }
)

result = response.json()
print(f"找到 {len(result['posts'])} 条相关帖子")
```

### 3. 使用数据

```python
for post in result["posts"]:
    print(f"\n标题: {post['title']}")
    print(f"相关性: {post['relevance_score']:.3f} ({post['relevance_level']})")
    print(f"点赞: {post['metrics_likes']}")
    print(f"评论数: {len(post['comments'])}")
    
    # 查看评论
    for comment in post["comments"][:3]:
        print(f"  - {comment['author_nickname']}: {comment['content'][:50]}...")
```

---

## 📖 API 详细说明

### 端点

```
POST /api/filter/complete
```

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 用户查询，如"丽江旅游攻略" |
| `platform` | string | ❌ | `null` | 平台过滤（`xhs`/`weibo`），不填则全平台 |
| `max_posts` | int | ❌ | `500` | Layer-1 最多读取帖子数（10-2000） |
| `force_scenario` | string | ❌ | `null` | 强制指定场景（如"travel"） |
| `min_relevance` | string | ❌ | `"medium"` | 最低相关性（`high`/`medium`/`low`） |
| `llm_only` | bool | ❌ | `true` | Layer-3 完全依赖 LLM |
| `limit` | int | ❌ | `50` | 返回结果数量（1-500） |
| `min_score` | float | ❌ | `null` | 最低相关性分数过滤（0.0-1.0） |
| `include_comments` | bool | ❌ | `true` | 是否包含评论 |

### 响应格式

```json
{
  "query": "丽江旅游攻略",
  "session_id": "sess_20250109_123045_a1b2c3d4",
  
  "stats": {
    "l1_total_posts": 500,
    "l2_passed_posts": 234,
    "l3_passed_posts": 89,
    "final_returned": 50
  },
  
  "posts": [
    {
      "id": "post_xxx",
      "title": "丽江古城深度游攻略",
      "content": "...",
      "platform": "xhs",
      
      "relevance_score": 0.92,
      "relevance_level": "high",
      
      "metrics_likes": 1523,
      "metrics_collects": 456,
      "metrics_comments_count": 78,
      
      "author_nickname": "旅行达人",
      "publish_time": "2024-12-15T10:30:00Z",
      
      "tags": ["丽江", "旅游", "攻略"],
      
      "comments": [
        {
          "id": "comment_xxx",
          "content": "很实用！",
          "author_nickname": "用户A",
          "publish_time": "2024-12-15T11:00:00Z"
        }
      ]
    }
  ],
  
  "performance": {
    "layer1": 1.2,
    "layer2": 15.6,
    "layer3": 12.3,
    "fetch_results": 0.5,
    "total": 29.6
  },
  
  "metadata": {
    "scenario": "travel",
    "min_relevance": "medium",
    "platform": "xhs"
  }
}
```

---

## 💡 使用示例

### 示例1: 基础查询

```python
import requests

response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={"query": "丽江旅游攻略"}
)

result = response.json()
print(f"Query: {result['query']}")
print(f"返回: {len(result['posts'])} 条")
```

### 示例2: 高质量内容过滤

```python
response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={
        "query": "丽江旅游攻略",
        "min_relevance": "high",     # 只要高相关性
        "min_score": 0.8,            # 分数 >= 0.8
        "limit": 20,                 # 返回 Top 20
        "platform": "xhs"            # 只看小红书
    }
)

for post in response.json()["posts"]:
    print(f"{post['relevance_score']:.3f} | {post['title']}")
```

### 示例3: 快速浏览（不含评论）

```python
# 不需要评论时，设置 include_comments=False 可加快速度
response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={
        "query": "成都美食推荐",
        "include_comments": False,  # 跳过评论
        "limit": 30
    }
)

posts = response.json()["posts"]
print(f"找到 {len(posts)} 条帖子（不含评论）")
```

### 示例4: 批量查询

```python
queries = ["丽江旅游", "杭州美食", "成都周边游"]

for query in queries:
    response = requests.post(
        "http://localhost:8081/api/filter/complete",
        json={"query": query, "limit": 5}
    )
    
    result = response.json()
    stats = result['stats']
    
    print(f"\nQuery: {query}")
    print(f"  L1→L2→L3: {stats['l1_total_posts']} → {stats['l2_passed_posts']} → {stats['l3_passed_posts']}")
    print(f"  返回: {len(result['posts'])} 条")
    print(f"  耗时: {result['performance']['total']:.2f}s")
```

### 示例5: 处理结果数据

```python
response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={"query": "丽江旅游攻略", "limit": 10}
)

result = response.json()

# 按相关性分组
high_rel = [p for p in result['posts'] if p['relevance_level'] == 'high']
medium_rel = [p for p in result['posts'] if p['relevance_level'] == 'medium']

print(f"高相关性: {len(high_rel)} 条")
print(f"中相关性: {len(medium_rel)} 条")

# 按点赞数排序
sorted_by_likes = sorted(
    result['posts'],
    key=lambda x: x.get('metrics_likes', 0),
    reverse=True
)

print("\nTop 5 热门帖子:")
for i, post in enumerate(sorted_by_likes[:5], 1):
    print(f"{i}. {post['title']} ({post['metrics_likes']} 赞)")

# 提取所有评论
all_comments = []
for post in result['posts']:
    all_comments.extend(post.get('comments', []))

print(f"\n总评论数: {len(all_comments)}")
```

### 示例6: 保存到文件

```python
import json

response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={"query": "丽江旅游攻略", "limit": 50}
)

result = response.json()

# 保存完整数据
with open("result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

# 保存为 CSV（简化版）
import csv

with open("result.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["标题", "相关性", "点赞", "评论数", "链接"])
    
    for post in result['posts']:
        writer.writerow([
            post.get('title', ''),
            post['relevance_score'],
            post.get('metrics_likes', 0),
            len(post.get('comments', [])),
            post.get('note_url', '')
        ])

print("✅ 数据已保存")
```

---

## 🔧 高级配置

### 场景强制指定

如果自动检测场景不准确，可以强制指定：

```python
response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={
        "query": "丽江",
        "force_scenario": "travel"  # 强制使用旅游场景规则
    }
)
```

### 相关性等级说明

| 等级 | 分数范围 | 说明 | 适用场景 |
|------|---------|------|----------|
| `high` | 0.8-1.0 | 高度相关 | 精准查询 |
| `medium` | 0.5-0.79 | 中度相关 | 常规查询（推荐） |
| `low` | 0.3-0.49 | 低度相关 | 扩展查询 |

```python
# 高精度查询
response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={
        "query": "丽江旅游攻略",
        "min_relevance": "high",
        "min_score": 0.85
    }
)

# 宽松查询
response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={
        "query": "丽江",
        "min_relevance": "low",
        "limit": 100
    }
)
```

### 性能优化

```python
# 快速模式（少量数据 + 无评论）
response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={
        "query": "丽江旅游",
        "max_posts": 200,          # 减少 Layer-1 数据量
        "include_comments": False, # 跳过评论
        "limit": 10                # 少量结果
    }
)

# 完整模式（大量数据 + 评论）
response = requests.post(
    "http://localhost:8081/api/filter/complete",
    json={
        "query": "丽江旅游",
        "max_posts": 2000,         # 最大数据量
        "include_comments": True,  # 包含评论
        "limit": 100               # 大量结果
    }
)
```

---

## 🧪 测试脚本

### 运行测试

```bash
# 基础测试
uv run python scripts/test_complete_filter_api.py

# 多查询测试
uv run python scripts/test_complete_filter_api.py multi

# 过滤参数测试
uv run python scripts/test_complete_filter_api.py filter

# 对比测试（一站式 vs 两步式）
uv run python scripts/test_complete_filter_api.py compare
```

### 测试输出

```
================================================================================
🎯 测试一站式过滤 API（Query → Post Data）
================================================================================

📤 请求数据:
{
  "query": "丽江旅游攻略",
  "platform": "xhs",
  "max_posts": 500,
  "min_relevance": "medium",
  "limit": 10
}

⏳ 发送请求...

================================================================================
📊 统计信息
================================================================================
Query: 丽江旅游攻略
Session ID: sess_20250109_123045_a1b2c3d4
场景: travel

过滤流程:
  L1 总数: 500
  L2 通过: 234 (46.8%)
  L3 通过: 89 (17.8%)
  最终返回: 10 条

性能:
  Layer-1 读取: 1.23s
  Layer-2 规则: 15.67s
  Layer-3 LLM: 12.45s
  评论读取: 0.56s
  总耗时: 29.91s

================================================================================
📝 帖子数据（共 10 条）
================================================================================

1. 丽江古城深度游攻略
   ID: post_xxx
   平台: xhs
   相关性: 0.920 (high)
   点赞: 1523
   评论数: 45
   内容: 这次丽江之行收获满满，给大家分享下我的行程安排...
   评论示例:
     1) 旅行爱好者: 太实用了，已收藏！
     2) 张三: 请问住宿推荐哪里？

2. 丽江自由行完整攻略
   ...

✅ 测试完成！
💾 完整结果已保存到: complete_filter_result.json
```

---

## 🆘 错误处理

### 常见错误

#### 1. 没有数据

```json
{
  "detail": "No posts found. Please run Layer-1 filter first: uv run python scripts/batch_filter.py"
}
```

**解决方法**：先运行 Layer-1 批量过滤，导入数据到 `filtered_posts` 表

```bash
uv run python scripts/batch_filter.py
```

#### 2. Layer-2 无结果

如果 Layer-2 过滤后没有数据，API 会提前返回：

```json
{
  "stats": {
    "l1_total_posts": 500,
    "l2_passed_posts": 0,
    "l3_passed_posts": 0,
    "final_returned": 0
  },
  "posts": [],
  "metadata": {
    "early_stop": "layer2",
    "scenario": "travel"
  }
}
```

**可能原因**：
- 查询词与场景规则不匹配
- 场景检测错误

**解决方法**：
- 调整查询词
- 使用 `force_scenario` 强制指定场景

#### 3. Layer-3 无结果

如果 Layer-3 过滤后没有数据：

```json
{
  "stats": {
    "l1_total_posts": 500,
    "l2_passed_posts": 234,
    "l3_passed_posts": 0,
    "final_returned": 0
  },
  "posts": []
}
```

**解决方法**：
- 降低 `min_relevance`（`high` → `medium` → `low`）
- 移除 `min_score` 限制
- 检查 LLM 服务是否正常

---

## 📊 性能分析

### 各层耗时占比

典型场景（500 条数据）：

| 阶段 | 耗时 | 占比 |
|------|------|------|
| Layer-1 读取 | 1-2s | 5% |
| Layer-2 规则 | 15-20s | 50% |
| Layer-3 LLM | 10-15s | 40% |
| 评论读取 | 0.5-1s | 5% |
| **总计** | **~30s** | **100%** |

### 优化建议

1. **减少 Layer-1 数据量**
   ```python
   "max_posts": 200  # 默认 500
   ```

2. **跳过评论**
   ```python
   "include_comments": False  # 节省 0.5-1s
   ```

3. **减少返回数量**
   ```python
   "limit": 10  # 默认 50
   ```

4. **提高过滤阈值**
   ```python
   "min_relevance": "high",
   "min_score": 0.8
   ```

---

## 🔄 迁移指南

### 从两步式迁移到一站式

**旧代码（两步式）**：

```python
# Step 1
resp1 = requests.post("/api/filter/auto", json={"query": query})
session_id = resp1.json()["session_id"]

# Step 2
resp2 = requests.get(f"/api/sessions/{session_id}/results")
posts = resp2.json()["results"]
```

**新代码（一站式）**：

```python
# 一步搞定
response = requests.post("/api/filter/complete", json={"query": query})
posts = response.json()["posts"]
```

### 字段映射

| 两步式 | 一站式 |
|--------|--------|
| `results` | `posts` |
| `total_results` | `stats.final_returned` |
| N/A（需二次查询） | 直接返回 |

---

## 💡 最佳实践

### 1. 根据场景选择接口

```python
# ✅ 推荐：一次性查询
use_case = "快速获取结果"
endpoint = "/api/filter/complete"

# ⚠️ 特殊场景：需要管理 Session
use_case = "多次查询同一批数据"
endpoint = "/api/filter/auto" + "/api/sessions/{id}/results"
```

### 2. 合理设置参数

```python
# 日常查询
config = {
    "min_relevance": "medium",
    "limit": 50,
    "include_comments": True
}

# 快速预览
config = {
    "max_posts": 200,
    "limit": 10,
    "include_comments": False
}

# 深度分析
config = {
    "max_posts": 2000,
    "min_relevance": "low",
    "limit": 200,
    "include_comments": True
}
```

### 3. 错误处理

```python
try:
    response = requests.post(
        "http://localhost:8081/api/filter/complete",
        json={"query": query},
        timeout=300  # 设置超时
    )
    response.raise_for_status()
    
    result = response.json()
    
    if not result["posts"]:
        print("未找到相关结果，尝试调整 min_relevance")
    else:
        process_posts(result["posts"])
        
except requests.exceptions.Timeout:
    print("请求超时，尝试减少 max_posts")
except requests.exceptions.HTTPError as e:
    print(f"API 错误: {e.response.status_code}")
except Exception as e:
    print(f"未知错误: {e}")
```

---

## 📚 相关文档

- [AUTO_FILTER_API_GUIDE.md](AUTO_FILTER_API_GUIDE.md) - 两步式过滤 API
- [SESSION_API_GUIDE.md](SESSION_API_GUIDE.md) - Session 管理 API
- [FILTER_WORKFLOW.md](FILTER_WORKFLOW.md) - 三层过滤原理

---

## ❓ FAQ

### Q1: 什么时候用一站式，什么时候用两步式？

**一站式（推荐）**：
- ✅ 一次性查询，立即使用结果
- ✅ 不需要保存 session_id
- ✅ 代码简洁

**两步式**：
- ✅ 需要多次查询同一批数据（避免重复过滤）
- ✅ 需要查看过滤元数据（如 Layer-2 规则）
- ✅ 需要 Web 界面查看结果

### Q2: 一站式接口会保存 Session 吗？

不会自动保存到 Session 表，但响应中会返回 `session_id`，可以手动保存。

### Q3: 如何获取更多结果？

调整 `limit` 和 `min_relevance`：

```python
{
    "query": "丽江旅游",
    "min_relevance": "low",  # 降低阈值
    "limit": 200             # 增加数量
}
```

### Q4: 为什么有时返回 0 条结果？

可能原因：
1. Layer-2 规则过严（尝试 `force_scenario`）
2. Layer-3 阈值过高（降低 `min_relevance`）
3. 数据库无相关数据（检查 `filtered_posts` 表）

### Q5: 如何提高性能？

```python
# 性能优化配置
{
    "max_posts": 200,          # 减少数据量
    "include_comments": False, # 跳过评论
    "limit": 10,               # 少量结果
    "min_relevance": "high"    # 提高阈值（减少 LLM 调用）
}
```

---

## 🎯 总结

一站式过滤 API 是最简单、最高效的方式：

- **输入**: `query`
- **输出**: `post_data`
- **优势**: 一次请求、直接返回、无需管理 session_id

推荐在绝大多数场景下使用！🚀
