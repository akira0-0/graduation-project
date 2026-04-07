-- =============================================
-- 迁移脚本：给 filter_logs 表补充 data_type 列
-- 在 Supabase SQL 编辑器中执行此文件
-- =============================================

ALTER TABLE filter_logs
    ADD COLUMN IF NOT EXISTS data_type VARCHAR(20) DEFAULT 'posts';

COMMENT ON COLUMN filter_logs.data_type IS '过滤数据类型：posts / comments';

SELECT '✅ filter_logs.data_type 列添加成功' AS message;
