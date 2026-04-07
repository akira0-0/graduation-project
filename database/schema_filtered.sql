-- =============================================
-- 过滤结果表 Schema
-- Version: 1.1
-- Date: 2026-04-07
-- Description: 存储初步过滤后的帖子和评论数据，以及过滤任务日志
-- =============================================


-- =============================================
-- 1. 过滤后帖子表
-- =============================================
CREATE TABLE IF NOT EXISTS filtered_posts (
    -- 与原表关联
    id VARCHAR(50) PRIMARY KEY,                      -- 与 posts.id 保持一致
    original_id VARCHAR(50) NOT NULL,                -- 原始 posts.id，冗余存储方便查询

    -- 原始核心内容字段（从 posts 复制）
    platform VARCHAR(20) NOT NULL,
    type VARCHAR(20),
    url TEXT,
    title VARCHAR(500),
    content TEXT,

    -- 时间信息
    publish_time TIMESTAMP,

    -- 作者信息
    author_id VARCHAR(50),
    author_nickname VARCHAR(100),
    author_ip_location VARCHAR(50),
    author_is_verified BOOLEAN DEFAULT FALSE,

    -- 互动指标
    metrics_likes INTEGER DEFAULT 0,
    metrics_collects INTEGER DEFAULT 0,
    metrics_comments INTEGER DEFAULT 0,
    metrics_shares INTEGER DEFAULT 0,

    -- 标签/关键词
    tags JSONB,
    source_keyword VARCHAR(100),

    -- -----------------------------------------------
    -- 过滤元数据（新增字段）
    -- -----------------------------------------------
    filter_batch_id VARCHAR(50) NOT NULL,            -- 关联 filter_logs.batch_id，标记属于哪次过滤批次
    filter_passed_rules JSONB,                       -- 通过了哪些规则，例如 ["min_length", "keyword_match"]
    filter_rejected_rules JSONB,                     -- 被哪些规则拒绝（此表存的是通过的，但记录中间过程）
    quality_score NUMERIC(4, 3),                     -- 质量评分 0.000 ~ 1.000
    relevance_score NUMERIC(4, 3),                   -- 关键词相关性评分（可选，Layer-2 填充）
    filter_layer INTEGER DEFAULT 1,                  -- 由哪一层过滤通过：1=规则引擎, 2=LLM辅助

    -- 系统字段
    created_at TIMESTAMP DEFAULT NOW()
);

-- 注释
COMMENT ON TABLE filtered_posts IS '经过初步规则过滤后的帖子，是原始 posts 表的子集';
COMMENT ON COLUMN filtered_posts.original_id IS '对应 posts.id，方便回溯原始数据';
COMMENT ON COLUMN filtered_posts.filter_batch_id IS '关联 filter_logs.batch_id，标记属于哪次过滤任务';
COMMENT ON COLUMN filtered_posts.filter_passed_rules IS '通过的规则列表，JSON数组，例如 ["keyword_match","min_length"]';
COMMENT ON COLUMN filtered_posts.quality_score IS '内容质量评分，0~1，越高越好';
COMMENT ON COLUMN filtered_posts.relevance_score IS '与目标关键词的相关性评分，0~1';
COMMENT ON COLUMN filtered_posts.filter_layer IS '过滤层级：1=Layer1规则引擎, 2=Layer2 LLM辅助';

