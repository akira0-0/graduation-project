# -*- coding: utf-8 -*-
"""
测试用敏感词库
仅用于开发和测试，实际使用请根据业务需求定制
"""

# 垃圾广告类
SPAM_KEYWORDS = [
    "加微信", "vx", "wx", "私信我", "加Q", "QQ群",
    "点击链接", "扫码关注", "免费领取", "限时优惠",
    "代刷", "代练", "代开", "发票", "贷款秒批",
    "兼职日结", "轻松赚钱", "月入过万", "刷单",
    "推广", "引流", "加群", "关注公众号"
]

# 辱骂攻击类（温和版）
ABUSE_KEYWORDS = [
    "垃圾", "废物", "滚", "闭嘴", "脑残",
    "智障", "傻X", "SB", "NC", "你妈的"
]

# 低质量内容
LOW_QUALITY_KEYWORDS = [
    "水军", "刷评论", "买粉", "假货", "骗子",
    "三无产品", "虚假宣传", "夸大其词"
]

# 测试用通用敏感词
TEST_KEYWORDS = [
    "测试敏感词", "违规内容", "不当言论", "禁止词汇"
]

# 合并所有类别（用于快速测试）
ALL_TEST_KEYWORDS = (
    SPAM_KEYWORDS + 
    ABUSE_KEYWORDS + 
    LOW_QUALITY_KEYWORDS + 
    TEST_KEYWORDS
)

# JSON 格式（可直接用于规则创建）
SPAM_RULE_CONTENT = '["加微信", "vx", "私信我", "加Q", "点击链接", "免费领取", "兼职日结", "刷单"]'

ABUSE_RULE_CONTENT = '["垃圾", "废物", "滚", "闭嘴", "脑残", "智障"]'

LOW_QUALITY_RULE_CONTENT = '["水军", "刷评论", "买粉", "假货", "骗子", "虚假宣传"]'


if __name__ == "__main__":
    import json
    
    print("=== 测试用敏感词库 ===")
    print(f"\n垃圾广告类 ({len(SPAM_KEYWORDS)} 个):")
    print(json.dumps(SPAM_KEYWORDS, ensure_ascii=False, indent=2))
    
    print(f"\n辱骂攻击类 ({len(ABUSE_KEYWORDS)} 个):")
    print(json.dumps(ABUSE_KEYWORDS, ensure_ascii=False, indent=2))
    
    print(f"\n低质量内容 ({len(LOW_QUALITY_KEYWORDS)} 个):")
    print(json.dumps(LOW_QUALITY_KEYWORDS, ensure_ascii=False, indent=2))
    
    print(f"\n总计: {len(ALL_TEST_KEYWORDS)} 个测试关键词")
