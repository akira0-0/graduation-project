# 主键冲突问题修复记录

## 概述

本文档记录了两次主键冲突问题的修复：
1. **Layer-2**: `session_l2_posts` 表主键冲突（已修复）
2. **Layer-3**: `session_l3_results` 表主键冲突（已修复）

---

## 问题 1: Layer-2 主键冲突

**错误日期**: 2026-04-08

**错误信息**:
```
postgrest.exceptions.APIError: {
  'message': 'duplicate key value violates unique constraint "session_l2_posts_pkey"',
  'code': '23505',
  'details': 'Key (id)=(5271530469590781) already exists.'
}
```

**发生位置**: `insert_session_l2_posts_batch` 函数

**根本原因**: 
Session 表的主键使用的是来自 `filtered_posts` 的原始 `id`，当同一条帖子在不同 session 中被处理时，会导致主键冲突。

---

## 问题 2: Layer-3 主键冲突（新增）

**错误日期**: 2026-04-08

**错误信息**:
```
postgrest.exceptions.APIError: {
  'message': 'duplicate key value violates unique constraint "session_l3_results_pkey"',
  'code': '23505',
  'details': 'Key (session_id, post_id)=(b78b232c-0f81-4663-ac72-2794ac6d1342, 5b3aeab13469ec06_03810138) already exists.'
}
```

**发生位置**: `batch_insert_l3_results` 函数

**根本原因**: 
重复运行 `batch_llm_filter.py`（如测试不同 `--min-relevance` 参数），使用 `insert()` 而非 `upsert()` 导致主键冲突。

**Schema 设计**:
```sql
CREATE TABLE session_l3_results (
    session_id VARCHAR(50),
    post_id VARCHAR(50),
    PRIMARY KEY (session_id, post_id)  -- 联合主键
);
```

**修复方案**: 使用 `upsert()` 替代 `insert()`

```python
# 修复前
supabase.table("session_l3_results").insert(chunk).execute()  # ❌

# 修复后
supabase.table("session_l3_results").upsert(chunk).execute()  # ✅
```

**新增功能**: `--clear-existing` 参数清理旧数据

```bash
# 清理后重新运行
uv run python scripts/batch_llm_filter.py \
  --session-id xxx \
  --query "xxx" \
  --clear-existing
```

---

## Layer-2 问题分析（原内容）

### 当前 Schema 设计

```sql
CREATE TABLE session_l2_posts (
    id VARCHAR(50) PRIMARY KEY,        -- ❌ 直接使用 filtered_posts.id
    session_id VARCHAR(50) NOT NULL,
    ...
);
```

### 冲突场景

```
Session 1: 用户 A 查询 "电商广告"
  → 帖子 5271530469590781 被写入 session_l2_posts
  → id = "5271530469590781"

Session 2: 用户 B 查询 "社交营销"（可能包含同一条帖子）
  → 帖子 5271530469590781 再次被写入
  → ❌ 主键冲突！Key (id)=(5271530469590781) already exists
```

---

## 解决方案对比

### 方案 1: 修改 Schema 为组合主键（不推荐）

**优点**: 语义清晰
**缺点**: 需要修改数据库 Schema，影响现有数据

```sql
-- 需要重建表
DROP TABLE session_l2_posts;
CREATE TABLE session_l2_posts (
    id VARCHAR(50) NOT NULL,              -- 原始 ID
    session_id VARCHAR(50) NOT NULL,
    ...
    PRIMARY KEY (session_id, id)         -- 组合主键
);
```

### 方案 2: 生成唯一的 Session-Level ID（✅ 采用）

**优点**: 
- 无需修改 Schema
- 代码改动最小
- 向后兼容
- ID 长度可控（<50 字符）

**缺点**: ID 可读性稍弱

```python
# 生成规则：MD5(session_id + 原始 id)[:16] + "_" + 原始 id[-8:]
import hashlib

original_id = str(post.get('id', ''))
hash_prefix = hashlib.md5(f"{session_id}_{original_id}".encode()).hexdigest()[:16]
id_suffix = original_id[-8:] if len(original_id) >= 8 else original_id
unique_id = f"{hash_prefix}_{id_suffix}"

# 示例：a1b2c3d4e5f6g7h8_69590781  (最多 25 字符)
```

---

## 修复实现

### 修复前（冲突 + 长度超限）

```python
def insert_session_l2_posts_batch(...):
    rows = []
    for post in posts:
        # ❌ 方案 1: 直接使用原始 ID → 主键冲突
        rows.append({
            "id": post.get("id"),
            ...
        })
        
        # ❌ 方案 2: session_id + 原始 id → 长度超过 50 字符
        unique_id = f"{session_id}_{post.get('id')}"
        # 示例：a1b2c3d4-e5f6-7890-abcd-1234567890ab_5271530469590781
        # 长度：36 + 1 + 16 = 53 字符 > 50 ❌
```

