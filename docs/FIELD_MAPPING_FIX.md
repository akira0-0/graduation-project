# 字段映射修复记录

## 修复日期
2026-04-08

## 问题描述
原脚本使用了不存在的字段名（如 `author`, `content_id` 等），导致 Supabase API 报错：
```
Could not find the 'author' column of 'session_l2_posts' in the schema cache
```

## 修复内容

### 1. `insert_session_l2_posts_batch` 函数

**修复前**（错误字段）：
```python
{
    "session_id": session_id,
    "content_id": post.get("content_id"),     # ❌ 错误
    "author": post.get("author"),              # ❌ 不存在
    "note_url": post.get("note_url"),         # ❌ 应为 url
    "collected_at": post.get("collected_at"), # ❌ 应为 publish_time
}
```

**修复后**（正确字段，完全匹配 `schema_session.sql`）：
```python
{
    "id": post.get("id"),                           # ✅ 主键
    "session_id": session_id,
    "platform": post.get("platform", "xhs"),
    "type": post.get("type"),
    "url": post.get("url") or post.get("note_url"),
    "title": post.get("title"),
    "content": post.get("content", ""),
    "publish_time": post.get("publish_time"),
    # 作者信息（拆分为多个字段）
    "author_id": post.get("author_id"),
    "author_nickname": post.get("author_nickname"),
    "author_ip_location": post.get("author_ip_location"),
    "author_is_verified": post.get("author_is_verified", False),
    # 互动指标
    "metrics_likes": post.get("metrics_likes", 0),
    "metrics_collects": post.get("metrics_collects", 0),
    "metrics_comments": post.get("metrics_comments", 0),
    "metrics_shares": post.get("metrics_shares", 0),
    # 标签
    "tags": post.get("tags"),
    "source_keyword": post.get("source_keyword"),
    # Layer-2 元数据
    "scene_matched_rules": json.dumps(matched_rules, ensure_ascii=False),
    "filter_batch_id": post.get("filter_batch_id"),
}
```

---

### 2. `insert_session_l2_comments_batch` 函数

**修复前**：
```python
{
    "session_id": session_id,
    "content_id": comment.get("content_id"),
    "comment_id": comment.get("comment_id"),      # ❌ 应为 id（主键）
    "author": comment.get("author"),              # ❌ 不存在
}
```

**修复后**：
```python
{
    "id": comment.get("id"),                      # ✅ 主键
    "session_id": session_id,
    "content_id": comment.get("content_id"),      # ✅ 关联的帖子 ID
    "platform": comment.get("platform", "xhs"),
    "content": comment.get("content", ""),
    "publish_time": comment.get("publish_time"),
    # 作者信息
    "author_id": comment.get("author_id"),
    "author_nickname": comment.get("author_nickname"),
    "author_ip_location": comment.get("author_ip_location"),
    # 互动指标
    "metrics_likes": comment.get("metrics_likes", 0),
    "metrics_sub_comments": comment.get("metrics_sub_comments", 0),
    # 评论层级
    "parent_comment_id": comment.get("parent_comment_id"),
    "root_comment_id": comment.get("root_comment_id"),
    "reply_to_user_id": comment.get("reply_to_user_id"),
    "reply_to_user_nickname": comment.get("reply_to_user_nickname"),
    "comment_level": comment.get("comment_level", 1),
    # Layer-2 元数据
    "scene_matched_rules": json.dumps(matched_rules, ensure_ascii=False),
    "filter_batch_id": comment.get("filter_batch_id"),
}
```

---

### 3. `update_session_metadata` 函数

**修复前**：
```python
def update_session_metadata(
    ...,
    scene: str,                    # ❌ schema 中无此字段
    matched_rules_count: int,      # ❌ schema 中无此字段
    gap_rules_count: int,          # ❌ schema 中无此字段
):
    supabase.table("session_metadata").insert({
        "query": "",               # ❌ 应为 query_text
        "detected_scene": scene,   # ❌ schema 中无此字段
    })
```

**修复后**：
```python
def update_session_metadata(
    supabase: Client,
    session_id: str,
    query_text: str,              # ✅ 正确字段名
    l1_total_posts: int,
    l1_total_comments: int,
    l2_passed_posts: int,
    l2_passed_comments: int,
    dry_run: bool,
):
    supabase.table("session_metadata").insert({
        "session_id": session_id,
        "query_text": query_text,     # ✅ 正确字段名
        "l1_total_posts": l1_total_posts,
        "l1_total_comments": l1_total_comments,
        "l2_passed_posts": l2_passed_posts,
        "l2_passed_comments": l2_passed_comments,
        "l3_passed_posts": 0,
        "status": "completed",
    })
```

