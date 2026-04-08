# 三层过滤流程完整指南

## 架构概览

```
原始数据 (posts + comments)
        │
        ▼
┌──────────────────────────────────────────────────┐
│ Layer-1: 全量初步过滤 (batch_filter.py)           │
│ • 引擎: FilterPipeline (规则引擎)                 │
│ • 规则: 通用规则 (通用-前缀)                      │
│ • 目标: 过滤垃圾/广告/违禁/过短内容               │
│ • 输出: filtered_posts + filtered_comments       │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│ Layer-2: 场景规则过滤 (batch_scene_filter.py)    │
│ • 引擎: DynamicFilterPipeline                    │
│ • 输入: 用户 query (如"丽江旅游攻略")             │
│ • 行为: 场景识别 → 动态选择规则 → 过滤           │
│ • 输出: session_l2_posts + session_l2_comments   │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│ Layer-3: LLM语义过滤 (batch_llm_filter.py)       │
│ • 引擎: RelevanceFilter (Embedding + LLM)        │
│ • 输入: session_l2_* 表数据                      │
│ • 行为: 只对帖子打相关性分数                      │
│ • 输出: session_l3_results (帖子+评论嵌套)       │
└──────────────────────────────────────────────────┘
```

---

## 数据表说明

### 持久化表 (Persistent)
| 表名 | 用途 | 数据来源 |
|------|------|---------|
| `posts` | 爬虫原始帖子 | 爬虫程序 |
| `comments` | 爬虫原始评论 | 爬虫程序 |
| `filtered_posts` | Layer-1 通过的帖子 | `batch_filter.py` |
| `filtered_comments` | Layer-1 通过的评论 | `batch_filter.py` |

### Session 临时表 (TTL 2小时)
| 表名 | 用途 | 数据来源 |
|------|------|---------|
| `session_l2_posts` | Layer-2 通过的帖子 | `batch_scene_filter.py` |
| `session_l2_comments` | Layer-2 通过的评论 | `batch_scene_filter.py` |
| `session_l3_results` | Layer-3 最终结果 (帖子+评论嵌套) | `batch_llm_filter.py` |
| `session_metadata` | Session 元数据和统计 | 各脚本自动维护 |

---

## 使用流程

### 前置准备

1. **初始化数据库表**
```bash
# 1. 在 Supabase SQL Editor 中执行
database/schema_filtered.sql    # 创建 filtered_* 表
database/schema_session.sql     # 创建 session_* 表

# 2. 如果 filter_logs 表缺少 data_type 列，执行迁移
database/migrate_add_data_type.sql
```

2. **确保有爬虫数据**
```bash
# 确认原始数据表有数据
SELECT COUNT(*) FROM posts;
SELECT COUNT(*) FROM comments;
```

---

### Step 1: Layer-1 全量初步过滤

**目的**: 过滤明显的垃圾/广告/违禁内容

```bash
# 过滤全部帖子和评论
uv run python scripts/batch_filter.py --data-type all

# 只过滤小红书平台
uv run python scripts/batch_filter.py --data-type all --platform xhs

# 试运行（不写数据库）
uv run python scripts/batch_filter.py --data-type all --dry-run
```

**输出检查**:
```sql
-- 查看通过数量
SELECT COUNT(*) FROM filtered_posts;
SELECT COUNT(*) FROM filtered_comments;

-- 查看过滤日志
SELECT * FROM filter_logs ORDER BY started_at DESC LIMIT 5;
```

**重置数据** (如需重跑):
```sql
TRUNCATE filtered_posts;
TRUNCATE filtered_comments;
TRUNCATE filter_logs;
```

---

### Step 2: Layer-2 场景规则过滤

**目的**: 根据用户 query 识别场景，应用场景规则

