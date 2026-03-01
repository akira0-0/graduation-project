-- =============================================
-- 社交媒体数据采集系统 - 数据库表结构
-- 版本: 1.0
-- 日期: 2026-01-13
-- 说明: 根据统一数据格式设计的MySQL表结构
-- =============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS social_media_db 
DEFAULT CHARACTER SET utf8mb4 
DEFAULT COLLATE utf8mb4_unicode_ci;

USE social_media_db;

-- =============================================
-- 1. 帖子/内容表 (posts)
-- =============================================
DROP TABLE IF EXISTS posts;

CREATE TABLE posts (
    -- 主键和基础信息
    id VARCHAR(50) PRIMARY KEY COMMENT '内容唯一ID',
    platform VARCHAR(20) NOT NULL COMMENT '平台标识(xhs/weibo/douyin/bilibili/zhihu)',
    type VARCHAR(20) DEFAULT NULL COMMENT '内容类型(video/image/text)',
    url TEXT DEFAULT NULL COMMENT '内容链接',
    title VARCHAR(500) DEFAULT NULL COMMENT '标题',
    content TEXT DEFAULT NULL COMMENT '完整文本内容',
    
    -- 时间信息
    publish_time DATETIME DEFAULT NULL COMMENT '发布时间',
    last_update_time DATETIME DEFAULT NULL COMMENT '最后更新时间',
    
    -- 作者信息
    author_id VARCHAR(50) DEFAULT NULL COMMENT '作者ID',
    author_nickname VARCHAR(100) DEFAULT NULL COMMENT '作者昵称',
    author_avatar VARCHAR(500) DEFAULT NULL COMMENT '作者头像URL',
    author_is_verified BOOLEAN DEFAULT FALSE COMMENT '是否认证用户',
    author_ip_location VARCHAR(50) DEFAULT NULL COMMENT 'IP归属地',
    
    -- 媒体信息（JSON格式）
    media_images JSON DEFAULT NULL COMMENT '图片URL数组，格式: ["url1", "url2"]',
    media_video_url TEXT DEFAULT NULL COMMENT '视频URL',
    
    -- 互动数据（metrics）
    metrics_likes INT DEFAULT 0 COMMENT '点赞数',
    metrics_collects INT DEFAULT 0 COMMENT '收藏数',
    metrics_comments INT DEFAULT 0 COMMENT '评论数',
    metrics_shares INT DEFAULT 0 COMMENT '分享/转发数',
    
    -- 其他元数据
    tags JSON DEFAULT NULL COMMENT '标签数组，格式: ["tag1", "tag2"]',
    source_keyword VARCHAR(100) DEFAULT NULL COMMENT '搜索关键词（如果是搜索结果）',
    task_id VARCHAR(50) DEFAULT NULL COMMENT '任务ID',
    crawl_time BIGINT DEFAULT NULL COMMENT '爬取时间戳（Unix时间戳）',
    
    -- 扩展字段（平台特有数据）
    extra JSON DEFAULT NULL COMMENT '扩展字段，存储平台特有数据',
    
    -- 系统字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    -- 索引
    INDEX idx_platform (platform) COMMENT '平台索引',
    INDEX idx_author_id (author_id) COMMENT '作者ID索引',
    INDEX idx_publish_time (publish_time) COMMENT '发布时间索引',
    INDEX idx_source_keyword (source_keyword) COMMENT '搜索关键词索引',
    INDEX idx_task_id (task_id) COMMENT '任务ID索引',
    INDEX idx_crawl_time (crawl_time) COMMENT '爬取时间索引',
    INDEX idx_platform_author (platform, author_id) COMMENT '平台+作者组合索引',
    INDEX idx_platform_keyword (platform, source_keyword) COMMENT '平台+关键词组合索引'
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='帖子/内容数据表';


-- =============================================
-- 2. 评论表 (comments)
-- =============================================
DROP TABLE IF EXISTS comments;

CREATE TABLE comments (
    -- 主键和基础信息
    id VARCHAR(50) PRIMARY KEY COMMENT '评论唯一ID',
    content_id VARCHAR(50) NOT NULL COMMENT '所属内容ID（关联posts表）',
    platform VARCHAR(20) NOT NULL COMMENT '平台标识(xhs/weibo/douyin/bilibili/zhihu)',
    content TEXT DEFAULT NULL COMMENT '评论文本',
    publish_time DATETIME DEFAULT NULL COMMENT '发布时间',
    
    -- 作者信息
    author_id VARCHAR(50) DEFAULT NULL COMMENT '评论者ID',
    author_nickname VARCHAR(100) DEFAULT NULL COMMENT '评论者昵称',
    author_avatar VARCHAR(500) DEFAULT NULL COMMENT '评论者头像URL',
    author_ip_location VARCHAR(50) DEFAULT NULL COMMENT 'IP归属地',
    
    -- 互动数据
    metrics_likes INT DEFAULT 0 COMMENT '点赞数',
    metrics_sub_comments INT DEFAULT 0 COMMENT '子评论数量',
    
    -- 评论层级关系
    parent_comment_id VARCHAR(50) DEFAULT NULL COMMENT '父评论ID（一级评论为NULL）',
    root_comment_id VARCHAR(50) DEFAULT NULL COMMENT '根评论ID（始终指向顶层评论）',
    reply_to_user_id VARCHAR(50) DEFAULT NULL COMMENT '被回复的用户ID',
    reply_to_user_nickname VARCHAR(100) DEFAULT NULL COMMENT '被回复的用户昵称',
    comment_level INT DEFAULT 1 COMMENT '评论层级（1=一级，2=二级，3=三级...）',
    
    -- 其他元数据
    task_id VARCHAR(50) DEFAULT NULL COMMENT '任务ID',
    crawl_time BIGINT DEFAULT NULL COMMENT '爬取时间戳（Unix时间戳）',
    
    -- 扩展字段
    extra JSON DEFAULT NULL COMMENT '扩展字段，存储平台特有数据',
    
    -- 系统字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    -- 索引
    INDEX idx_content_id (content_id) COMMENT '内容ID索引',
    INDEX idx_platform (platform) COMMENT '平台索引',
    INDEX idx_author_id (author_id) COMMENT '评论者ID索引',
    INDEX idx_parent_comment_id (parent_comment_id) COMMENT '父评论ID索引',
    INDEX idx_root_comment_id (root_comment_id) COMMENT '根评论ID索引',
    INDEX idx_comment_level (comment_level) COMMENT '评论层级索引',
    INDEX idx_publish_time (publish_time) COMMENT '发布时间索引',
    INDEX idx_platform_content (platform, content_id) COMMENT '平台+内容组合索引',
    
    -- 外键约束（可选，根据需要启用）
    -- FOREIGN KEY (content_id) REFERENCES posts(id) ON DELETE CASCADE ON UPDATE CASCADE,
    
    -- 检查约束
    CONSTRAINT chk_comment_level CHECK (comment_level >= 1 AND comment_level <= 10)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评论数据表';


-- =============================================
-- 3. 作者/创作者表 (authors) - 可选
-- =============================================
DROP TABLE IF EXISTS authors;

CREATE TABLE authors (
    -- 主键
    id VARCHAR(50) PRIMARY KEY COMMENT '作者唯一ID',
    platform VARCHAR(20) NOT NULL COMMENT '平台标识',
    
    -- 基础信息
    nickname VARCHAR(100) DEFAULT NULL COMMENT '昵称',
    avatar VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
    bio TEXT DEFAULT NULL COMMENT '个人简介',
    is_verified BOOLEAN DEFAULT FALSE COMMENT '是否认证',
    
    -- 统计信息
    fans_count INT DEFAULT 0 COMMENT '粉丝数',
    follows_count INT DEFAULT 0 COMMENT '关注数',
    posts_count INT DEFAULT 0 COMMENT '发帖数',
    
    -- 其他信息
    ip_location VARCHAR(50) DEFAULT NULL COMMENT '常用IP归属地',
    
    -- 系统字段
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '首次发现时间',
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    
    -- 索引
    UNIQUE INDEX idx_platform_id (platform, id) COMMENT '平台+ID唯一索引',
    INDEX idx_nickname (nickname) COMMENT '昵称索引'
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作者/创作者信息表';


-- =============================================
-- 4. 任务表 (tasks) - 可选
-- =============================================
DROP TABLE IF EXISTS tasks;

CREATE TABLE tasks (
    -- 主键
    id VARCHAR(50) PRIMARY KEY COMMENT '任务ID',
    
    -- 任务信息
    platform VARCHAR(20) NOT NULL COMMENT '平台',
    task_type VARCHAR(20) DEFAULT NULL COMMENT '任务类型(search/detail/creator)',
    keywords JSON DEFAULT NULL COMMENT '搜索关键词数组',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '任务状态(pending/running/completed/failed)',
    
    -- 统计信息
    posts_count INT DEFAULT 0 COMMENT '采集帖子数',
    comments_count INT DEFAULT 0 COMMENT '采集评论数',
    
    -- 时间信息
    start_time DATETIME DEFAULT NULL COMMENT '开始时间',
    end_time DATETIME DEFAULT NULL COMMENT '结束时间',
    
    -- 系统字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX idx_platform (platform),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='爬取任务表';


-- =============================================
-- 5. 创建视图 - 便捷查询
-- =============================================

-- 帖子概览视图
CREATE OR REPLACE VIEW v_posts_overview AS
SELECT 
    p.id,
    p.platform,
    p.title,
    LEFT(p.content, 100) AS content_preview,
    p.author_nickname,
    p.publish_time,
    p.metrics_likes AS likes,
    p.metrics_comments AS comments,
    p.metrics_shares AS shares,
    p.source_keyword,
    p.created_at
FROM posts p
ORDER BY p.publish_time DESC;

-- 评论概览视图
CREATE OR REPLACE VIEW v_comments_overview AS
SELECT 
    c.id,
    c.content_id,
    c.platform,
    LEFT(c.content, 100) AS content_preview,
    c.author_nickname,
    c.comment_level,
    c.metrics_likes AS likes,
    c.publish_time,
    p.title AS post_title
FROM comments c
LEFT JOIN posts p ON c.content_id = p.id
ORDER BY c.publish_time DESC;

-- 热门内容视图（按点赞数排序）
CREATE OR REPLACE VIEW v_hot_posts AS
SELECT 
    p.id,
    p.platform,
    p.title,
    p.author_nickname,
    p.metrics_likes AS likes,
    p.metrics_comments AS comments,
    p.metrics_shares AS shares,
    (p.metrics_likes + p.metrics_comments * 2 + p.metrics_shares * 3) AS hot_score,
    p.publish_time
FROM posts p
WHERE p.publish_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY hot_score DESC
LIMIT 100;


-- =============================================
-- 6. 示例查询
-- =============================================

-- 查询某个关键词的所有帖子
-- SELECT * FROM posts WHERE source_keyword = 'Python' ORDER BY publish_time DESC;

-- 查询某个帖子的所有评论（包括层级）
-- SELECT * FROM comments WHERE content_id = '5253447687340964' ORDER BY comment_level, publish_time;

-- 查询某个作者的所有内容
-- SELECT * FROM posts WHERE author_id = '2286908003' ORDER BY publish_time DESC;

-- 统计各平台的数据量
-- SELECT platform, COUNT(*) as post_count FROM posts GROUP BY platform;

-- 查询最近7天的热门内容
-- SELECT * FROM v_hot_posts WHERE publish_time >= DATE_SUB(NOW(), INTERVAL 7 DAY);

-- =============================================
-- 完成
-- =============================================
SELECT '数据库表结构创建完成！' AS message;
