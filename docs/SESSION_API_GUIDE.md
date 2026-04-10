# Session API 使用指南

## 📋 概述

为了方便跨局域网的 Agent 获取过滤后的数据，我们提供了一套 RESTful API 接口，用于查询 Layer-3 最终过滤结果。

**核心优势**：
- ✅ 安全：不暴露 Supabase 凭证
- ✅ 简洁：统一的 JSON 格式
- ✅ 标准化：符合 REST 规范
- ✅ 自动文档：访问 `/docs` 查看 Swagger UI

---

## 🚀 快速开始

### 1. 启动 API 服务

```bash
# 本地开发模式
uv run uvicorn filter_engine.api:app --host 0.0.0.0 --port 8081 --reload

# 生产模式（稳定）
uv run uvicorn filter_engine.api:app --host 0.0.0.0 --port 8081
```

**服务地址**：
- 本地：`http://localhost:8081`
- 局域网：`http://<你的IP>:8081`
- 公网：部署到云服务后的域名

### 2. 访问 API 文档

打开浏览器访问：`http://localhost:8081/docs`

你会看到自动生成的交互式 API 文档（Swagger UI），可以直接测试所有接口。

---

## 📡 核心接口

### 1️⃣ 获取 Session 结果（最重要）

**端点**：`GET /api/sessions/{session_id}/results`

**用途**：获取 Layer-3 最终过滤的帖子+评论数据

**请求示例**：
```bash
# 基础查询
curl http://localhost:8081/api/sessions/sess_abc123/results

# 带参数查询（前50条，相关性≥0.7）
curl "http://localhost:8081/api/sessions/sess_abc123/results?limit=50&min_score=0.7"

# 分页查询（第2页，每页20条）
curl "http://localhost:8081/api/sessions/sess_abc123/results?limit=20&offset=20"
```

**Python 调用示例**：
```python
import requests

session_id = "sess_abc123"
url = f"http://your-server:8081/api/sessions/{session_id}/results"

# 请求参数
params = {
    "limit": 100,        # 最多返回100条
    "min_score": 0.6,    # 只要相关性≥0.6的
}

response = requests.get(url, params=params)
data = response.json()

# 使用数据
for item in data["results"]:
    post = item["post"]
    print(f"标题: {post['title']}")
    print(f"内容: {post['content'][:100]}...")
    print(f"相关性: {post['relevance_score']}")
    print(f"评论数: {item['comment_count']}")
    print("-" * 50)
```

**响应格式**：
```json
{
  "session_id": "sess_abc123",
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
          "metrics_likes": 15
        }
      ],
      "comment_count": 15
    }
  ],
  "metadata": {
    "session_id": "sess_abc123",
    "query_text": "丽江旅游景点推荐",
    "l1_total_posts": 1000,
    "l2_passed_posts": 180,
    "l3_passed_posts": 45,
    "status": "completed",
    "created_at": "2026-04-09T14:30:00Z"
  }
}
```

---

### 2️⃣ 获取 Session 元数据

**端点**：`GET /api/sessions/{session_id}/metadata`

**用途**：查看过滤任务的统计信息

**请求示例**：
```bash
curl http://localhost:8081/api/sessions/sess_abc123/metadata
```

**响应示例**：
```json
{
  "session_id": "sess_abc123",
  "query_text": "丽江旅游景点推荐",
  "l1_total_posts": 1000,
  "l1_total_comments": 5000,
  "l2_passed_posts": 180,
  "l2_passed_comments": 850,
  "l3_passed_posts": 45,
  "status": "completed",
  "created_at": "2026-04-09T14:30:00Z",
  "completed_at": "2026-04-09T14:35:00Z"
}
```

---

### 3️⃣ 列出所有 Session

**端点**：`GET /api/sessions`

**用途**：查看所有过滤任务

**请求示例**：
```bash
# 获取最近20个 Session
curl http://localhost:8081/api/sessions?limit=20

# 只看已完成的
curl http://localhost:8081/api/sessions?status=completed
```

