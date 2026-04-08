-- =============================================
-- Session 临时表 Schema
-- Version: 1.0
-- Date: 2026-04-08
-- Description: 存储 Layer-2 和 Layer-3 过滤过程中的临时数据
--              支持多用户并发查询，通过 session_id 隔离
-- =============================================

-- =============================================
-- 1. Layer-2 Session 帖子表
-- =============================================
CREATE TABLE IF NOT EXISTS session_l2_posts (
    -- 主键与来源
    id VARCHAR(50) PRIMARY KEY,                      -- 来自 filtered_posts.id
    session_id VARCHAR(50) NOT NULL,                 -- 本次查询的唯一 session ID
    
    -- 核心内容（从 filtered_posts 复制）
    platform VARCHAR(20) NOT NULL,
    type VARCHAR(20),
    url TEXT,
    title VARCHAR(500),
    content TEXT,
    
    -- 时间
    publish_time TIMESTAMP,
    
    -- 作者
    author_id VARCHAR(50),
    author_nickname VARCHAR(100),
    author_ip_location VARCHAR(50),
    author_is_verified BOOLEAN DEFAULT FALSE,
    
    -- 互动指标
    metrics_likes INTEGER DEFAULT 0,
    metrics_collects INTEGER DEFAULT 0,
    metrics_comments INTEGER DEFAULT 0,
    metrics_shares INTEGER DEFAULT 0,
    
    -- 标签
    tags JSONB,
    source_keyword VARCHAR(100),
    
    -- Layer-2 过滤元数据
    scene_matched_rules JSONB,                       -- Layer-2 场景规则命中记录
    filter_batch_id VARCHAR(50),                     -- 关联原始 filtered_posts 的批次
    
    -- Session 管理
    created_at TIMESTAMP DEFAULT NOW(),              -- 创建时间（用于 TTL 清理）
    query_text TEXT                                  -- 本次查询的原始文本（调试用）
);

-- 注释
COMMENT ON TABLE session_l2_posts IS 'Layer-2 场景规则过滤后的临时帖子数据，按 session_id 隔离';
COMMENT ON COLUMN session_l2_posts.session_id IS '查询会话唯一标识，格式: sess_{timestamp}_{uuid}';
COMMENT ON COLUMN session_l2_posts.scene_matched_rules IS 'Layer-2 命中的场景规则，JSON 数组';
COMMENT ON COLUMN session_l2_posts.created_at IS '记录创建时间，超过 TTL 的记录会被清理（建议 2 小时）';

-- 索引
CREATE INDEX IF NOT EXISTS idx_session_l2_posts_session_id ON session_l2_posts(session_id);
CREATE INDEX IF NOT EXISTS idx_session_l2_posts_created_at ON session_l2_posts(created_at);
CREATE INDEX IF NOT EXISTS idx_session_l2_posts_platform ON session_l2_posts(platform);


-- =============================================
-- 2. Layer-2 Session 评论表
-- =============================================
CREATE TABLE IF NOT EXISTS session_l2_comments (
    -- 主键与来源
    id VARCHAR(50) PRIMARY KEY,                      -- 来自 filtered_comments.id
    session_id VARCHAR(50) NOT NULL,                 -- 本次查询的 session ID
    
    -- 核心内容（从 filtered_comments 复制）
    content_id VARCHAR(50) NOT NULL,                 -- 关联的帖子 ID
    platform VARCHAR(20) NOT NULL,
    content TEXT,
    
    -- 时间
    publish_time TIMESTAMP,
    
    -- 作者
    author_id VARCHAR(50),
    author_nickname VARCHAR(100),
    author_ip_location VARCHAR(50),
    
    -- 互动指标
    metrics_likes INTEGER DEFAULT 0,
    metrics_sub_comments INTEGER DEFAULT 0,
    
    -- 评论层级
    parent_comment_id VARCHAR(50),
    root_comment_id VARCHAR(50),
    reply_to_user_id VARCHAR(50),
    reply_to_user_nickname VARCHAR(100),
    comment_level INTEGER DEFAULT 1,
    
    -- Layer-2 过滤元数据
    scene_matched_rules JSONB,
    filter_batch_id VARCHAR(50),
    
    -- Session 管理
    created_at TIMESTAMP DEFAULT NOW(),
    query_text TEXT
);

-- 注释
COMMENT ON TABLE session_l2_comments IS 'Layer-2 场景规则过滤后的临时评论数据';
COMMENT ON COLUMN session_l2_comments.content_id IS '关联的帖子 ID（可能在 session_l2_posts 或 filtered_posts 中）';

-- 索引
CREATE INDEX IF NOT EXISTS idx_session_l2_comments_session_id ON session_l2_comments(session_id);
CREATE INDEX IF NOT EXISTS idx_session_l2_comments_content_id ON session_l2_comments(content_id);
CREATE INDEX IF NOT EXISTS idx_session_l2_comments_created_at ON session_l2_comments(created_at);
CREATE INDEX IF NOT EXISTS idx_session_l2_comments_platform ON session_l2_comments(platform);
-- 联合索引：快速查询某 session 下某帖子的全部评论
CREATE INDEX IF NOT EXISTS idx_session_l2_comments_sess_content ON session_l2_comments(session_id, content_id);


