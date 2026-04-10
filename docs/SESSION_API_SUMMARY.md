# Session API 实现总结

## ✅ 已完成的工作

### 1. 新增 API 接口（`filter_engine/api.py`）

#### 📡 核心接口

| 端点 | 方法 | 功能 | 说明 |
|------|------|------|------|
| `/api/sessions/{session_id}/results` | GET | 获取 Layer-3 最终过滤结果 | **最重要**，Agent 使用 |
| `/api/sessions/{session_id}/metadata` | GET | 获取 Session 元数据 | 查看统计信息 |
| `/api/sessions` | GET | 列出所有 Session | 查看历史任务 |
| `/api/sessions/{session_id}` | DELETE | 删除 Session | 清理旧数据 |

#### 🔧 关键参数

**`GET /api/sessions/{session_id}/results`**
- `limit`: 返回数量（1-1000，默认100）
- `offset`: 分页偏移（默认0）
- `min_score`: 最低相关性分数（0.0-1.0）

**示例**:
```bash
curl "http://localhost:8081/api/sessions/sess_abc/results?limit=50&min_score=0.7"
```

---

### 2. 数据模型（Pydantic）

```python
class SessionPostData(BaseModel):
    post_id: str
    title: Optional[str]
    content: str
    relevance_score: Optional[float]  # Layer-3 相关性分数
    relevance_level: Optional[str]     # high/medium/low
    platform: str
    author_nickname: Optional[str]
    metrics_likes: int
    ...

class SessionResult(BaseModel):
    post: SessionPostData
    comments: List[dict]
    comment_count: int

class SessionResponse(BaseModel):
    session_id: str
    query_text: str
    total_results: int
    results: List[SessionResult]
    metadata: SessionMetadata
```

---

### 3. 文档

#### 📄 已创建的文档

1. **`docs/SESSION_API_GUIDE.md`** - 完整使用指南
   - 快速开始
   - 核心接口说明
   - Python/JavaScript 调用示例
   - 跨局域网部署方案
   - 安全配置建议
   - 常见问题解答

2. **`scripts/test_session_api.py`** - API 测试脚本
   - 自动测试所有接口
   - 验证数据格式
   - 生成调用示例

---

## 🚀 使用流程

### 数据过滤端（你）

```bash
# 1. 运行过滤任务
uv run python scripts/batch_scene_filter_smart.py \
  --query "保留关于丽江旅游、景点、美食的真实体验分享"

# 输出: Session ID: sess_20260410_143022_a1b2

# 2. 启动 API 服务
uv run uvicorn filter_engine.api:app --host 0.0.0.0 --port 8081

# 3. 告诉同学
# "Session ID 是 sess_20260410_143022_a1b2"
# "API 地址是 http://你的IP:8081"
```

---

### Agent 端（同学）

```python
import requests

# 配置
API_URL = "http://your-server:8081"
SESSION_ID = "sess_20260410_143022_a1b2"

# 获取数据
response = requests.get(
    f"{API_URL}/api/sessions/{SESSION_ID}/results",
    params={"min_score": 0.7, "limit": 100}
)

data = response.json()

# 使用数据
for item in data["results"]:
    post = item["post"]
    print(f"标题: {post['title']}")
    print(f"内容: {post['content'][:100]}...")
    print(f"相关性: {post['relevance_score']}")
```

---

## 🌐 跨局域网访问方案

### 方案对比

| 方案 | 复杂度 | 成本 | 稳定性 | 适用场景 |
|------|--------|------|--------|----------|
| **ngrok**（临时隧道） | ⭐ | 免费 | ⭐⭐ | 快速测试 |
| **Railway**（云服务） | ⭐⭐ | 免费额度 | ⭐⭐⭐⭐ | 长期使用 |
| **Render**（云服务） | ⭐⭐ | 免费层 | ⭐⭐⭐⭐ | 生产环境 |
| **本机公网IP**（端口映射） | ⭐⭐⭐ | 免费 | ⭐⭐⭐ | 有公网IP |

### 推荐：ngrok（最简单）

```bash
# 1. 下载 ngrok: https://ngrok.com/download
# 2. 启动 API 服务
uv run uvicorn filter_engine.api:app --host 0.0.0.0 --port 8081

# 3. 启动 ngrok
ngrok http 8081

# 输出:
# Forwarding https://abc123.ngrok.io -> http://localhost:8081
```

然后告诉同学访问：`https://abc123.ngrok.io/api/sessions/...`

---

## 🔐 安全建议

### 1. 添加 API Key 认证

```python
# filter_engine/api.py
from fastapi import Header, Depends, HTTPException

API_KEY = "your-secret-key-here"  # 改为环境变量

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.get("/api/sessions/{session_id}/results", dependencies=[Depends(verify_api_key)])
async def get_session_results(...):
    ...
```

调用时：
```python
headers = {"X-API-Key": "your-secret-key-here"}
response = requests.get(url, headers=headers)
```

---

### 2. 配置 CORS（跨域）

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改为具体域名
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📊 返回数据格式

### 完整示例