**响应示例**：
```json
{
  "total": 5,
  "sessions": [
    {
      "session_id": "sess_abc123",
      "query_text": "丽江旅游",
      "status": "completed",
      "created_at": "2026-04-09T14:30:00Z"
    },
    {
      "session_id": "sess_xyz789",
      "query_text": "成都美食",
      "status": "completed",
      "created_at": "2026-04-08T10:15:00Z"
    }
  ]
}
```

---

### 4️⃣ 删除 Session

**端点**：`DELETE /api/sessions/{session_id}`

**用途**：清理旧的 Session 数据

**请求示例**：
```bash
curl -X DELETE http://localhost:8081/api/sessions/sess_abc123
```

**响应示例**：
```json
{
  "message": "Session 'sess_abc123' deleted successfully"
}
```

---

## 🌐 跨局域网部署

### 方案 1：本地端口映射（临时方案）

使用 **ngrok** 或 **frp** 将本地服务暴露到公网：

```bash
# 使用 ngrok（免费）
ngrok http 8081

# 会生成一个临时 URL，如：
# https://abc123.ngrok.io -> http://localhost:8081
```

然后告诉同学访问：`https://abc123.ngrok.io/api/sessions/{session_id}/results`

---

### 方案 2：云服务部署（推荐）

**选项 A：Railway（最简单，免费额度）**

1. 注册 Railway.app
2. 连接 GitHub 仓库
3. 自动部署（检测到 `requirements.txt` 会自动安装依赖）
4. 获得永久域名：`https://your-project.railway.app`

**选项 B：Render（稳定，免费层）**

1. 注册 Render.com
2. 创建 Web Service
3. 设置启动命令：
   ```bash
   uvicorn filter_engine.api:app --host 0.0.0.0 --port $PORT
   ```
4. 获得域名：`https://your-service.onrender.com`

**选项 C：Vercel（边缘计算，超快）**

需要创建 `vercel.json`：
```json
{
  "builds": [
    {
      "src": "filter_engine/api.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "filter_engine/api.py"
    }
  ]
}
```

---

## 🔐 安全建议

### 1. 添加 API Key 认证（可选）

在 `filter_engine/api.py` 中添加：

```python
from fastapi import Header, HTTPException

API_KEY = "your-secret-key-here"  # 改为环境变量

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

# 在需要保护的端点上添加依赖
@app.get("/api/sessions/{session_id}/results", dependencies=[Depends(verify_api_key)])
async def get_session_results(...):
    ...
```

调用时带上 Header：
```bash
curl -H "X-API-Key: your-secret-key-here" \
  http://localhost:8081/api/sessions/sess_abc123/results
```

---

### 2. 配置 CORS（允许跨域）

如果同学的 Agent 是在浏览器中运行，需要配置 CORS：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 💡 Agent 使用示例

### Python Agent

```python
import requests
from typing import List, Dict

class FilterDataClient:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key} if api_key else {}
    
    def get_filtered_posts(
        self,
        session_id: str,
        min_score: float = 0.6,
        limit: int = 100,
    ) -> List[Dict]:
        """获取过滤后的帖子数据"""
        url = f"{self.base_url}/api/sessions/{session_id}/results"
        params = {"min_score": min_score, "limit": limit}
        
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        
        data = response.json()
        return data["results"]
    
    def get_session_info(self, session_id: str) -> Dict:
        """获取 Session 统计信息"""
        url = f"{self.base_url}/api/sessions/{session_id}/metadata"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()


# 使用示例
client = FilterDataClient("http://your-server:8081")

# 获取数据
results = client.get_filtered_posts("sess_abc123", min_score=0.7, limit=50)

for item in results:
    post = item["post"]
    # 处理数据...
    print(f"处理帖子: {post['title']}")
```

---

### JavaScript Agent