-- =============================================
-- 3. Layer-3 最终结果表（帖子 + 评论嵌套）
-- =============================================
CREATE TABLE IF NOT EXISTS session_l3_results (
    -- 主键
    session_id VARCHAR(50) NOT NULL,
    post_id VARCHAR(50) NOT NULL,
    
    -- 帖子完整数据（包含 Layer-3 relevance_score）
    post_data JSONB NOT NULL,                        -- {id, title, content, relevance_score, ...}
    
    -- 该帖子下的全部评论列表
    comments JSONB,                                  -- [{id, content, ...}, {...}, ...]
    
    -- 统计
    comment_count INTEGER DEFAULT 0,                 -- 评论数量
    
    -- Session 管理
    created_at TIMESTAMP DEFAULT NOW(),
    query_text TEXT,
    
    PRIMARY KEY (session_id, post_id)
);

-- 注释
COMMENT ON TABLE session_l3_results IS 'Layer-3 LLM 语义过滤后的最终结果，帖子+评论嵌套结构';
COMMENT ON COLUMN session_l3_results.post_data IS '帖子完整数据 JSON，包含 relevance_score 字段';
COMMENT ON COLUMN session_l3_results.comments IS '该帖子下的评论数组 JSON';

-- 索引
CREATE INDEX IF NOT EXISTS idx_session_l3_results_session_id ON session_l3_results(session_id);
CREATE INDEX IF NOT EXISTS idx_session_l3_results_created_at ON session_l3_results(created_at);


-- =============================================
-- 4. Session 元数据表（可选，用于跟踪 session 状态）
-- =============================================
CREATE TABLE IF NOT EXISTS session_metadata (
    session_id VARCHAR(50) PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_intent JSONB,                              -- QueryIntent 的 JSON 序列化
    
    -- 统计
    l1_total_posts INTEGER DEFAULT 0,                -- Layer-1 输入帖子数
    l1_total_comments INTEGER DEFAULT 0,             -- Layer-1 输入评论数
    l2_passed_posts INTEGER DEFAULT 0,               -- Layer-2 通过帖子数
    l2_passed_comments INTEGER DEFAULT 0,            -- Layer-2 通过评论数
    l3_passed_posts INTEGER DEFAULT 0,               -- Layer-3 通过帖子数
    
    -- 时间
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',            -- pending / running / completed / failed
    error_message TEXT
);

-- 注释
COMMENT ON TABLE session_metadata IS 'Session 查询元数据，记录每次查询的统计信息和状态';

-- 索引
CREATE INDEX IF NOT EXISTS idx_session_metadata_created_at ON session_metadata(created_at);
CREATE INDEX IF NOT EXISTS idx_session_metadata_status ON session_metadata(status);


-- =============================================
-- 5. TTL 自动清理函数（定时任务）
-- =============================================
-- Supabase 可以配合 pg_cron 扩展定时执行此函数
-- 或在应用层调用此函数
CREATE OR REPLACE FUNCTION cleanup_expired_sessions(ttl_hours INTEGER DEFAULT 2)
RETURNS TABLE(deleted_posts BIGINT, deleted_comments BIGINT, deleted_results BIGINT, deleted_metadata BIGINT) AS $$
DECLARE
    cutoff_time TIMESTAMP;
    del_posts BIGINT;
    del_comments BIGINT;
    del_results BIGINT;
    del_metadata BIGINT;
BEGIN
    cutoff_time := NOW() - (ttl_hours || ' hours')::INTERVAL;
    
    -- 删除过期的 session 数据
    DELETE FROM session_l2_posts WHERE created_at < cutoff_time;
    GET DIAGNOSTICS del_posts = ROW_COUNT;
    
    DELETE FROM session_l2_comments WHERE created_at < cutoff_time;
    GET DIAGNOSTICS del_comments = ROW_COUNT;
    
    DELETE FROM session_l3_results WHERE created_at < cutoff_time;
    GET DIAGNOSTICS del_results = ROW_COUNT;
    
    DELETE FROM session_metadata WHERE created_at < cutoff_time AND status IN ('completed', 'failed');
    GET DIAGNOSTICS del_metadata = ROW_COUNT;
    
    RETURN QUERY SELECT del_posts, del_comments, del_results, del_metadata;
END;
$$ LANGUAGE plpgsql;

-- 注释
COMMENT ON FUNCTION cleanup_expired_sessions IS '清理超过 TTL 的过期 session 数据，默认 2 小时';


-- =============================================
-- 使用示例
-- =============================================
-- 1. 手动清理过期数据（保留最近 2 小时）：
--    SELECT * FROM cleanup_expired_sessions(2);
--
-- 2. 查询某个 session 的完整结果：
--    SELECT * FROM session_l3_results WHERE session_id = 'sess_20260408_abc123';
--
-- 3. 统计当前活跃 session 数量：
--    SELECT COUNT(DISTINCT session_id) FROM session_metadata WHERE status = 'running';


-- =============================================
-- Done
-- =============================================
SELECT '✅ Session tables created successfully! Use cleanup_expired_sessions(2) to clean old data.' AS message;
