-- =============================================
-- Supabase Database Schema (Unified Format)
-- Version: 1.0
-- Date: 2026-01-13
-- Description: Supabase table structure based on unified data format
-- =============================================

-- =============================================
-- 1. Posts Table
-- =============================================
CREATE TABLE IF NOT EXISTS posts (
    -- Primary key and basic info
    id VARCHAR(50) PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    type VARCHAR(20),
    url TEXT,
    title VARCHAR(500),
    content TEXT,
    
    -- Time information
    publish_time TIMESTAMP,
    last_update_time TIMESTAMP,
    
    -- Author information
    author_id VARCHAR(50),
    author_nickname VARCHAR(100),
    author_avatar VARCHAR(500),
    author_is_verified BOOLEAN DEFAULT FALSE,
    author_ip_location VARCHAR(50),
    
    -- Media information (stored as JSONB arrays)
    media_images JSONB,
    media_video_url TEXT,
    
    -- Interaction metrics
    metrics_likes INTEGER DEFAULT 0,
    metrics_collects INTEGER DEFAULT 0,
    metrics_comments INTEGER DEFAULT 0,
    metrics_shares INTEGER DEFAULT 0,
    
    -- Other metadata
    tags JSONB,
    source_keyword VARCHAR(100),
    task_id VARCHAR(50),
    crawl_time BIGINT,
    
    -- Extended fields (platform-specific data)
    extra JSONB,
    
    -- System fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add comments
COMMENT ON TABLE posts IS 'Posts/Content data table';
COMMENT ON COLUMN posts.id IS 'Unique content ID';
COMMENT ON COLUMN posts.platform IS 'Platform identifier (xhs/weibo/douyin/bilibili/zhihu)';
COMMENT ON COLUMN posts.type IS 'Content type (video/image/text)';
COMMENT ON COLUMN posts.media_images IS 'Image URL array (JSONB format)';
COMMENT ON COLUMN posts.extra IS 'Extended fields for platform-specific data';

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_publish_time ON posts(publish_time);
CREATE INDEX IF NOT EXISTS idx_posts_source_keyword ON posts(source_keyword);
CREATE INDEX IF NOT EXISTS idx_posts_task_id ON posts(task_id);
CREATE INDEX IF NOT EXISTS idx_posts_platform_author ON posts(platform, author_id);

-- Create update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =============================================
-- 2. Comments Table
-- =============================================
CREATE TABLE IF NOT EXISTS comments (
    -- Primary key and basic info
    id VARCHAR(50) PRIMARY KEY,
    content_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    content TEXT,
    publish_time TIMESTAMP,
    
    -- Author information
    author_id VARCHAR(50),
    author_nickname VARCHAR(100),
    author_avatar VARCHAR(500),
    author_ip_location VARCHAR(50),
    
    -- Interaction metrics
    metrics_likes INTEGER DEFAULT 0,
    metrics_sub_comments INTEGER DEFAULT 0,
    
    -- Comment hierarchy
    parent_comment_id VARCHAR(50),
    root_comment_id VARCHAR(50),
    reply_to_user_id VARCHAR(50),
    reply_to_user_nickname VARCHAR(100),
    comment_level INTEGER DEFAULT 1,
    
    -- Other metadata
    task_id VARCHAR(50),
    crawl_time BIGINT,
    
    -- Extended fields
    extra JSONB,
    
    -- System fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add comments
COMMENT ON TABLE comments IS 'Comments data table';
COMMENT ON COLUMN comments.id IS 'Unique comment ID';
COMMENT ON COLUMN comments.content_id IS 'Associated content ID (links to posts table)';
COMMENT ON COLUMN comments.parent_comment_id IS 'Parent comment ID (NULL for top-level comments)';
COMMENT ON COLUMN comments.root_comment_id IS 'Root comment ID (always points to top-level comment)';
COMMENT ON COLUMN comments.comment_level IS 'Comment level (1=top-level, 2=reply, 3=nested reply...)';

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_comments_content_id ON comments(content_id);
CREATE INDEX IF NOT EXISTS idx_comments_platform ON comments(platform);
CREATE INDEX IF NOT EXISTS idx_comments_author_id ON comments(author_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_comment_id ON comments(parent_comment_id);
CREATE INDEX IF NOT EXISTS idx_comments_root_comment_id ON comments(root_comment_id);
CREATE INDEX IF NOT EXISTS idx_comments_publish_time ON comments(publish_time);
CREATE INDEX IF NOT EXISTS idx_comments_platform_content ON comments(platform, content_id);

-- Create update timestamp trigger
CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add check constraint
ALTER TABLE comments ADD CONSTRAINT chk_comment_level CHECK (comment_level >= 1 AND comment_level <= 10);


-- =============================================
-- 3. Row Level Security (RLS) - Optional
-- =============================================
-- Enable the following policies if you need public access

-- ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE comments ENABLE ROW LEVEL SECURITY;

-- Allow everyone to read
-- CREATE POLICY "Allow public read access on posts" ON posts FOR SELECT USING (true);
-- CREATE POLICY "Allow public read access on comments" ON comments FOR SELECT USING (true);

-- Only allow authenticated users to insert
-- CREATE POLICY "Allow authenticated insert on posts" ON posts FOR INSERT WITH CHECK (auth.role() = 'authenticated');
-- CREATE POLICY "Allow authenticated insert on comments" ON comments FOR INSERT WITH CHECK (auth.role() = 'authenticated');


-- =============================================
-- 4. Create Views - Convenient Queries
-- =============================================

-- Posts overview view
CREATE OR REPLACE VIEW v_posts_overview AS
SELECT 
    id,
    platform,
    title,
    LEFT(content, 100) AS content_preview,
    author_nickname,
    publish_time,
    metrics_likes AS likes,
    metrics_comments AS comments,
    metrics_shares AS shares,
    source_keyword,
    created_at
FROM posts
ORDER BY publish_time DESC;

-- Comments overview view
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

-- Hot posts view (last 30 days)
CREATE OR REPLACE VIEW v_hot_posts AS
SELECT 
    id,
    platform,
    title,
    author_nickname,
    metrics_likes AS likes,
    metrics_comments AS comments,
    metrics_shares AS shares,
    (metrics_likes + metrics_comments * 2 + metrics_shares * 3) AS hot_score,
    publish_time
FROM posts
WHERE publish_time >= NOW() - INTERVAL '30 days'
ORDER BY hot_score DESC
LIMIT 100;


-- =============================================
-- 5. Example Queries
-- =============================================

-- Query all posts by keyword
-- SELECT * FROM posts WHERE source_keyword = 'Python' ORDER BY publish_time DESC;

-- Query all comments for a post (including hierarchy)
-- SELECT * FROM comments WHERE content_id = '5253447687340964' ORDER BY comment_level, publish_time;

-- Query all content by an author
-- SELECT * FROM posts WHERE author_id = '2286908003' ORDER BY publish_time DESC;

-- Count posts by platform
-- SELECT platform, COUNT(*) as post_count FROM posts GROUP BY platform;

-- Query hot posts from last 7 days
-- SELECT * FROM v_hot_posts WHERE publish_time >= NOW() - INTERVAL '7 days';

-- =============================================
-- Done
-- =============================================
SELECT '✅ Supabase database schema created successfully!' AS message;
