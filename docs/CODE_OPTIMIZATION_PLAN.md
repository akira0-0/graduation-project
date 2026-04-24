# 代码优化计划

## 📊 当前问题分析

经过代码审查，发现以下可优化的地方：

### 1. 重复的数据库读取逻辑 🔴

**问题**：`/api/filter/complete` 和 `/api/filter/auto` 中有大量重复的数据库读取代码

**位置**：
- `filter_engine/api.py` Line 1347-1365 (complete_filter)
- `filter_engine/api.py` Line 1752-1775 (auto_filter)

**重复代码**：
```python
# 两处都有相同的分页读取逻辑
query_builder = supabase.table("filtered_posts").select("*")
if request.platform:
    query_builder = query_builder.eq("platform", request.platform)

all_posts = []
page_size = 1000
offset = 0

while len(all_posts) < request.max_posts:
    resp = query_builder.range(offset, offset + page_size - 1).execute()
    data = resp.data or []
    if not data:
        break
    all_posts.extend(data)
    offset += page_size
    if len(data) < page_size:
        break
```

**优化方案**：提取为公共函数

---

### 2. 重复的 Layer-2 过滤逻辑 🔴

**问题**：三个 API 中都有相似的 Layer-2 场景匹配和规则应用

**位置**：
- `filter_engine/api.py` Line 1375-1395 (complete_filter)
- `filter_engine/api.py` Line 1810-1830 (auto_filter)
- `filter_engine/api.py` Line 1020-1065 (three_layer_filter)

**重复代码**：
```python
match_result = await matcher.match(request.query, force_scenario=...)
post_contents = [...]
pass_flags, _ = apply_rules_to_contents(matcher, post_contents, ...)
passed_posts = [p for p, flag in zip(all_posts, pass_flags) if flag]
```

**优化方案**：提取为 `execute_layer2_filter()` 函数

---

### 3. 重复的 Layer-3 过滤逻辑 🔴

**问题**：Layer-3 相关性过滤代码几乎完全重复

**位置**：
- `filter_engine/api.py` Line 1400-1467 (complete_filter)
- `filter_engine/api.py` Line 1910-1980 (auto_filter)

**重复代码**：
```python
relevance_map = {"high": RelevanceLevel.HIGH, ...}
min_rel = relevance_map.get(request.min_relevance, ...)

post_texts = [f"{p.get('title') or ''} {p.get('content') or ''}".strip() ...]

rel_result = sf.relevance_filter.filter_by_relevance(
    query=request.query,
    texts=post_texts,
    min_relevance=min_rel,
    use_llm_for_uncertain=True,
    llm_only=request.llm_only,
)

# 处理结果逻辑也完全相同
```

**优化方案**：提取为 `execute_layer3_filter()` 函数

---

### 4. 冗余的 API 端点 🟡

**问题**：存在功能重叠的 API

| API | 功能 | 是否必要 |
|-----|------|---------|
| `/api/filter/complete` | 一站式过滤 | ✅ **保留**（主推） |
| `/api/filter/auto` | 两步式过滤 | ✅ **保留**（Session 管理） |
| `/api/filter/three-layer` | 三层过滤（手动内容） | ⚠️ **考虑废弃**（仅测试用） |
| `/api/smart-filter` | Layer-2 过滤 | ⚠️ **考虑废弃**（被 complete 替代） |
| `/api/filter/relevance` | Layer-3 过滤 | ⚠️ **考虑废弃**（被 complete 替代） |
| `/api/filter/smart-relevance` | 智能相关性 | ⚠️ **重复**（与 relevance 重复） |

**优化建议**：
- 保留核心 API：`/api/filter/complete` 和 `/api/filter/auto`
- 废弃或标记为 deprecated：测试用 API
- 合并重复功能的 API

---

### 5. Session 保存逻辑重复 🟡

**问题**：`complete_filter` 和 `auto_filter` 中有相似的 Session 保存代码

**位置**：
- `filter_engine/api.py` Line 1509-1555 (complete_filter 的 save_session 分支)
- `filter_engine/api.py` Line 2000-2100 (auto_filter 的 Session 保存)

**优化方案**：提取为 `save_session_to_database()` 函数

---

### 6. 评论读取逻辑重复 🟡

**问题**：两处都有相同的评论批量读取逻辑

**位置**：
- `filter_engine/api.py` Line 1472-1500
- `filter_engine/api.py` Line 1850-1880

