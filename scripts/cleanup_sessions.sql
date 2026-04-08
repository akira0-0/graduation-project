-- Session 临时表快速清理 SQL
-- 
-- 使用方法:
--   1. 打开 Supabase Dashboard SQL 编辑器
--      https://supabase.com/dashboard/project/rynxtsbrwvexytmztcyh/sql/new
--   2. 复制以下任一 SQL 语句执行

-- =====================================================
-- 方案 1: 清理 L2 临时表（保留 L3 和 metadata）
-- =====================================================
TRUNCATE TABLE session_l2_posts, session_l2_comments;

-- =====================================================
-- 方案 2: 清理所有 session 相关表
-- =====================================================
-- TRUNCATE TABLE session_l2_posts, session_l2_comments, session_l3_results, session_metadata;

-- =====================================================
-- 方案 3: 仅清理特定表
-- =====================================================
-- TRUNCATE TABLE session_l2_posts;
-- TRUNCATE TABLE session_l2_comments;
-- TRUNCATE TABLE session_l3_results;
-- TRUNCATE TABLE session_metadata;

-- =====================================================
-- 查询各表数据量
-- =====================================================
-- SELECT 
--     'session_l2_posts' as table_name, COUNT(*) as count FROM session_l2_posts
-- UNION ALL
-- SELECT 
--     'session_l2_comments' as table_name, COUNT(*) as count FROM session_l2_comments
-- UNION ALL
-- SELECT 
--     'session_l3_results' as table_name, COUNT(*) as count FROM session_l3_results
-- UNION ALL
-- SELECT 
--     'session_metadata' as table_name, COUNT(*) as count FROM session_metadata;