```javascript
class FilterDataClient {
  constructor(baseURL, apiKey = null) {
    this.baseURL = baseURL;
    this.headers = apiKey ? { 'X-API-Key': apiKey } : {};
  }

  async getFilteredPosts(sessionId, { minScore = 0.6, limit = 100 } = {}) {
    const url = `${this.baseURL}/api/sessions/${sessionId}/results`;
    const params = new URLSearchParams({ min_score: minScore, limit });
    
    const response = await fetch(`${url}?${params}`, {
      headers: this.headers
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    return data.results;
  }
}

// 使用示例
const client = new FilterDataClient('http://your-server:8081');

const results = await client.getFilteredPosts('sess_abc123', {
  minScore: 0.7,
  limit: 50
});

results.forEach(item => {
  const post = item.post;
  console.log(`处理帖子: ${post.title}`);
  // 处理数据...
});
```

---

## 📊 完整工作流程

### 数据过滤端（你）

```bash
# 1. 运行 Layer-2 + Layer-3 过滤
uv run python scripts/batch_scene_filter_smart.py \
  --query "保留关于丽江旅游、景点、美食的真实体验分享"

# 输出：Session ID: sess_20260410_143022_a1b2

# 2. 启动 API 服务
uv run uvicorn filter_engine.api:app --host 0.0.0.0 --port 8081

# 3. 告诉同学 Session ID
# "Hey，我过滤好了，Session ID 是 sess_20260410_143022_a1b2"
```

---

### Agent 端（同学）

```python
import requests

# 配置 API 地址（你提供的）
API_URL = "http://your-server:8081"
SESSION_ID = "sess_20260410_143022_a1b2"

# 获取数据
response = requests.get(
    f"{API_URL}/api/sessions/{SESSION_ID}/results",
    params={"min_score": 0.7, "limit": 100}
)

data = response.json()

print(f"总共获取 {data['total_results']} 条结果")

# 处理数据
for item in data["results"]:
    post = item["post"]
    
    # 你的 Agent 逻辑...
    process_post(post)
```

---

## 🐛 常见问题

### Q1: 如何查看所有可用的 Session？

```bash
curl http://localhost:8081/api/sessions
```

---

### Q2: 数据太多，如何分页？

```bash
# 第1页（0-99）
curl "http://localhost:8081/api/sessions/sess_abc/results?limit=100&offset=0"

# 第2页（100-199）
curl "http://localhost:8081/api/sessions/sess_abc/results?limit=100&offset=100"
```

---

### Q3: 只要高相关性的数据怎么办？

```bash
curl "http://localhost:8081/api/sessions/sess_abc/results?min_score=0.8"
```

---

### Q4: API 响应太慢？

**原因**：数据量大或网络慢

**解决方案**：
1. 减少 `limit` 参数（如改为50）
2. 使用 `min_score` 过滤低分数据
3. 考虑在 Supabase 添加索引（`session_id`, `relevance_score`）

---

### Q5: 同学无法访问我的 API？

**检查清单**：
- [ ] API 服务已启动（`uvicorn` 正在运行）
- [ ] 防火墙允许 8081 端口
- [ ] 使用正确的 IP 地址（不是 `localhost`，而是 `192.168.x.x` 或公网 IP）
- [ ] 如果跨公网，考虑使用 ngrok 或部署到云服务

---

## 📖 参考资源

- **Swagger UI 文档**：http://localhost:8081/docs
- **ReDoc 文档**：http://localhost:8081/redoc
- **FastAPI 官方文档**：https://fastapi.tiangolo.com/
- **ngrok 使用指南**：https://ngrok.com/docs

---

## ✅ 总结

**推荐方案**：使用 FastAPI 封装的 REST API

**优势**：
1. ✅ 安全：不暴露数据库凭证
2. ✅ 简洁：统一的 JSON 格式
3. ✅ 灵活：支持分页、过滤、排序
4. ✅ 文档：自动生成交互式 API 文档
5. ✅ 跨域：轻松支持跨局域网/公网访问

**核心端点**：
```
GET /api/sessions/{session_id}/results
```

这是同学最需要的接口，返回 Layer-3 最终过滤的高质量数据！🎉