**重复代码**：
```python
all_comments = []
batch_size = 100
for i in range(0, len(valid_post_ids), batch_size):
    chunk_ids = valid_post_ids[i:i + batch_size]
    resp = supabase.table("filtered_comments").select("*").in_("content_id", chunk_ids).execute()
    all_comments.extend(resp.data or [])

comments_by_post = {}
for comment in all_comments:
    content_id = comment.get("content_id")
    if content_id not in comments_by_post:
        comments_by_post[content_id] = []
    comments_by_post[content_id].append(comment)
```

**优化方案**：提取为 `fetch_comments_for_posts()` 函数

---

### 7. 性能统计代码重复 🟢

**问题**：多处有相似的性能统计和打印代码

**优化方案**：创建统一的性能监控装饰器或工具函数

---

## 🎯 优化方案

### 方案 A：提取公共函数（推荐）⭐

**优点**：
- ✅ 代码复用，减少维护成本
- ✅ 统一逻辑，避免不一致
- ✅ 易于测试和修改

**实施步骤**：

#### 1. 创建工具模块 `filter_engine/api_utils.py`

```python
"""API 公共工具函数"""
from typing import List, Dict, Tuple, Optional
import time


async def fetch_filtered_posts_from_db(
    supabase,
    platform: Optional[str] = None,
    max_posts: int = 500
) -> Tuple[List[dict], float]:
    """
    从数据库分页读取 filtered_posts
    
    Returns:
        (posts, elapsed_time)
    """
    start = time.time()
    
    query_builder = supabase.table("filtered_posts").select("*")
    if platform:
        query_builder = query_builder.eq("platform", platform)
    
    all_posts = []
    page_size = 1000
    offset = 0
    
    while len(all_posts) < max_posts:
        resp = query_builder.range(offset, offset + page_size - 1).execute()
        data = resp.data or []
        if not data:
            break
        all_posts.extend(data)
        offset += page_size
        if len(data) < page_size:
            break
    
    all_posts = all_posts[:max_posts]
    elapsed = time.time() - start
    
    return all_posts, elapsed


async def execute_layer2_filter(
    matcher,
    query: str,
    posts: List[dict],
    force_scenario: Optional[str] = None
) -> Tuple[List[dict], dict, float]:
    """
    执行 Layer-2 场景规则过滤
    
    Returns:
        (passed_posts, match_result, elapsed_time)
    """
    start = time.time()
    
    match_result = await matcher.match(query, force_scenario=force_scenario)
    
    post_contents = [
        f"{p.get('title') or ''} {p.get('content') or ''} {' '.join(p.get('tags') or [])}".strip()
        for p in posts
    ]
    
    from .api import apply_rules_to_contents
    pass_flags, _ = apply_rules_to_contents(
        matcher, post_contents, match_result.matched_rules, match_result.gap_rules
    )
    
    passed_posts = [p for p, flag in zip(posts, pass_flags) if flag]
    elapsed = time.time() - start
    
    return passed_posts, match_result, elapsed


async def execute_layer3_filter(
    sf,
    query: str,
    posts: List[dict],
    min_relevance: str = "medium",
    llm_only: bool = True,
    min_score: Optional[float] = None
) -> Tuple[List[dict], List[str], float]:
    """
    执行 Layer-3 相关性过滤
    
    Returns:
        (valid_posts_with_score, valid_post_ids, elapsed_time)
    """
    from .core.relevance_filter import RelevanceLevel
    start = time.time()
    
    relevance_map = {
        "high": RelevanceLevel.HIGH,
        "medium": RelevanceLevel.MEDIUM,
        "low": RelevanceLevel.LOW,
    }
    min_rel = relevance_map.get(min_relevance, RelevanceLevel.MEDIUM)
    
    post_texts = [
        f"{p.get('title') or ''} {p.get('content') or ''}".strip()
        for p in posts
    ]
    
    rel_result = sf.relevance_filter.filter_by_relevance(
        query=query,
        texts=post_texts,
        min_relevance=min_rel,
        use_llm_for_uncertain=True,
        llm_only=llm_only,
    )
    
    relevance_order = {
        RelevanceLevel.HIGH: 3,
        RelevanceLevel.MEDIUM: 2,
        RelevanceLevel.LOW: 1,
        RelevanceLevel.IRRELEVANT: 0,
    }
    min_order = relevance_order[min_rel]
    
    valid_posts_with_score = []
    valid_post_ids = []
    
    for post, res_dict in zip(posts, rel_result["results"]):
        score = float(res_dict.get("score", 0.0))
        level_str = res_dict.get("relevance", "irrelevant")
        level = RelevanceLevel(level_str) if level_str in [e.value for e in RelevanceLevel] else RelevanceLevel.IRRELEVANT
        
        if relevance_order[level] >= min_order:
            if min_score is None or score >= min_score:
                post_with_score = {
                    **post,
                    "relevance_score": round(score, 3),
                    "relevance_level": level_str,
                }
                valid_posts_with_score.append(post_with_score)
                valid_post_ids.append(post["id"])
    
    elapsed = time.time() - start
    return valid_posts_with_score, valid_post_ids, elapsed


async def fetch_comments_for_posts(
    supabase,
    post_ids: List[str]
) -> Tuple[Dict[str, List[dict]], int, float]:
    """
    批量读取帖子评论
    
    Returns:
        (comments_by_post, total_comments, elapsed_time)
    """
    start = time.time()
    
    all_comments = []
    batch_size = 100
    
    for i in range(0, len(post_ids), batch_size):
        chunk_ids = post_ids[i:i + batch_size]
        resp = supabase.table("filtered_comments").select("*").in_("content_id", chunk_ids).execute()
        all_comments.extend(resp.data or [])
    
    comments_by_post = {}
    for comment in all_comments:
        content_id = comment.get("content_id")
        if content_id not in comments_by_post:
            comments_by_post[content_id] = []
        comments_by_post[content_id].append(comment)
    
    elapsed = time.time() - start
    return comments_by_post, len(all_comments), elapsed


async def save_session_to_database(
    supabase,
    session_id: str,
    query: str,
    scenario: str,
    stats: dict,
    l2_posts: List[dict],
    l3_posts: List[dict]
) -> float:
    """
    保存 Session 到数据库（3个表）
    
    Returns:
        elapsed_time
    """
    from datetime import datetime, timezone
    start = time.time()
    
    # 保存元数据
    metadata_row = {
        "session_id": session_id,
        "query": query,
        "scenario": scenario,
        "l1_total_posts": stats.get("l1_total_posts", 0),
        "l2_passed_posts": stats.get("l2_passed_posts", 0),
        "l3_passed_posts": stats.get("l3_passed_posts", 0),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase.table("session_metadata").insert(metadata_row).execute()
    
    # 保存 Layer-2 结果
    if l2_posts:
        l2_rows = []
        for post in l2_posts:
            l2_rows.append({
                "session_id": session_id,
                "post_id": post["id"],
                "title": post.get("title"),
                "content": post.get("content"),
                "platform": post.get("platform"),
            })
        
        batch_size = 100
        for i in range(0, len(l2_rows), batch_size):
            chunk = l2_rows[i:i + batch_size]
            supabase.table("session_l2_results").insert(chunk).execute()
    
    # 保存 Layer-3 结果
    if l3_posts:
        l3_rows = []
        for post in l3_posts:
            l3_rows.append({
                "session_id": session_id,
                "post_id": post["id"],
                "relevance_score": post.get("relevance_score"),
                "relevance_level": post.get("relevance_level"),
            })
        
        batch_size = 100
        for i in range(0, len(l3_rows), batch_size):
            chunk = l3_rows[i:i + batch_size]
            supabase.table("session_l3_results").insert(chunk).execute()
    
    elapsed = time.time() - start
    return elapsed
```