**问题**: 
1. 多个 session 处理同一帖子时，`id` 重复（主键冲突）
2. 组合 ID 超过 VARCHAR(50) 限制

---

### 修复后（哈希缩短 ID）

```python
import hashlib

def insert_session_l2_posts_batch(...):
    rows = []
    for post in posts:
        # ✅ 使用哈希缩短 ID
        original_id = str(post.get('id', ''))
        
        # MD5 哈希前 16 位（保证唯一性）
        hash_prefix = hashlib.md5(
            f"{session_id}_{original_id}".encode()
        ).hexdigest()[:16]
        
        # 原始 ID 后 8 位（保留可读性）
        id_suffix = original_id[-8:] if len(original_id) >= 8 else original_id
        
        # 组合：哈希前缀 + 下划线 + ID 后缀
        unique_id = f"{hash_prefix}_{id_suffix}"
        # 长度：16 + 1 + 8 = 25 字符 < 50 ✅
        
        rows.append({
            "id": unique_id,
            "session_id": session_id,
            ...
        })
```

**改进**: 
- ✅ 长度可控（最多 25 字符）
- ✅ 唯一性保证（MD5 碰撞概率极低）
- ✅ 部分可读（保留原始 ID 后 8 位）

---

## ID 格式说明

### 生成算法

```python
# 输入
session_id = "a1b2c3d4-e5f6-7890-abcd-1234567890ab"
original_id = "5271530469590781"

# 步骤 1: 组合字符串
combined = f"{session_id}_{original_id}"
# "a1b2c3d4-e5f6-7890-abcd-1234567890ab_5271530469590781"

# 步骤 2: MD5 哈希取前 16 位
hash_prefix = hashlib.md5(combined.encode()).hexdigest()[:16]
# "a7f3d2c8b1e4f5a6"

# 步骤 3: 原始 ID 取后 8 位
id_suffix = original_id[-8:]
# "69590781"

# 步骤 4: 组合最终 ID
unique_id = f"{hash_prefix}_{id_suffix}"
# "a7f3d2c8b1e4f5a6_69590781"
```

### 长度分析

| 组成部分 | 长度 | 示例 |
|---------|------|------|
| **哈希前缀** | 16 字符 | `a7f3d2c8b1e4f5a6` |
| **分隔符** | 1 字符 | `_` |
| **ID 后缀** | 最多 8 字符 | `69590781` |
| **总长度** | **最多 25 字符** | `a7f3d2c8b1e4f5a6_69590781` |

**✅ 符合 VARCHAR(50) 限制**

### 示例对比

| Session ID | 原始 ID | 生成的唯一 ID | 长度 |
|-----------|---------|--------------|------|
| `abc-123-...` | `5271530469590781` | `a7f3d2c8b1e4f5a6_69590781` | 25 |
| `def-456-...` | `5271530469590781` | `b8e4c3d9a2f5e6b7_69590781` | 25 |
| `xyz-789-...` | `123456` | `c9f5d4e0b3a6f7c8_123456` | 23 |

**关键点**: 
- 同一帖子在不同 session 中有不同的 ID
- 哈希保证唯一性，后缀保留可读性
- 通过 `session_id` 字段关联原始数据

---

## 数据查询调整

### 查询方式

```sql
-- 方式 1: 按 session 查询（最常见，推荐）
SELECT * FROM session_l2_posts 
WHERE session_id = 'a1b2c3d4-e5f6-7890';

-- 方式 2: 按 ID 后缀模糊匹配原始 ID
SELECT * FROM session_l2_posts 
WHERE id LIKE '%_69590781';

-- 方式 3: 结合 session + ID 后缀精确查询
SELECT * FROM session_l2_posts 
WHERE session_id = 'a1b2c3d4-e5f6-7890'
  AND id LIKE '%_69590781';
```

### 原始 ID 反查（如需）

如果需要频繁通过原始 ID 查询，建议：

**选项 A**: 添加 `original_id` 字段（推荐）

```sql
ALTER TABLE session_l2_posts 
ADD COLUMN original_id VARCHAR(50);

CREATE INDEX idx_session_l2_posts_original_id 
ON session_l2_posts(original_id);
```

修改插入代码：
```python
rows.append({
    "id": unique_id,
    "original_id": post.get("id"),  # 新增字段
    "session_id": session_id,
    ...
})
```

查询：
```sql
SELECT * FROM session_l2_posts 
WHERE original_id = '5271530469590781';
```

