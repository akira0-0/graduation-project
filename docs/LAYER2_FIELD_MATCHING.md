# Layer-2 Smart 版规则匹配字段说明

## 📅 最后更新
2026-04-08

---

## 🎯 规则匹配机制

### 核心问题
**"规则关键词与数据库哪些字段进行比对？"**

### 回答
Layer-2 规则匹配时，会综合多个字段的内容：

---

## 📝 帖子（Posts）匹配字段

### 匹配字段组合
```
帖子匹配文本 = title + content + tags
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `title` | String | 帖子标题 | "丽江超值民宿推荐" |
| `content` | Text | 帖子正文 | "这次去丽江住的民宿性价比超高..." |
| `tags` | List/JSON | 标签列表 | `["旅游", "丽江", "民宿"]` |

### 代码实现

```python
# 综合 title + content + tags 作为匹配内容
post_contents = []
for p in all_posts:
    parts = []
    
    # 1. 添加标题
    if p.get("title"):
        parts.append(p.get("title"))
    
    # 2. 添加正文
    if p.get("content"):
        parts.append(p.get("content"))
    
    # 3. 添加标签
    if p.get("tags"):
        tags = p.get("tags")
        if isinstance(tags, list):
            parts.extend(tags)  # ["旅游", "丽江"]
        elif isinstance(tags, str):
            # 尝试解析 JSON
            tags_list = json.loads(tags)
            parts.extend(tags_list)
    
    # 用空格连接所有部分
    post_contents.append(" ".join(parts))
```

### 匹配示例

**规则**: Select 关键词 `["丽江"]`

**帖子数据**:
```json
{
  "id": "12345",
  "title": "云南旅游攻略",
  "content": "这次去丽江玩了3天...",
  "tags": ["旅游", "云南", "丽江"]
}
```

**匹配文本**:
```
"云南旅游攻略 这次去丽江玩了3天... 旅游 云南 丽江"
```

**匹配结果**:
- ✅ 在 `content` 中找到 "丽江" → 命中
- ✅ 在 `tags` 中找到 "丽江" → 命中
- 结果: **通过 select 规则，保留此帖子**

---

## 💬 评论（Comments）匹配字段

### 匹配字段
```
评论匹配文本 = content
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `content` | Text | 评论正文（唯一字段）|

**注意**: 评论表通常只有 `content` 字段，无 `title` 和 `tags`

### 代码实现

```python
# 评论只有 content 字段
comment_contents = [c.get("content", "") for c in all_comments]
```

### 匹配示例

**规则**: Filter 关键词 `["加微信", "私聊"]`

**评论数据**:
```json
{
  "id": "67890",
  "content": "想了解更多加微信xxx",
  "author_id": "user123"
}
```

**匹配文本**:
```
"想了解更多加微信xxx"
```

**匹配结果**:
- ✅ 在 `content` 中找到 "加微信" → 命中
- 结果: **被 filter 规则拦截**

---

## 🔍 规则匹配逻辑

### 关键词规则（keyword）

```python
# 小写不区分大小写匹配
text_lower = text.lower()
hit = any(str(kw).lower() in text_lower for kw in keywords)
```

**示例**:
- 规则: `["丽江"]`
- 文本: "云南旅游攻略 这次去**丽江**玩了3天... 旅游 云南 **丽江**"
- 匹配: `"丽江" in text_lower` → ✅ True

### 正则规则（regex）

```python
# 正则表达式匹配（不区分大小写）
import re
hit = re.search(pattern, text, re.IGNORECASE)
```

**示例**:
- 规则: `r"\d{11}"`（手机号）
- 文本: "联系我 13812345678"
- 匹配: `re.search(r"\d{11}", text)` → ✅ 匹配到 "13812345678"

---

## 📊 完整匹配流程

### 帖子过滤流程

```
1. 读取帖子数据
   ├── title: "丽江超值民宿推荐"
   ├── content: "这次去丽江住的民宿性价比超高..."
   └── tags: ["旅游", "丽江", "民宿"]

2. 组合匹配文本
   → "丽江超值民宿推荐 这次去丽江住的民宿性价比超高... 旅游 丽江 民宿"

3. LLM 思维链分析
   matched_rules: [旅游-住宿-民宿推荐 (select)]
   gap_rules: [旅游-性价比-关键词 (select): ["便宜", "实惠", "性价比"]]

4. 应用规则
   ✅ matched_rules: "民宿" in text → 命中
   ✅ gap_rules: "性价比" in text → 命中
   
5. 决策
   → 命中 select 规则 → 保留帖子 ✅
```

