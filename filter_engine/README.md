# 数据过滤引擎 (Filter Engine)

基于规则引擎和大语言模型的内容过滤系统，支持高效的关键词匹配、正则表达式过滤和 LLM 语义分析。

## 功能特性

### 🚀 核心功能

- **AC自动机关键词匹配**: 基于 Aho-Corasick 算法，O(n) 复杂度多关键词匹配
- **正则表达式过滤**: 支持超时保护，防止 ReDoS 攻击
- **LLM 语义过滤**: 支持 OpenAI、通义千问、智谱 GLM、Ollama 等多模型
- **协同决策引擎**: 规则引擎与 LLM 结合，置信度加权决策
- **缓存优化**: LRU 缓存 + SimHash 相似文本去重

### 📊 管理功能

- **规则 CRUD**: 创建、读取、更新、删除规则
- **版本管理**: 规则变更历史，支持回滚
- **批量导入导出**: JSON 格式规则迁移
- **Web 管理界面**: Vue3 + Element Plus 前端

## 快速开始

### 1. 安装依赖

```bash
cd e:\xhs-crawler
uv add pyahocorasick httpx pydantic-settings
```

### 2. 启动 API 服务

```bash
# 开发模式（热重载）
uv run uvicorn filter_engine.api:app --host 127.0.0.1 --port 8081 --reload

# 生产模式
uv run python -m filter_engine.main
```

### 3. 访问服务

- **Web 管理界面**: http://127.0.0.1:8081
- **API 文档**: http://127.0.0.1:8081/docs
- **健康检查**: http://127.0.0.1:8081/health

## 使用方法

### Python API

```python
from filter_engine import FilterPipeline

# 初始化（不使用LLM）
pipeline = FilterPipeline(use_llm=False)

# 过滤单条文本
result = pipeline.filter_text("这是一条测试评论")
print(f"是否过滤: {result.should_filter}")
print(f"置信度: {result.confidence}")
print(f"命中规则: {result.matched_rules}")

# 批量过滤
texts = ["评论1", "评论2", "评论3"]
batch_result = pipeline.filter_batch(texts)
for text, res in zip(texts, batch_result.results):
    print(f"{text}: {'过滤' if res.should_filter else '通过'}")

# 过滤并分流
passed, filtered = pipeline.filter_and_split(texts)
print(f"通过: {len(passed)}, 过滤: {len(filtered)}")
```

### 使用 LLM 过滤

```python
# 需要配置环境变量
# FILTER_LLM_PROVIDER=openai
# FILTER_LLM_API_KEY=sk-xxx
# FILTER_LLM_BASE_URL=https://api.openai.com/v1

pipeline = FilterPipeline(use_llm=True)
result = pipeline.filter_text("复杂的待分析文本")
```

### REST API

```bash
# 过滤文本
curl -X POST http://127.0.0.1:8081/api/filter \
  -H "Content-Type: application/json" \
  -d '{"text": "测试文本"}'

# 批量过滤
curl -X POST http://127.0.0.1:8081/api/filter/batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["文本1", "文本2"]}'

# 获取规则列表
curl http://127.0.0.1:8081/api/rules

# 创建规则
curl -X POST http://127.0.0.1:8081/api/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "垃圾词过滤",
    "type": "keyword",
    "content": "[\"垃圾\", \"广告\", \"骗子\"]",
    "category": "spam",
    "priority": 100
  }'

# 获取统计信息
curl http://127.0.0.1:8081/api/stats
```

## 配置说明

通过环境变量配置（前缀 `FILTER_`）：

```bash
# LLM 配置
FILTER_LLM_PROVIDER=openai          # openai | qwen | glm | ollama
FILTER_LLM_API_KEY=sk-xxx           # API 密钥
FILTER_LLM_BASE_URL=                # 自定义 API 地址
FILTER_LLM_MODEL=gpt-3.5-turbo      # 模型名称

# 过滤阈值
FILTER_SPAM_THRESHOLD=0.7           # 垃圾内容阈值
FILTER_RULE_CONFIDENCE_THRESHOLD=0.8 # 规则置信度阈值

# 缓存配置
FILTER_CACHE_ENABLED=true           # 启用缓存
FILTER_CACHE_MAX_SIZE=10000         # 缓存大小
FILTER_CACHE_TTL=3600               # 缓存过期时间（秒）

# 数据库
FILTER_DB_PATH=filter_engine/data/rules.db
```