#### 2. 重构 `complete_filter` API

```python
@app.post("/api/filter/complete", response_model=CompleteFilterResponse, tags=["一站式过滤"])
async def complete_filter(request: CompleteFilterRequest):
    import time
    import uuid
    from datetime import datetime
    from .api_utils import (
        fetch_filtered_posts_from_db,
        execute_layer2_filter,
        execute_layer3_filter,
        fetch_comments_for_posts,
        save_session_to_database
    )
    
    start_time = time.time()
    session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    perf = {"layer1": 0.0, "layer2": 0.0, "layer3": 0.0, "fetch_results": 0.0, "save_session": 0.0, "total": 0.0}
    stats = {"l1_total_posts": 0, "l2_passed_posts": 0, "l3_passed_posts": 0, "final_returned": 0}
    
    try:
        supabase = get_supabase()
        matcher = get_smart_matcher()
        sf = get_smart_filter()
        
        # Step 1: 读取 Layer-1 数据（使用公共函数）
        all_posts, perf["layer1"] = await fetch_filtered_posts_from_db(
            supabase, request.platform, request.max_posts
        )
        stats["l1_total_posts"] = len(all_posts)
        
        if stats["l1_total_posts"] == 0:
            raise HTTPException(status_code=404, detail="No posts found")
        
        # Step 2: Layer-2 过滤（使用公共函数）
        passed_posts, match_result, perf["layer2"] = await execute_layer2_filter(
            matcher, request.query, all_posts, request.force_scenario
        )
        stats["l2_passed_posts"] = len(passed_posts)
        
        if stats["l2_passed_posts"] == 0:
            perf["total"] = time.time() - start_time
            return CompleteFilterResponse(
                query=request.query, session_id=session_id,
                stats=stats, posts=[], performance=perf,
                metadata={"early_stop": "layer2"}
            )
        
        # Step 3: Layer-3 过滤（使用公共函数）
        valid_posts_with_score, valid_post_ids, perf["layer3"] = await execute_layer3_filter(
            sf, request.query, passed_posts, request.min_relevance, request.llm_only, request.min_score
        )
        stats["l3_passed_posts"] = len(valid_posts_with_score)
        
        # Step 4: 读取评论（使用公共函数）
        if request.include_comments and valid_post_ids:
            comments_by_post, total_comments, perf["fetch_results"] = await fetch_comments_for_posts(
                supabase, valid_post_ids
            )
            for post in valid_posts_with_score:
                post["comments"] = comments_by_post.get(post["id"], [])
        else:
            for post in valid_posts_with_score:
                post["comments"] = []
        
        # Step 5: 排序和限制
        valid_posts_with_score.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        final_posts = valid_posts_with_score[:request.limit]
        stats["final_returned"] = len(final_posts)
        
        # Step 6: 保存 Session（可选，使用公共函数）
        if request.save_session:
            perf["save_session"] = await save_session_to_database(
                supabase, session_id, request.query, match_result.detected_scenario,
                stats, passed_posts, valid_posts_with_score
            )
        
        perf["total"] = time.time() - start_time
        
        return CompleteFilterResponse(
            query=request.query,
            session_id=session_id,
            stats=stats,
            posts=final_posts,
            performance=perf,
            metadata={
                "scenario": match_result.detected_scenario,
                "min_relevance": request.min_relevance,
                "platform": request.platform,
                "session_saved": request.save_session,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"\n❌ 一站式过滤出错: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Complete filter failed: {str(e)}")
```