```bash
# 示例 1: 旅游攻略场景
uv run python scripts/batch_scene_filter.py --query "丽江旅游攻略"

# 示例 2: 电商场景 + 严格模式
uv run python scripts/batch_scene_filter.py --query "过滤电商广告和刷单" --severity strict

# 示例 3: 美食推荐 + 只处理小红书
uv run python scripts/batch_scene_filter.py --query "成都美食推荐" --platform xhs

# 示例 4: 评论只过滤有效帖子下的
uv run python scripts/batch_scene_filter.py --query "旅游景点" --filter-comments-mode valid-posts-only

# 试运行
uv run python scripts/batch_scene_filter.py --query "新闻资讯" --dry-run
```

**参数说明**:
- `--query`: 查询描述，用于场景识别 (必需)
- `--severity`: 过滤严格度 (`relaxed` / `normal` / `strict`)
- `--platform`: 平台过滤 (`xhs` / `weibo`)
- `--filter-comments-mode`: 评论模式 (`all` / `valid-posts-only`)
- `--no-llm`: 禁用 LLM 辅助 (更快，但可能不准)
- `--no-generate-rules`: 禁止自动生成规则

**输出检查**:
```sql
-- 查看 session 数据
SELECT session_id, query_text, created_at 
FROM session_metadata 
ORDER BY created_at DESC LIMIT 5;

-- 查看某个 session 的帖子和评论数量
SELECT 
  (SELECT COUNT(*) FROM session_l2_posts WHERE session_id = 'sess_xxx') AS posts,
  (SELECT COUNT(*) FROM session_l2_comments WHERE session_id = 'sess_xxx') AS comments;
```

**记住 session_id** (控制台输出):
```
session_id : sess_20260408_153022_a1b2c3d4
```

---

### Step 3: Layer-3 LLM 语义过滤

**目的**: 对帖子进行语义相关性判断，输出帖子+评论嵌套结构

```bash
# 使用 Layer-2 生成的 session_id
uv run python scripts/batch_llm_filter.py \
  --session-id sess_20260408_153022_a1b2c3d4 \
  --query "丽江有什么好玩的景点"

# 只要高相关的结果
uv run python scripts/batch_llm_filter.py \
  --session-id sess_xxx \
  --query "成都美食推荐" \
  --min-relevance high

# 纯关键词模式 (不调用 LLM，速度快)
uv run python scripts/batch_llm_filter.py \
  --session-id sess_xxx \
  --query "北京旅游" \
  --no-llm

# 试运行
uv run python scripts/batch_llm_filter.py \
  --session-id sess_xxx \
  --query "西安景点" \
  --dry-run
```

**参数说明**:
- `--session-id`: Layer-2 生成的 session ID (必需)
- `--query`: 语义查询 (必需)
- `--min-relevance`: 最低相关性 (`high` / `medium` / `low`)
- `--no-llm`: 只用关键词匹配

**输出检查**:
```sql
-- 查看最终结果
SELECT session_id, post_id, comment_count 
FROM session_l3_results 
WHERE session_id = 'sess_xxx';

-- 提取完整结果 (JSON 格式)
SELECT post_data, comments 
FROM session_l3_results 
WHERE session_id = 'sess_xxx'
LIMIT 10;

-- 查看帖子的相关性分数
SELECT 
  post_data->>'id' AS post_id,
  post_data->>'title' AS title,
  post_data->>'relevance_score' AS score
FROM session_l3_results 
WHERE session_id = 'sess_xxx'
ORDER BY (post_data->>'relevance_score')::numeric DESC;
```

---

## 输出数据格式

### Layer-3 最终结果格式 (`session_l3_results`)

```json
{
  "session_id": "sess_20260408_153022_a1b2c3d4",
  "post_id": "abc123",
  "post_data": {
    "id": "abc123",
    "platform": "xhs",
    "title": "丽江古城3天2夜攻略",
    "content": "...",
    "relevance_score": 0.92,
    "relevance_level": "high",
    "author_nickname": "旅行达人",
    "metrics_likes": 1234,
    ...
  },
  "comments": [
    {
      "id": "c001",
      "content": "求问住哪里比较好",
      "author_nickname": "用户A",
      "metrics_likes": 10,
      ...
    },
    {
      "id": "c002",
      "content": "束河古镇更推荐",
      ...
    }
  ],
  "comment_count": 2,
  "query_text": "丽江有什么好玩的景点"
}
```

