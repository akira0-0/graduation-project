# -*- coding: utf-8 -*-
"""
初始化测试规则
创建常见的敏感词过滤规则
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filter_engine.rules import RuleManager, RuleCreate

# 测试用敏感词（安全的示例）
TEST_RULES = [
    {
        "name": "垃圾广告过滤",
        "type": "keyword",
        "content": '["加微信", "vx", "wx", "私信我", "加Q", "QQ群", "点击链接", "扫码关注", "免费领取", "限时优惠", "代刷", "代练", "代开", "发票", "贷款秒批", "兼职日结", "轻松赚钱", "月入过万", "刷单", "推广", "引流", "加群"]',
        "category": "spam",
        "priority": 100,
        "description": "过滤垃圾广告、营销推广类内容"
    },
    {
        "name": "辱骂攻击过滤",
        "type": "keyword",
        "content": '["垃圾", "废物", "滚", "闭嘴", "脑残", "智障", "傻X", "SB", "NC"]',
        "category": "abuse",
        "priority": 90,
        "description": "过滤辱骂、攻击性言论"
    },
    {
        "name": "低质量内容过滤",
        "type": "keyword",
        "content": '["水军", "刷评论", "买粉", "假货", "骗子", "三无产品", "虚假宣传", "夸大其词"]',
        "category": "spam",
        "priority": 80,
        "description": "过滤低质量、虚假内容"
    },
    {
        "name": "联系方式正则",
        "type": "regex",
        "content": r'["微信[：:][a-zA-Z0-9_]{5,}", "QQ[：:][0-9]{5,}", "vx[：:][a-zA-Z0-9_]+", "[0-9]{11}"]',
        "category": "spam",
        "priority": 85,
        "description": "使用正则表达式过滤联系方式"
    },
    {
        "name": "URL链接过滤",
        "type": "regex",
        "content": r'["http[s]?://[\\w\\-\\./]+", "www\\.[\\w\\-\\./]+"]',
        "category": "spam",
        "priority": 70,
        "description": "过滤外部链接"
    }
]


def init_rules():
    """初始化测试规则"""
    db_path = os.path.join(
        os.path.dirname(__file__),
        'filter_engine', 'data', 'rules.db'
    )
    
    manager = RuleManager(db_path)
    
    print("=" * 60)
    print("初始化测试规则")
    print("=" * 60)
    
    created_count = 0
    skipped_count = 0
    
    for rule_data in TEST_RULES:
        try:
            # 检查是否已存在
            existing = manager.get_by_name(rule_data["name"])
            if existing:
                print(f"⏭️  跳过（已存在）: {rule_data['name']}")
                skipped_count += 1
                continue
            
            # 创建规则
            rule = manager.create(RuleCreate(**rule_data))
            print(f"✅ 创建成功: {rule.name} (ID: {rule.id})")
            created_count += 1
            
        except Exception as e:
            print(f"❌ 创建失败: {rule_data['name']} - {e}")
    
    print("\n" + "=" * 60)
    print(f"完成！创建 {created_count} 条，跳过 {skipped_count} 条")
    print("=" * 60)
    
    # 显示统计
    stats = manager.stats()
    print(f"\n当前规则统计:")
    print(f"  总计: {stats['total']}")
    print(f"  启用: {stats['enabled']}")
    print(f"  禁用: {stats['disabled']}")
    print(f"\n按类型分布:")
    for rule_type, count in stats['by_type'].items():
        print(f"  {rule_type}: {count}")
    print(f"\n按分类分布:")
    for category, count in stats['by_category'].items():
        print(f"  {category}: {count}")


if __name__ == "__main__":
    init_rules()
