-- 过滤引擎数据库结构（精简版）

-- 规则表
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,              -- keyword, regex, pattern
    content TEXT NOT NULL,           -- JSON格式规则内容
    category TEXT,                   -- spam, ad, sensitive, profanity
    priority INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 版本历史表
CREATE TABLE IF NOT EXISTS rule_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_rules_enabled ON rules(enabled);
CREATE INDEX IF NOT EXISTS idx_rules_category ON rules(category);
CREATE INDEX IF NOT EXISTS idx_versions_rule_id ON rule_versions(rule_id);

-- 默认规则
INSERT OR IGNORE INTO rules (name, type, content, category, priority) VALUES
('spam_keywords', 'keyword', '["加微信", "免费领取", "点击链接", "限时优惠", "扫码关注", "私信我"]', 'spam', 10),
('ad_wechat', 'regex', '["[Vv]信", "[Ww][Xx]", "微信号?[:：]?\\s*\\w+", "加我\\s*\\d+"]', 'ad', 15),
('sensitive_words', 'keyword', '["敏感词示例1", "敏感词示例2"]', 'sensitive', 20);