### 评论过滤流程

```
1. 读取评论数据
   └── content: "想了解更多加微信xxx"

2. 匹配文本（直接使用 content）
   → "想了解更多加微信xxx"

3. 复用帖子的规则
   matched_rules: [电商-引流-私信加V (filter)]
   gap_rules: []

4. 应用规则
   ✅ matched_rules: "加微信" in text → 命中

5. 决策
   → 命中 filter 规则 → 拦截评论 ❌
```

---

## 🎯 实际案例分析

### 案例 1: 旅游攻略筛选

**Query**: "保留丽江旅游相关的真实评价"

**LLM 生成规则**:
- Select: `["丽江", "旅游", "攻略", "景点"]`
- Filter: `["加微信", "私聊", "扫码"]`

**帖子 A**:
```json
{
  "title": "丽江3日游攻略",
  "content": "分享我的丽江旅游经历...",
  "tags": ["旅游", "丽江"]
}
```
**匹配文本**: "丽江3日游攻略 分享我的丽江旅游经历... 旅游 丽江"
- ✅ 命中 select: "丽江" → **保留**

**帖子 B**:
```json
{
  "title": "最全丽江旅游资讯",
  "content": "想去丽江的加微信xxx",
  "tags": ["旅游"]
}
```
**匹配文本**: "最全丽江旅游资讯 想去丽江的加微信xxx 旅游"
- ✅ 命中 select: "丽江"
- ❌ 同时命中 filter: "加微信" → **拦截**（filter 优先级更高）

**帖子 C**:
```json
{
  "title": "成都美食推荐",
  "content": "火锅串串太好吃了",
  "tags": ["美食", "成都"]
}
```
**匹配文本**: "成都美食推荐 火锅串串太好吃了 美食 成都"
- ❌ 未命中任何规则 → **默认通过**（但不是目标内容）

---

### 案例 2: 电商广告过滤

**Query**: "过滤电商评论中的广告"

**LLM 生成规则**:
- Filter: `["加微信", "私聊", "优惠券", "领取"]`

**评论 A**:
```json
{
  "content": "产品质量不错，值得购买"
}
```
**匹配文本**: "产品质量不错，值得购买"
- ❌ 未命中规则 → **默认通过**

**评论 B**:
```json
{
  "content": "想要优惠券的加微信xxx"
}
```
**匹配文本**: "想要优惠券的加微信xxx"
- ✅ 命中 filter: "优惠券"、"加微信" → **拦截**

---

## 💡 优化建议

### 1. **标题权重更高**
如果需要标题有更高权重，可以重复标题：
```python
parts = []
if p.get("title"):
    parts.append(p.get("title"))
    parts.append(p.get("title"))  # 重复一次，提高权重
if p.get("content"):
    parts.append(p.get("content"))
```

### 2. **添加作者昵称**
如果要过滤特定作者：
```python
if p.get("author_nickname"):
    parts.append(p.get("author_nickname"))
```

### 3. **添加 IP 归属地**
如果要按地域过滤：
```python
if p.get("author_ip_location"):
    parts.append(p.get("author_ip_location"))
```

### 4. **自定义字段组合**
可以添加 `--match-fields` 参数，让用户指定：
```bash
--match-fields title,content,tags,author_nickname
```

---

## 🔧 调试技巧

### 查看实际匹配文本

在代码中添加调试输出：
```python
# 调试：查看前 3 条帖子的匹配文本
if len(post_contents) > 0:
    print(f"\n🔍 匹配文本示例（前3条）:")
    for i, text in enumerate(post_contents[:3]):
        print(f"\n  [{i+1}] {text[:200]}...")  # 只显示前 200 字符
```

### 查看规则命中情况

在 `apply_rules_to_contents` 函数中添加：
```python
# 记录命中的具体关键词
if hit:
    print(f"    命中: {rule.name} - 关键词: {kw}")
```

---

## 📚 相关文档
- `docs/LAYER2_SMART_CRITICAL_BUG_FIX.md` - Bug 修复记录
- `docs/FILTER_WORKFLOW.md` - 完整过滤流程
- `database/schema_filtered.sql` - 数据表结构

---

**最后更新**: 2026-04-08  
**关键改进**: 帖子匹配改为 title + content + tags 综合匹配