```json
{
  "session_id": "sess_20260410_143022_a1b2",
  "query_text": "丽江旅游景点推荐",
  "total_results": 45,
  "results": [
    {
      "post": {
        "post_id": "6a7b8c9d",
        "title": "丽江古城深度游攻略",
        "content": "丽江古城是一个非常值得一去的地方...",
        "platform": "xhs",
        "author_nickname": "旅行达人",
        "publish_time": "2026-04-01T10:30:00",
        "relevance_score": 0.92,
        "relevance_level": "high",
        "metrics_likes": 1523,
        "metrics_comments": 87,
        "url": "https://...",
        "tags": ["旅游", "丽江", "攻略"]
      },
      "comments": [
        {
          "id": "comment1",
          "content": "写得很详细，已收藏！",
          "author_nickname": "用户A",
          "metrics_likes": 15,
          "publish_time": "2026-04-01T11:00:00"
        }
      ],
      "comment_count": 15
    }
  ],
  "metadata": {
    "session_id": "sess_20260410_143022_a1b2",
    "query_text": "丽江旅游景点推荐",
    "l1_total_posts": 1000,
    "l2_passed_posts": 180,
    "l3_passed_posts": 45,
    "status": "completed",
    "created_at": "2026-04-10T14:30:00Z"
  }
}
```

---

## ✅ 与直接访问 Supabase 的对比

| 维度 | 直接访问 Supabase | 通过 API 封装 |
|------|-------------------|---------------|
| **安全性** | ❌ 暴露凭证 | ✅ 隐藏凭证 |
| **易用性** | ⚠️ 需学习 Supabase 语法 | ✅ 标准 REST API |
| **数据格式** | ⚠️ 嵌套 JSON 需解析 | ✅ 扁平化、标准化 |
| **文档** | ⚠️ 需查 Supabase 文档 | ✅ Swagger 自动文档 |
| **错误处理** | ❌ 原始错误 | ✅ 友好的错误消息 |
| **扩展性** | ❌ 难以添加功能 | ✅ 易于添加缓存、日志 |
| **跨域支持** | ⚠️ 需配置 Supabase | ✅ CORS 易配置 |

**结论**：封装 API 方案更优！✅

---

## 🧪 测试

### 运行测试脚本

```bash
# 确保 API 服务已启动
uv run uvicorn filter_engine.api:app --host 0.0.0.0 --port 8081

# 运行测试
uv run python scripts/test_session_api.py
```

### 预期输出

```
🚀 Session API 测试
============================================================

测试 1: 列出所有 Session
============================================================
✅ 成功！找到 3 个 Session

最近的 Session:
  - ID: sess_20260410_143022_a1b2
    Query: 丽江旅游景点推荐
    Status: completed
    Created: 2026-04-10T14:30:00Z

测试 2: 获取 Session 元数据
============================================================
✅ 成功！

Session 信息:
  - Query: 丽江旅游景点推荐
  - Layer-1 帖子: 1000 条
  - Layer-2 通过: 180 条
  - Layer-3 通过: 45 条
  - 状态: completed

测试 3: 获取 Session 结果（前 5 条）
============================================================
✅ 成功！

结果统计:
  - 总结果数: 45 条
  - Query: 丽江旅游景点推荐

前 3 条帖子:
  1. 丽江古城深度游攻略
     内容: 丽江古城是一个非常值得一去的地方...
     相关性: 0.92 (high)
     点赞: 1523 | 评论: 15
     平台: xhs | 作者: 旅行达人

测试 4: API 文档可访问性
============================================================
✅ Swagger UI 可访问！
   URL: http://localhost:8081/docs
```

---

## 📌 给同学的快速上手指南

### 1. 获取 Session ID

找你要 Session ID（格式：`sess_yyyymmdd_hhmmss_xxxx`）

### 2. 调用 API

```python
import requests

# 配置（你提供的）
API_URL = "http://your-server:8081"
SESSION_ID = "sess_20260410_143022_a1b2"

# 获取数据
url = f"{API_URL}/api/sessions/{SESSION_ID}/results"
params = {
    "limit": 100,        # 最多100条
    "min_score": 0.7,    # 相关性≥0.7
}

response = requests.get(url, params=params)
data = response.json()

# 使用数据
print(f"获取到 {data['total_results']} 条高质量数据")

for item in data["results"]:
    post = item["post"]
    # 你的 Agent 逻辑...
    process_post(post)
```

### 3. 完整示例（Agent 客户端类）

```python
class FilterDataClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def get_posts(self, session_id: str, min_score: float = 0.7, limit: int = 100):
        """获取过滤后的帖子"""
        url = f"{self.base_url}/api/sessions/{session_id}/results"
        response = requests.get(url, params={"min_score": min_score, "limit": limit})
        response.raise_for_status()
        return response.json()["results"]

# 使用
client = FilterDataClient("http://your-server:8081")
posts = client.get_posts("sess_abc", min_score=0.7, limit=50)
```

---

## 🎯 核心优势

1. ✅ **安全**：不暴露 Supabase 凭证
2. ✅ **简洁**：标准 REST API，易于集成
3. ✅ **标准化**：统一的 JSON 格式
4. ✅ **文档化**：自动生成 Swagger UI
5. ✅ **灵活**：支持分页、过滤、排序
6. ✅ **跨域友好**：轻松支持跨局域网/公网访问

---

## 📚 相关文档

- **完整使用指南**: `docs/SESSION_API_GUIDE.md`
- **API 实现**: `filter_engine/api.py` (第 1050+ 行)
- **测试脚本**: `scripts/test_session_api.py`
- **Swagger 文档**: http://localhost:8081/docs (服务启动后访问)

---

## 🔗 快速链接

```bash
# 启动 API 服务
uv run uvicorn filter_engine.api:app --host 0.0.0.0 --port 8081

# 测试接口
uv run python scripts/test_session_api.py

# 查看文档
http://localhost:8081/docs
```

---

**总结**：通过 FastAPI 封装的 REST API 是**最推荐**的方案！🎉