-- 索引
CREATE INDEX IF NOT EXISTS idx_filtered_posts_original_id ON filtered_posts(original_id);
CREATE INDEX IF NOT EXISTS idx_filtered_posts_platform ON filtered_posts(platform);
CREATE INDEX IF NOT EXISTS idx_filtered_posts_batch_id ON filtered_posts(filter_batch_id);
CREATE INDEX IF NOT EXISTS idx_filtered_posts_publish_time ON filtered_posts(publish_time);
CREATE INDEX IF NOT EXISTS idx_filtered_posts_source_keyword ON filtered_posts(source_keyword);
CREATE INDEX IF NOT EXISTS idx_filtered_posts_quality_score ON filtered_posts(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_filtered_posts_filter_layer ON filtered_posts(filter_layer);


-- =============================================
-- 2. 过滤后评论表
-- =============================================
CREATE TABLE IF NOT EXISTS filtered_comments (
    -- 与原表关联
    id VARCHAR(50) PRIMARY KEY,                      -- 与 comments.id 保持一致
    original_id VARCHAR(50) NOT NULL,                -- 原始 comments.id，冗余存储

    -- 原始核心内容字段（从 comments 复制）
    content_id VARCHAR(50) NOT NULL,                 -- 关联的帖子 ID（对应 posts.id / filtered_posts.id）
    platform VARCHAR(20) NOT NULL,
    content TEXT,

    -- 时间信息
    publish_time TIMESTAMP,

    -- 作者信息
    author_id VARCHAR(50),
    author_nickname VARCHAR(100),
    author_ip_location VARCHAR(50),

    -- 互动指标
    metrics_likes INTEGER DEFAULT 0,
    metrics_sub_comments INTEGER DEFAULT 0,

    -- 评论层级关系
    parent_comment_id VARCHAR(50),
    root_comment_id VARCHAR(50),
    reply_to_user_id VARCHAR(50),
    reply_to_user_nickname VARCHAR(100),
    comment_level INTEGER DEFAULT 1,

    -- -----------------------------------------------
    -- 过滤元数据（新增字段）
    -- -----------------------------------------------
    filter_batch_id VARCHAR(50) NOT NULL,            -- 关联 filter_logs.batch_id
    filter_passed_rules JSONB,                       -- 通过的规则列表
    filter_rejected_rules JSONB,                     -- 检测到但未达排除阈值的规则
    quality_score NUMERIC(4, 3),                     -- 质量评分 0.000 ~ 1.000（Layer-2 填充）
    relevance_score NUMERIC(4, 3),                   -- 相关性评分 0.000 ~ 1.000（Layer-3 填充）
    filter_layer INTEGER DEFAULT 1,                  -- 1=规则引擎, 2=LLM辅助

    -- 系统字段
    created_at TIMESTAMP DEFAULT NOW()
);

-- 注释
COMMENT ON TABLE filtered_comments IS '经过初步规则过滤后的评论，是原始 comments 表的子集';
COMMENT ON COLUMN filtered_comments.original_id IS '对应 comments.id，方便回溯原始数据';
COMMENT ON COLUMN filtered_comments.content_id IS '关联帖子 ID，可 JOIN filtered_posts 或 posts';
COMMENT ON COLUMN filtered_comments.filter_batch_id IS '关联 filter_logs.batch_id，标记属于哪次过滤任务';
COMMENT ON COLUMN filtered_comments.quality_score IS '内容质量评分，0~1，越高越好';
COMMENT ON COLUMN filtered_comments.relevance_score IS '与目标关键词的相关性评分，0~1';
COMMENT ON COLUMN filtered_comments.filter_layer IS '过滤层级：1=Layer1规则引擎, 2=Layer2 LLM辅助';

-- 索引
CREATE INDEX IF NOT EXISTS idx_filtered_comments_original_id ON filtered_comments(original_id);
CREATE INDEX IF NOT EXISTS idx_filtered_comments_content_id ON filtered_comments(content_id);
CREATE INDEX IF NOT EXISTS idx_filtered_comments_platform ON filtered_comments(platform);
CREATE INDEX IF NOT EXISTS idx_filtered_comments_batch_id ON filtered_comments(filter_batch_id);
CREATE INDEX IF NOT EXISTS idx_filtered_comments_publish_time ON filtered_comments(publish_time);
CREATE INDEX IF NOT EXISTS idx_filtered_comments_comment_level ON filtered_comments(comment_level);
CREATE INDEX IF NOT EXISTS idx_filtered_comments_quality_score ON filtered_comments(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_filtered_comments_filter_layer ON filtered_comments(filter_layer);
-- 联合索引：通过 content_id 快速拿某帖子下所有过滤评论
CREATE INDEX IF NOT EXISTS idx_filtered_comments_content_level ON filtered_comments(content_id, comment_level);


-- =============================================
-- 3. 过滤任务日志表
-- =============================================
CREATE TABLE IF NOT EXISTS filter_logs (
    -- 主键
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50) UNIQUE NOT NULL,            -- 唯一批次ID，格式建议: batch_{timestamp}

    -- 任务配置
    filter_criteria JSONB NOT NULL,                  -- 本次过滤使用的完整规则配置
    data_type VARCHAR(20) DEFAULT 'posts',           -- 过滤的数据类型：posts / comments
    source_keyword VARCHAR(100),                     -- 本次过滤针对的关键词（可为 NULL 表示全量）
    platform VARCHAR(20),                            -- 过滤的平台（可为 NULL 表示全平台）

    -- 过滤统计
    total_input INTEGER DEFAULT 0,                   -- 输入总数
    total_passed INTEGER DEFAULT 0,                  -- 通过总数
    total_rejected INTEGER DEFAULT 0,                -- 拒绝总数
    pass_rate NUMERIC(5, 4),                         -- 通过率 0.0000 ~ 1.0000

    -- 各步骤统计（详细）
    step_stats JSONB,                                -- 每个过滤步骤的统计，格式参考 filter_stats.filter_steps

    -- 任务状态
    status VARCHAR(20) DEFAULT 'pending',            -- pending / running / completed / failed
    error_message TEXT,                              -- 失败时的错误信息

    -- 时间
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds NUMERIC(10, 2)                  -- 耗时（秒）
);

-- 注释
COMMENT ON TABLE filter_logs IS '每次批量过滤任务的运行记录和统计信息';
COMMENT ON COLUMN filter_logs.batch_id IS '唯一批次标识，建议格式 batch_{yyyymmdd}_{timestamp}';
COMMENT ON COLUMN filter_logs.data_type IS '过滤数据类型：posts 或 comments';
COMMENT ON COLUMN filter_logs.filter_criteria IS '本次过滤配置的完整快照，便于复现';
COMMENT ON COLUMN filter_logs.step_stats IS '各过滤步骤详细统计，JSON数组格式';
COMMENT ON COLUMN filter_logs.pass_rate IS '通过率，等于 total_passed / total_input';
COMMENT ON COLUMN filter_logs.status IS '任务状态：pending/running/completed/failed';

-- 索引
CREATE INDEX IF NOT EXISTS idx_filter_logs_batch_id ON filter_logs(batch_id);
CREATE INDEX IF NOT EXISTS idx_filter_logs_status ON filter_logs(status);
CREATE INDEX IF NOT EXISTS idx_filter_logs_started_at ON filter_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_filter_logs_source_keyword ON filter_logs(source_keyword);


-- =============================================
-- Done
-- =============================================
SELECT '✅ filtered_posts, filtered_comments and filter_logs tables created successfully!' AS message;