---

## 性能优化建议

### Layer-2 优化
```bash
# 禁用 LLM 辅助（只用规则）
--no-llm

# 只过滤有效帖子的评论（减少数据量）
--filter-comments-mode valid-posts-only
```

### Layer-3 优化
```bash
# 纯关键词模式（速度最快，准确度略低）
--no-llm

# 降低相关性要求（获得更多结果）
--min-relevance low
```

---

## 数据清理

### 清理过期 Session 数据
```sql
-- 清理 2 小时前的数据
SELECT * FROM cleanup_expired_sessions(2);

-- 清理 1 小时前的数据
SELECT * FROM cleanup_expired_sessions(1);

-- 查看清理结果
-- 返回: (deleted_posts, deleted_comments, deleted_results, deleted_metadata)
```

### 手动清理特定 Session
```sql
-- 删除某个 session 的全部数据
DELETE FROM session_l2_posts WHERE session_id = 'sess_xxx';
DELETE FROM session_l2_comments WHERE session_id = 'sess_xxx';
DELETE FROM session_l3_results WHERE session_id = 'sess_xxx';
DELETE FROM session_metadata WHERE session_id = 'sess_xxx';
```

---

## 常见问题

### Q1: Layer-1/2 为什么没有置信度分数？
**A**: Layer-1/2 使用 AC 自动机 + 规则引擎，是布尔命中逻辑，没有语义相似度概念。只有 Layer-3 的 `relevance_score` (0~1) 是真正的语义置信度。

### Q2: 如何理解三层的过滤目标？
**A**: 
- **Layer-1**: 过滤通用垃圾（广告/违禁/过短），数据质量提升
- **Layer-2**: 过滤场景不匹配内容（如旅游 query 过滤电商内容）
- **Layer-3**: 过滤语义不相关内容（如"丽江"query 过滤"大理"帖子）

### Q3: Session 表数据会自动删除吗？
**A**: 需要手动或定时调用 `cleanup_expired_sessions()` 函数。推荐设置 Supabase pg_cron 每小时执行一次。

### Q4: 能否跳过 Layer-2 直接跑 Layer-3？
**A**: 技术上可以，但 Layer-2 的场景规则能大幅减少 Layer-3 的 LLM 调用次数，节省成本和时间。

### Q5: 如何调整过滤严格度？
**A**: 
- Layer-2: 使用 `--severity strict`
- Layer-3: 使用 `--min-relevance high`

---

## 完整示例

```bash
# 场景: 筛选小红书上关于"成都美食"的高质量帖子

# Step 1: Layer-1 全量过滤
uv run python scripts/batch_filter.py --data-type all --platform xhs

# Step 2: Layer-2 场景过滤
uv run python scripts/batch_scene_filter.py \
  --query "成都美食推荐" \
  --platform xhs \
  --severity normal
# 记住输出的 session_id: sess_20260408_160000_xyz

# Step 3: Layer-3 语义过滤
uv run python scripts/batch_llm_filter.py \
  --session-id sess_20260408_160000_xyz \
  --query "成都有什么好吃的特色美食" \
  --min-relevance medium

# Step 4: 提取最终结果
# 在 Supabase Dashboard 或 API 中查询 session_l3_results
```

---

## 技术栈

- **规则引擎**: AC 自动机 (pyahocorasick)
- **场景识别**: DynamicFilterPipeline + QueryAnalyzer
- **LLM**: OpenAI API / 通义千问 (可配置)
- **数据库**: Supabase (PostgreSQL)
- **语言**: Python 3.11+

---

## 相关文档

- [数据格式标准](DATA_FORMAT_STANDARD.md)
- [Filter Engine README](../filter_engine/README.md)
- [使用指南](使用指南.md)