---

### 4. 联动查询字段修复

**修复前**：
```python
passed_post_ids = [p.get("content_id") for p in passed_posts]  # ❌ 错误
```

**修复后**：
```python
passed_post_ids = [p.get("id") for p in passed_posts]  # ✅ 正确
# filtered_posts 的主键是 id，不是 content_id
```

---

### 5. 评论计数初始化修复

**修复前**：
```python
if not all_comments:
    print("⚠️  无评论数据，跳过")
else:
    ...
    l2_passed_comments_count = insert_session_l2_comments_batch(...)
# ❌ 如果没有评论，l2_passed_comments_count 未定义
```

**修复后**：
```python
l2_passed_comments_count = 0  # ✅ 初始化
if not all_comments:
    print("⚠️  无评论数据，跳过")
else:
    ...
    l2_passed_comments_count = insert_session_l2_comments_batch(...)
```

---

## Schema 参考

### `session_l2_posts` 表结构
```sql
CREATE TABLE IF NOT EXISTS session_l2_posts (
    id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    type VARCHAR(20),
    url TEXT,
    title VARCHAR(500),
    content TEXT,
    publish_time TIMESTAMP,
    author_id VARCHAR(50),
    author_nickname VARCHAR(100),
    author_ip_location VARCHAR(50),
    author_is_verified BOOLEAN DEFAULT FALSE,
    metrics_likes INTEGER DEFAULT 0,
    metrics_collects INTEGER DEFAULT 0,
    metrics_comments INTEGER DEFAULT 0,
    metrics_shares INTEGER DEFAULT 0,
    tags JSONB,
    source_keyword VARCHAR(100),
    scene_matched_rules JSONB,
    filter_batch_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    query_text TEXT
);
```

### `session_l2_comments` 表结构
```sql
CREATE TABLE IF NOT EXISTS session_l2_comments (
    id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    content_id VARCHAR(50) NOT NULL,        -- 关联的帖子 ID
    platform VARCHAR(20) NOT NULL,
    content TEXT,
    publish_time TIMESTAMP,
    author_id VARCHAR(50),
    author_nickname VARCHAR(100),
    author_ip_location VARCHAR(50),
    metrics_likes INTEGER DEFAULT 0,
    metrics_sub_comments INTEGER DEFAULT 0,
    parent_comment_id VARCHAR(50),
    root_comment_id VARCHAR(50),
    reply_to_user_id VARCHAR(50),
    reply_to_user_nickname VARCHAR(100),
    comment_level INTEGER DEFAULT 1,
    scene_matched_rules JSONB,
    filter_batch_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    query_text TEXT
);
```

### `session_metadata` 表结构
```sql
CREATE TABLE IF NOT EXISTS session_metadata (
    session_id VARCHAR(50) PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_intent JSONB,
    l1_total_posts INTEGER DEFAULT 0,
    l1_total_comments INTEGER DEFAULT 0,
    l2_passed_posts INTEGER DEFAULT 0,
    l2_passed_comments INTEGER DEFAULT 0,
    l3_passed_posts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT
);
```

---

## 测试验证

修复后运行测试：
```bash
cd e:\xhs-crawler

# Dry-run 测试
uv run python scripts/batch_scene_filter_smart.py \
    --query "过滤电商广告" \
    --dry-run

# 正式运行
uv run python scripts/batch_scene_filter_smart.py \
    --query "过滤电商广告"
```

---

## 经验教训

1. **字段映射一致性**：脚本中的字段名必须严格匹配数据库 Schema
2. **Schema First**：先设计 Schema，再编写插入代码
3. **完整映射**：使用 `schema_session.sql` 中的所有字段，避免遗漏
4. **变量初始化**：所有可能为空的计数器必须初始化为 0
5. **主键映射**：`filtered_posts.id` → `session_l2_posts.id`（主键复制）

---

## 文件变更清单

- ✅ `scripts/batch_scene_filter_smart.py`
  - 修复 `insert_session_l2_posts_batch`
  - 修复 `insert_session_l2_comments_batch`
  - 修复 `update_session_metadata`
  - 修复联动查询字段
  - 修复变量初始化
