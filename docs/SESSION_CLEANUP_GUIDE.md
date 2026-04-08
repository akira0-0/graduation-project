# Session 数据清理指南

## 问题

由于多次运行 Layer-2 脚本，`session_l2_posts` 和 `session_l2_comments` 表累积了大量重复数据。

## 解决方案

### 方案 1: 独立清理脚本（推荐）

使用 `cleanup_sessions.py` 脚本手动清理：

#### 1.1 清理 2 小时前的旧 session

```bash
uv run python scripts/cleanup_sessions.py --older-than 2
```

**适用场景**: 定期维护，自动清理过期数据

#### 1.2 清理指定 session

```bash
uv run python scripts/cleanup_sessions.py --session-id abc-123-def-456
```

**适用场景**: 删除特定的测试 session

#### 1.3 清理所有 session（危险操作）

```bash
uv run python scripts/cleanup_sessions.py --all --confirm
```

**适用场景**: 完全重置，清空所有 session 数据

⚠️ **警告**: 此操作会删除所有 session 数据，包括 Layer-3 结果！

#### 1.4 Dry-run 预览

```bash
# 仅查看待清理的 session，不实际删除
uv run python scripts/cleanup_sessions.py --older-than 2 --dry-run
```

**输出示例**:
```
================================================================================
🧹 Session 数据清理工具
================================================================================
🔍 模式: 清理 2 小时前的 session

📊 待清理 session 数量: 15
────────────────────────────────────────────────────────────────────────────────

1. Session: b78b232c-0f81-46...
   创建时间: 2026-04-08T10:30:00.000Z
   Query: 丽江有什么好玩的...
   数据: L2 帖子=500, L2 评论=1200, L3 帖子=150

2. Session: a1b2c3d4-5e6f-78...
   创建时间: 2026-04-08T09:15:00.000Z
   Query: 成都美食推荐...
   数据: L2 帖子=300, L2 评论=800, L3 帖子=80

... (还有 13 个)

🧪 DRY-RUN 模式：仅查看，不实际删除
   如需实际删除，请移除 --dry-run 参数
```

---

### 方案 2: Layer-2 脚本自动清理

在运行 Layer-2 时自动清理旧数据：

```bash
# 运行前自动清理 2 小时前的 session
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江有什么好玩的" \
  --auto-cleanup

# 自定义清理时间（如 6 小时）
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江有什么好玩的" \
  --auto-cleanup \
  --cleanup-hours 6
```

**优势**:
- ✅ 自动维护，无需手动清理
- ✅ 在过滤前清理，避免数据累积

**新增参数**:
- `--auto-cleanup`: 启用自动清理
- `--cleanup-hours <小时数>`: 清理超过指定小时数的 session（默认 2）

---

## 清理策略

### 推荐策略 A: 定期手动清理

```bash
# 每天运行一次，清理 24 小时前的数据
uv run python scripts/cleanup_sessions.py --older-than 24
```

**优势**: 保留当天的调试数据，定期清理历史数据

### 推荐策略 B: 每次运行前自动清理

```bash
# 在 Layer-2 脚本中添加 --auto-cleanup
uv run python scripts/batch_scene_filter_smart.py \
  --query "xxx" \
  --auto-cleanup \
  --cleanup-hours 2
```

**优势**: 无需手动维护，始终保持数据清洁

### 推荐策略 C: 混合策略

- **日常使用**: 启用 `--auto-cleanup` 自动清理 2 小时前的数据
- **周期维护**: 每周手动运行 `--older-than 168` 清理 1 周前的数据
- **紧急清理**: 使用 `--all --confirm` 完全重置

---

## 清理范围

清理操作会删除以下数据：

| 表名 | 说明 | 数据量估计 |
|------|------|-----------|
| `session_l2_posts` | Layer-2 通过的帖子 | 每 session 100-1000 条 |
| `session_l2_comments` | Layer-2 通过的评论 | 每 session 200-2000 条 |
| `session_l3_results` | Layer-3 最终结果（帖子+评论嵌套） | 每 session 50-500 条 |
| `session_metadata` | Session 元数据 | 每 session 1 条 |

**总计**: 每个 session 约 **350-3500 条记录**

---

## 常见问题

### Q1: 清理会影响正在使用的 session 吗？