## 规则类型

| 类型 | 说明 | content 格式 |
|------|------|--------------|
| `keyword` | 关键词匹配 | `["词1", "词2", "词3"]` |
| `regex` | 正则表达式 | `["pattern1", "pattern2"]` |
| `semantic` | 语义规则（LLM） | 自然语言描述 |

## 规则分类

| 分类 | 说明 |
|------|------|
| `spam` | 垃圾/广告内容 |
| `abuse` | 辱骂/攻击内容 |
| `political` | 政治敏感内容 |
| `porn` | 色情内容 |
| `illegal` | 违法内容 |
| `other` | 其他 |

## 项目结构

```
filter_engine/
├── __init__.py          # 模块导出
├── api.py               # FastAPI 路由
├── config.py            # 配置管理
├── main.py              # 启动入口
├── pipeline.py          # 主过滤管道
├── requirements.txt     # 依赖列表
├── core/                # 核心引擎
│   ├── cache.py         # LRU缓存 + SimHash
│   ├── decision.py      # 协同决策引擎
│   └── rule_engine.py   # AC自动机 + 正则引擎
├── llm/                 # LLM 集成
│   ├── client.py        # 多模型客户端
│   ├── engine.py        # LLM 过滤引擎
│   ├── parser.py        # 输出解析器
│   └── prompts.py       # 提示词模板
├── rules/               # 规则管理
│   ├── manager.py       # CRUD + 版本管理
│   └── models.py        # Pydantic 模型
├── data/                # 数据存储
│   ├── rules.db         # SQLite 规则库
│   └── schema.sql       # 数据库 Schema
└── web/
    └── index.html       # Vue3 管理界面
```

## 决策流程

```
输入文本
    │
    ▼
┌─────────────┐
│  缓存检查   │ ──命中──> 返回缓存结果
└─────────────┘
    │ 未命中
    ▼
┌─────────────┐
│  规则引擎   │
│ (AC + Regex)│
└─────────────┘
    │
    ▼
┌─────────────────────┐
│ 置信度 >= 阈值?     │
│ (高置信度直接决策)   │
└─────────────────────┘
    │ 否          │ 是
    ▼             ▼
┌─────────────┐   返回规则结果
│  LLM 分析   │
│ (语义理解)   │
└─────────────┘
    │
    ▼
┌─────────────┐
│  协同决策   │
│ (加权融合)   │
└─────────────┘
    │
    ▼
更新缓存 → 返回结果
```

## API 端点

### 规则管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/rules` | 获取规则列表 |
| GET | `/api/rules/stats` | 规则统计 |
| GET | `/api/rules/{id}` | 获取单条规则 |
| POST | `/api/rules` | 创建规则 |
| PUT | `/api/rules/{id}` | 更新规则 |
| DELETE | `/api/rules/{id}` | 删除规则 |
| POST | `/api/rules/{id}/toggle` | 切换启用状态 |
| GET | `/api/rules/{id}/versions` | 版本历史 |
| POST | `/api/rules/{id}/rollback` | 回滚版本 |
| POST | `/api/rules/import` | 批量导入 |
| GET | `/api/rules/export` | 批量导出 |

### 过滤接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/filter` | 过滤单条文本 |
| POST | `/api/filter/batch` | 批量过滤 |

### 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/stats` | 系统统计 |
| POST | `/api/cache/clear` | 清空缓存 |
| POST | `/api/reload` | 重新加载规则 |

## 性能优化

1. **AC 自动机**: 多关键词匹配 O(n) 复杂度
2. **LRU 缓存**: 相同文本直接返回
3. **SimHash 去重**: 相似文本复用结果
4. **正则超时**: 防止 ReDoS 攻击
5. **批量处理**: 减少 LLM API 调用

## 注意事项

1. **pyahocorasick**: 需要 C 编译器，Windows 可能需要 Visual Studio Build Tools
2. **LLM 费用**: 使用 LLM 会产生 API 调用费用
3. **规则优先级**: 数值越大优先级越高
4. **缓存失效**: 规则变更后会自动清空缓存

## 许可证

本项目仅供学习研究使用，请遵守相关法律法规。