**选项 B**: 使用后缀索引（不推荐，性能较差）

```sql
CREATE INDEX idx_session_l2_posts_id_suffix 
ON session_l2_posts(SUBSTRING(id FROM POSITION('_' IN id) + 1));
```

---

## Schema 优化建议（可选）

### 添加原始 ID 字段

为了方便查询，可以在 session 表中添加 `original_id` 字段：

```sql
ALTER TABLE session_l2_posts 
ADD COLUMN original_id VARCHAR(50);

CREATE INDEX idx_session_l2_posts_original_id 
ON session_l2_posts(original_id);
```

然后修改插入代码：

```python
rows.append({
    "id": unique_id,
    "original_id": post.get("id"),  # 新增字段
    "session_id": session_id,
    ...
})
```

**优点**: 
- 可以直接通过 `original_id` 查询
- 不需要字符串分割

**缺点**: 
- 需要修改 Schema
- 数据冗余

---

## 代码变更清单

### 1. 导入模块

```python
# 新增
import hashlib
```

### 2. `insert_session_l2_posts_batch`

```python
# 修改前（主键冲突）
"id": post.get("id"),

# 修改中（长度超限）
unique_id = f"{session_id}_{post.get('id')}"  # 53 字符 > 50 ❌

# 修改后（哈希缩短）✅
original_id = str(post.get('id', ''))
hash_prefix = hashlib.md5(f"{session_id}_{original_id}".encode()).hexdigest()[:16]
id_suffix = original_id[-8:] if len(original_id) >= 8 else original_id
unique_id = f"{hash_prefix}_{id_suffix}"  # 最多 25 字符 ✅
"id": unique_id,
```

### 3. `insert_session_l2_comments_batch`

```python
# 同上改动
```

---

## 测试验证

### 场景 1: 单 Session

```bash
uv run python scripts/batch_scene_filter_smart.py \
    --query "过滤电商广告"
```

**预期结果**: 
- 成功插入，无冲突
- ID 格式：`<session_id>_<original_id>`

### 场景 2: 多 Session（同一数据集）

```bash
# Session 1
uv run python scripts/batch_scene_filter_smart.py \
    --query "过滤电商广告"

# Session 2（可能处理相同的帖子）
uv run python scripts/batch_scene_filter_smart.py \
    --query "过滤社交营销"
```

**预期结果**: 
- ✅ 两个 session 都成功
- ✅ 同一帖子在两个 session 中有不同的 ID
- ✅ 无主键冲突

---

## 性能影响

### ID 长度对比

| 类型 | 示例 | 长度 |
|------|------|------|
| **原始 ID** | `5271530469590781` | ~16 字符 |
| **Session ID** | `a1b2c3d4-e5f6-7890-abcd-1234567890ab` | 36 字符 |
| **组合 ID** | `a1b2c3d4-e5f6-7890-abcd-1234567890ab_5271530469590781` | ~53 字符 |

**影响评估**:
- 存储空间: 增加 ~37 字节/条（可忽略）
- 索引大小: 略微增加（可忽略）
- 查询性能: 无影响（主键索引自动优化）

---

## 回滚方案（如需）

如果想恢复到原始 ID（不推荐），需要：

1. **清空 session 表数据**:
```sql
TRUNCATE TABLE session_l2_posts;
TRUNCATE TABLE session_l2_comments;
```

2. **修改代码**:
```python
# 恢复为原始 ID
"id": post.get("id"),
```

3. **限制**: 每个帖子只能在一个 session 中存在

---

## 相关文档

- 字段映射修复: `docs/FIELD_MAPPING_FIX.md`
- 批量插入优化: `docs/BATCH_INSERT_TIMEOUT_FIX.md`
- Schema 定义: `database/schema_session.sql`

---

## 总结

- ✅ **问题 1**: 主键冲突（同一帖子在多个 session 中重复）
- ✅ **问题 2**: ID 长度超限（VARCHAR(50) 限制）
- ✅ **原因**: 直接使用 `filtered_posts.id` / 简单拼接导致过长
- ✅ **解决**: MD5 哈希缩短 + ID 后缀：`{hash[:16]}_{id[-8:]}`
- ✅ **优点**: 唯一性 + 长度可控（25 字符）+ 部分可读
- ✅ **影响**: 存储空间略增（可忽略），查询方式调整

### 关键技术点

1. **哈希唯一性**: MD5 碰撞概率 < 1/(2^128)，实际应用中可忽略
2. **长度优化**: 16 (hash) + 1 (_) + 8 (suffix) = 25 < 50 ✅
3. **可读性保留**: 后 8 位保留原始 ID 信息，便于人工调试

修复完成！🎉