**A**: 不会。清理仅针对：
- 指定时间前创建的 session（如 `--older-than 2` 只清理 2 小时前的）
- 显式指定的 session_id
- 使用 `--all` 时需要 `--confirm` 确认

### Q2: 如何查看当前有多少 session？

**A**: 使用 Dry-run 模式：
```bash
uv run python scripts/cleanup_sessions.py --older-than 0 --dry-run
```

这会列出所有 session（`--older-than 0` 表示包含所有）

### Q3: 清理后能恢复吗？

**A**: **不能**。删除操作是永久的，建议：
1. 先使用 `--dry-run` 预览
2. 确认无误后再执行实际删除

### Q4: 如何保留特定 session？

**A**: 使用时间过滤，例如：
- 保留最近 24 小时的数据：`--older-than 24`
- 手动清理时跳过特定 session

### Q5: 清理会很慢吗？

**A**: 速度取决于数据量：
- 每个 session 约 **0.5-2 秒**
- 100 个 session 约 **1-3 分钟**

对于大量 session，脚本会显示进度。

---

## 脚本选项对比

| 特性 | `cleanup_sessions.py` | `batch_scene_filter_smart.py --auto-cleanup` |
|------|----------------------|-------------------------------------------|
| **使用场景** | 定期手动清理 | 运行 Layer-2 时自动清理 |
| **灵活性** | ⭐⭐⭐⭐⭐ (可清理特定 session) | ⭐⭐⭐ (仅清理旧 session) |
| **自动化** | ❌ 需手动运行 | ✅ 自动清理 |
| **适用场景** | 维护、调试、完全重置 | 日常使用 |

---

## 最佳实践

### 1. 开发/测试阶段

```bash
# 每次运行前清理 1 小时前的数据
uv run python scripts/batch_scene_filter_smart.py \
  --query "xxx" \
  --auto-cleanup \
  --cleanup-hours 1
```

### 2. 生产环境

```bash
# 运行前清理 6 小时前的数据
uv run python scripts/batch_scene_filter_smart.py \
  --query "xxx" \
  --auto-cleanup \
  --cleanup-hours 6

# 每天定期清理 24 小时前的数据
# 可配置 cron job 或 Windows 任务计划
uv run python scripts/cleanup_sessions.py --older-than 24
```

### 3. 完全重置（谨慎）

```bash
# Step 1: 预览所有 session
uv run python scripts/cleanup_sessions.py --all --dry-run

# Step 2: 确认后清理
uv run python scripts/cleanup_sessions.py --all --confirm
```

---

## 示例输出

### 清理成功示例

```
================================================================================
🧹 Session 数据清理工具
================================================================================
🔍 模式: 清理 2 小时前的 session

📊 待清理 session 数量: 5
────────────────────────────────────────────────────────────────────────────────

🗑️  开始清理...

  [1/5] 清理 session: b78b232c-0f81-46...
     - session_l2_posts: 500 条
     - session_l2_comments: 1200 条
     - session_l3_results: 150 条
     - session_metadata: 1 条

  [2/5] 清理 session: a1b2c3d4-5e6f-78...
     - session_l2_posts: 300 条
     - session_l2_comments: 800 条
     - session_l3_results: 80 条
     - session_metadata: 1 条

... (继续)

================================================================================
✅ 清理完成！
================================================================================
   清理 session 数: 5
   删除 L2 帖子: 2500 条
   删除 L2 评论: 6000 条
   删除 L3 结果: 800 条
```

---

## 总结

**推荐使用方式**:
```bash
# 日常使用（自动清理）
uv run python scripts/batch_scene_filter_smart.py \
  --query "xxx" \
  --auto-cleanup

# 定期维护（手动清理）
uv run python scripts/cleanup_sessions.py --older-than 24

# 紧急清理（完全重置）
uv run python scripts/cleanup_sessions.py --all --confirm
```

**关键要点**:
1. ✅ 使用 `--auto-cleanup` 避免数据累积
2. ✅ 定期手动清理历史数据
3. ✅ 使用 `--dry-run` 预览后再删除
4. ⚠️ 删除操作不可恢复，谨慎使用 `--all`

---

**更新日期**: 2026年4月8日  
**版本**: v1.0
