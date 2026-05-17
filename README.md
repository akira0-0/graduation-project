# XHS-Crawler · 社交媒体采集与智能过滤系统

多平台社交媒体爬虫 + 三层智能内容过滤引擎，支持与智能体工作流对接。

---

## 🚀 启动服务

### 后端（过滤引擎 API）

```cmd
cd e:\MEDIA_ANALYSIS_SYSTEM\xhs-crawler
uv run python -m filter_engine.api
```

> 启动后访问 `http://localhost:8081`，Swagger 文档：`http://localhost:8081/docs`

### 前端（可视化管理界面）

```cmd
cd e:\MEDIA_ANALYSIS_SYSTEM\xhs-crawler\filter_engine\web\app
npm run dev
```

> 启动后访问 `http://localhost:5173`（若端口占用自动顺延至 5174 等）

> ⚠️ 前端需要后端同时运行，否则所有 API 请求会报 `ECONNREFUSED`

---

## 快速开始

### 环境要求

- Python 3.11 / 3.12（不支持 3.13+）
- 包管理器：[uv](https://docs.astral.sh/uv/)
- Chrome / Edge（CDP 模式需要）

### 安装

```cmd
uv sync
copy .env.example .env   # 填写 SUPABASE_URL、SUPABASE_KEY、OPENAI_API_KEY
```

---

## 功能模块

### 一、爬虫采集

| 平台 | 入口 | 配置文件 |
|------|------|---------|
| 小红书 | `uv run main.py` | `config/base_config.py` `config/xhs_config.py` |
| 微博 | `uv run weibo_crawler/weibo_crawler/main.py` | `weibo_crawler/weibo_crawler/config.json` |

采集数据统一保存为标准格式到 `data/unified/`，再通过 `import_with_sdk.py` 导入 Supabase。

---

### 二、三层过滤引擎

```
原始数据 (posts / comments)
    ↓
Layer-1  全量初步过滤      batch_filter.py           → filtered_posts / filtered_comments
    ↓
Layer-2  场景规则过滤      batch_scene_filter_smart.py → session_l2_posts / session_l2_comments
    ↓
Layer-3  LLM语义过滤      （Layer-2 完成后自动触发）  → session_l3_results
```

#### Layer-1：全量过滤

```cmd
uv run python scripts/batch_filter.py --data-type all
uv run python scripts/batch_filter.py --data-type all --platform xhs --dry-run
```

过滤规则存储在 Supabase `rules` 表，通过 `http://localhost:8081/api/rules` 管理。

#### Layer-2：场景规则过滤（SmartRuleMatcher）

```cmd
uv run python scripts/batch_scene_filter_smart.py --query "丽江旅游攻略"

# 常用参数
--force-scenario travel   # 跳过 LLM 场景识别，直接指定场景
--save-gap-rules          # 将 LLM 生成的补充规则保存到数据库
--skip-layer3             # 不自动触发 Layer-3
--dry-run                 # 试运行，不写数据库
```

**Layer-2 工作原理**

1. LLM 识别场景（`travel` / `ecommerce` / `normal` 等）
2. 从规则库加载场景规则
3. LLM 思维链分析：匹配已有规则 + 生成缺口补充规则
4. 规则引擎（AC自动机）批量过滤帖子和评论
5. 自动衔接 Layer-3

> 规则匹配字段：帖子 = `title + content + tags`，评论 = `content`  
> 关键词规则使用 **OR 逻辑**：满足任意一个关键词即命中

**Layer-2 两种模式对比**

| 特性 | 方案 A（DynamicFilterPipeline） | 方案 B（SmartRuleMatcher）✅ 推荐 |
|------|---------------------------------|-----------------------------------|
| 场景识别 | 关键词匹配 | LLM 语义识别 |
| 规则补充 | ❌ 无 | ✅ 自动生成 |
| 速度 | 快 | 慢（~2-5s/次） |
| 适合场景 | 场景明确、规则完善 | 复杂语义、规则不全 |

#### Layer-3：LLM 语义相关性过滤

```cmd
# 独立运行
uv run python scripts/batch_llm_filter.py --session-id sess_xxx --llm-only

# 参数说明
--llm-only             # 每条都调 LLM（最高准确率）
--no-llm               # 纯关键词匹配（最快）
--min-relevance high   # 相关性阈值: high / medium / low
--clear-existing       # 清理旧数据后重跑
```

**三种模式对比**

| 模式 | 准确率 | 速度 | 成本 |
|------|--------|------|------|
| LLM Only | ⭐⭐⭐⭐⚡ | 慢 | 高 |
| 混合（默认） | ⭐⭐⭐⭐ | 中 | 中 |
| 纯关键词 | ⭐⭐⭐ | 快 | 无 |

---

### 三、过滤引擎 API 服务

```cmd
cd e:\xhs-crawler
uv run python -m filter_engine.api          # 启动在 http://localhost:8081
```

Swagger 文档：`http://localhost:8081/docs`

**核心接口**

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/filter/auto` | 端到端过滤：输入 query，异步执行三层过滤，返回 `session_id` |
| `POST` | `/api/filter/complete` | 同步版本，直接返回帖子数据 |
| `GET` | `/api/sessions/{session_id}/results` | 获取过滤结果 |
| `GET` | `/api/rules` | 规则列表 |
| `POST` | `/api/rules` | 新建规则 |
| `PUT` | `/api/rules/{id}/toggle` | 启用/禁用规则 |
| `POST` | `/api/rules/test` | 测试规则效果 |
| `GET` | `/api/stats` | 系统统计 |

**调用示例**

```bash
# 1. 提交过滤任务
curl -X POST http://localhost:8081/api/filter/auto \
  -H "Content-Type: application/json" \
  -d '{"query": "丽江旅游攻略", "platform": "xhs", "max_posts": 500}'

# 2. 获取结果
curl http://localhost:8081/api/sessions/sess_xxx/results
```

---

### 四、与智能体工作流对接

工作流引擎（`work-flow-main/`）通过 `XHSFilterAgent` 节点调用过滤引擎 API，实现：

```
工作流 query → XHSFilterNode (调用 /api/filter/auto) → SentimentAgent → ReportAgent
```

**启动工作流引擎**

```cmd
cd e:\xhs-crawler\work-flow-main\work-flow-main
python -m uvicorn workflow_engine.api.server:app --port 8000 --reload
```

**运行融合工作流**

```cmd
cd workflow_engine
python main.py --file ../test_data/xhs_opinion_workflow.json
```

修改 `test_data/xhs_opinion_workflow.json` 中的 `variables.topic` 字段即可更换查询关键词。

---

## 数据库表结构

| 类型 | 表名 | 用途 |
|------|------|------|
| 持久化 | `posts` / `comments` | 爬虫原始数据 |
| 持久化 | `filtered_posts` / `filtered_comments` | Layer-1 通过数据 |
| 持久化 | `rules` | 过滤规则库 |
| Session | `session_l2_posts` / `session_l2_comments` | Layer-2 结果（TTL 2h） |
| Session | `session_l3_results` | Layer-3 最终结果（帖子+评论嵌套） |
| Session | `session_metadata` | Session 统计信息 |

初始化：在 Supabase SQL Editor 中依次执行 `database/schema.sql` → `database/schema_filtered.sql` → `database/schema_session.sql`

---

## 常见问题

**Q: 过滤引擎启动报 ImportError**  
检查 `.env` 中的 `SUPABASE_URL` 和 `OPENAI_API_KEY` 是否已填写。

**Q: Layer-2 通过率异常高（接近 100%）**  
旧版 Bug（已修复）：只应用了 gap_rules，忽略了 matched_rules。更新代码后重新运行。

**Q: Layer-2 场景识别错误（如旅游被识别为电商）**  
使用 `--force-scenario travel` 跳过自动识别，或升级到 SmartRuleMatcher（纯 LLM 识别）。

**Q: session_l3_results 主键冲突**  
重复运行时加 `--clear-existing` 参数，内部已改用 `upsert` 防止冲突。

**Q: 工作流引擎启动报 `Input should be a valid string [current_node=None]`**  
`main.py` 初始状态中 `current_node` 应为 `""` 而非 `None`，已修复。

**Q: `cannot import name 'create_agent' from langchain.agents`**  
`sentiment_agent_v2.py` 使用了不存在的 API，已替换为 `from langgraph.prebuilt import create_react_agent`。

---

## 项目结构

```
xhs-crawler/
├── main.py                    # 小红书爬虫入口
├── filter_engine/             # 三层过滤引擎
│   ├── api.py                 # FastAPI 服务（端口 8081）
│   ├── core/                  # RuleEngine + RelevanceFilter
│   ├── llm/                   # LLM 客户端 + SmartRuleMatcher
│   └── rules/                 # 规则管理器
├── scripts/                   # 过滤执行脚本
│   ├── batch_filter.py        # Layer-1
│   ├── batch_scene_filter_smart.py  # Layer-2
│   └── batch_llm_filter.py   # Layer-3（独立运行时）
├── database/                  # SQL Schema 文件
├── docs/                      # 详细技术文档
├── work-flow-main/            # 智能体工作流引擎（同事代码）
│   └── work-flow-main/
│       ├── workflow_engine/   # 工作流核心
│       └── test_data/xhs_opinion_workflow.json  # 融合工作流示例
├── config/                    # 爬虫配置
├── weibo_crawler/             # 微博爬虫子项目
└── data/                      # 采集数据存储
```

---

## 文档索引

详细文档在 `docs/` 目录：

| 文档 | 内容 |
|------|------|
| `FILTER_WORKFLOW.md` | 三层过滤完整流程 |
| `LAYER2_COMPARISON.md` | Layer-2 两种方案对比 |
| `LAYER2_SMART_CRITICAL_BUG_FIX.md` | matched_rules 未应用 Bug 修复 |
| `LAYER2_SMART_LLM_ONLY.md` | 纯 LLM 场景识别优化 |
| `LAYER3_LLM_ONLY_MODE.md` | Layer-3 LLM 判断模式 |
| `PRIMARY_KEY_CONFLICT_FIX.md` | 主键冲突修复记录 |
| `FIELD_MAPPING_FIX.md` | 字段映射修复记录 |
| `work-flow-main/.../INTEGRATION_TEST_GUIDE.md` | 融合系统测试文档 |
