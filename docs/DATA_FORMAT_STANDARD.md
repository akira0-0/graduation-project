# 统一数据格式规范

## 平台数据统一格式 (v1.0)

所有平台的爬取数据应遵循以下统一格式，以便后续数据分析和处理。

---

## 1. 帖子/内容数据格式

```json
{
  "id": "唯一标识符",
  "platform": "平台名称 (xhs/weibo/douyin等)",
  "type": "内容类型 (video/image/text)",
  "url": "内容链接",
  "title": "标题（可选，截取前30-50字）",
  "content": "完整文本内容",
  "publish_time": "发布时间 (统一格式: YYYY-MM-DD HH:MM:SS)",
  "last_update_time": "最后更新时间 (统一格式: YYYY-MM-DD HH:MM:SS)",
  
  "author": {
    "id": "作者ID",
    "nickname": "作者昵称",
    "avatar": "作者头像URL",
    "is_verified": "是否认证 (boolean)",
    "ip_location": "IP归属地（可选）"
  },
  
  "media": {
    "images": ["图片URL列表"],
    "video_url": "视频URL（可选）"
  },
  
  "metrics": {
    "likes": "点赞数 (int)",
    "collects": "收藏数 (int)",
    "comments": "评论数 (int)",
    "shares": "分享/转发数 (int)"
  },
  
  "tags": ["标签1", "标签2"],
  "source_keyword": "搜索关键词（如果是搜索结果）",
  "task_id": "任务ID",
  "crawl_time": "爬取时间戳",
  "extra": {
    "平台特有字段": "值"
  }
}
```

---

## 2. 评论数据格式

```json
{
  "id": "评论唯一标识符",
  "content_id": "所属内容ID",
  "platform": "平台名称",
  "content": "评论文本",
  "publish_time": "发布时间 (统一格式: YYYY-MM-DD HH:MM:SS)",
  
  "author": {
    "id": "作者ID",
    "nickname": "作者昵称",
    "avatar": "作者头像URL（可选）",
    "ip_location": "IP归属地（可选）"
  },
  
  "metrics": {
    "likes": "点赞数 (int)",
    "sub_comments": "子评论数 (int, 可选)"
  },
  
  "parent_comment_id": "父评论ID（一级评论为null）",
  "root_comment_id": "根评论ID",
  "task_id": "任务ID",
  "crawl_time": "爬取时间戳"
}
```

---

## 3. 字段命名规范

| 原字段名 | 统一字段名 | 说明 |
|---------|-----------|------|
| note_id / mid / video_id | id | 内容唯一标识 |
| user_id | author.id | 作者ID |
| nickname / screen_name | author.nickname | 作者昵称 |
| desc / text | content | 内容文本 |
| liked_count / attitudes_count | metrics.likes | 点赞数 |
| collected_count | metrics.collects | 收藏数 |
| comment_count / comments_count | metrics.comments | 评论数 |
| share_count / reposts_count | metrics.shares | 分享数 |
| image_list / pics | media.images | 图片列表 |
| video_url | media.video_url | 视频URL |

---

## 4. 时间格式统一

所有时间字段统一为：`YYYY-MM-DD HH:MM:SS`

例如：`2026-01-12 14:30:45`

---

## 5. 平台标识

| 平台 | 标识符 |
|-----|--------|
| 小红书 | xhs |
| 微博 | weibo |
| 抖音 | douyin |
| B站 | bilibili |
| 知乎 | zhihu |

---

## 6. 数据验证规则

- `id`: 必填，字符串
- `platform`: 必填，枚举值
- `content`: 必填，字符串
- `publish_time`: 必填，符合格式
- `author.id`: 必填
- `author.nickname`: 必填
- `metrics.*`: 数值类型，默认0