**代码量对比**：
- 原代码：~300 行
- 优化后：~80 行（减少 73%）

---

### 方案 B：废弃冗余 API

**建议废弃的 API**：

1. **`/api/filter/three-layer`** 
   - 原因：被 `/api/filter/complete` 替代
   - 迁移：用户改用 `/api/filter/complete`

2. **`/api/smart-filter`**
   - 原因：功能被整合到主 API
   - 保留：如果有独立使用场景可保留

3. **`/api/filter/smart-relevance`** 和 `/api/filter/relevance`**
   - 原因：重复功能
   - 保留：合并为一个 `/api/filter/relevance`

**废弃步骤**：
1. 标记为 `deprecated` (添加 `deprecated=True` 标签)
2. 在文档中说明替代方案
3. 1-2 个版本后完全移除

---

## 📈 预期效果

### 代码量减少

| 模块 | 原代码 | 优化后 | 减少 |
|------|--------|--------|------|
| `filter_engine/api.py` | 2731 行 | ~1800 行 | **-34%** |
| 公共函数提取 | 0 行 | 300 行 | +300 行 |
| **总计** | 2731 行 | ~2100 行 | **-23%** |

### 维护成本降低

- ✅ 逻辑统一：修改一处即可
- ✅ 测试简化：公共函数独立测试
- ✅ Bug 减少：避免多处不一致

### 性能提升

- 无明显性能影响（仅重构，逻辑不变）

---

## 🚀 实施计划

### 阶段 1：提取公共函数（1-2天）

- [x] 创建 `filter_engine/api_utils.py`
- [ ] 实现公共函数
- [ ] 编写单元测试

### 阶段 2：重构主 API（2-3天）

- [ ] 重构 `/api/filter/complete`
- [ ] 重构 `/api/filter/auto`
- [ ] 测试功能完整性

### 阶段 3：清理冗余 API（1天）

- [ ] 标记废弃 API
- [ ] 更新文档
- [ ] 提供迁移指南

### 阶段 4：测试验证（1天）

- [ ] 运行所有测试脚本
- [ ] 性能对比测试
- [ ] 回归测试

---

## ⚠️ 风险评估

### 低风险

- ✅ 提取公共函数（不改变逻辑）
- ✅ 代码复用（有测试覆盖）

### 中风险

- ⚠️ API 重构（需要充分测试）
- ⚠️ 废弃旧 API（需要通知用户）

### 降低风险措施

1. 充分的单元测试
2. 保留旧 API 一段时间
3. 提供详细的迁移文档
4. 分阶段实施，每阶段测试

---

## 🎯 下一步

请确认优化方案，我可以立即开始：

1. **方案 A**：提取公共函数（推荐）
2. **方案 B**：废弃冗余 API
3. **两者都做**：完整优化

**推荐顺序**：
1. 先实施方案 A（提取公共函数）
2. 测试通过后实施方案 B（废弃冗余 API）

需要我开始实施吗？
