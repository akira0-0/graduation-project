# -*- coding: utf-8 -*-
"""
初始化场景规则
批量添加7个场景的过滤和筛选规则到规则库
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from filter_engine.rules import RuleManager, RuleCreate, RuleType, RuleCategory, RulePurpose
from filter_engine.config import settings
import json

# 规则定义
SCENARIO_RULES = [
    # ==================== 1. NORMAL 通用场景 ====================
    # --- 剔除规则 (filter) ---
    {
        "name": "通用-垃圾-乱码重复字符",
        "type": "regex",
        "content": json.dumps([
            r"(.)\1{5,}",  # 同一字符重复6次以上（支持中英文及符号）
            r"[a-zA-Z0-9]{20,}",  # 长串无意义字母数字
        ], ensure_ascii=False),
        "category": "spam",
        "purpose": "filter",
        "priority": 90,
        "description": "过滤包含大量乱码或重复字符的内容，如'啊啊啊啊啊啊'、长串无意义字符"
    },
    {
        "name": "通用-垃圾-系统提示语",
        "type": "keyword",
        "content": json.dumps([
            "该评论已删除", "作者已设置不可见", "内容已被屏蔽", "该内容不存在",
            "评论已关闭", "仅自己可见", "该用户已注销", "内容违规已处理",
            "系统提示", "自动回复", "机器人消息"
        ], ensure_ascii=False),
        "category": "spam",
        "purpose": "filter",
        "priority": 95,
        "description": "过滤系统自动生成的提示语和无效占位内容"
    },
    {
        "name": "通用-敏感-涉黄词库",
        "type": "keyword",
        "content": json.dumps([
            "约炮", "一夜情", "援交", "包养", "小姐服务", "上门服务",
            "成人视频", "黄片", "色情", "裸聊", "看片加", "福利群",
            "寂寞加", "深夜福利", "激情视频", "脱衣"
        ], ensure_ascii=False),
        "category": "sensitive",
        "purpose": "filter",
        "priority": 100,
        "description": "涉黄内容关键词黑名单，优先级最高必须过滤"
    },
    {
        "name": "通用-敏感-涉政词库",
        "type": "keyword",
        "content": json.dumps([
            "翻墙软件", "VPN推荐", "FQ工具", "64事件", "反共",
            "政权颠覆", "分裂国家", "境外势力", "邪教组织"
        ], ensure_ascii=False),
        "category": "sensitive",
        "purpose": "filter",
        "priority": 100,
        "description": "涉政敏感词黑名单，红线内容必须过滤"
    },
    {
        "name": "通用-敏感-暴力词库",
        "type": "keyword",
        "content": json.dumps([
            "杀人教程", "自杀方法", "炸弹制作", "枪支买卖", "毒品交易",
            "雇凶", "买凶", "人肉搜索", "网暴", "死全家"
        ], ensure_ascii=False),
        "category": "sensitive",
        "purpose": "filter",
        "priority": 100,
        "description": "暴力相关词汇黑名单，涉及人身安全必须过滤"
    },
    # --- 保留规则 (select) ---
    {
        "name": "通用-质量-有效中文内容",
        "type": "regex",
        "content": json.dumps([
            r"[\u4e00-\u9fa5]{10,}",  # 至少10个中文字符
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 50,
        "description": "保留包含至少10个中文字符的有效内容"
    },

    # ==================== 2. ECOMMERCE 电商场景 ====================
    # --- 剔除规则 (filter) ---
    {
        "name": "电商-引流-私信加V",
        "type": "keyword",
        "content": json.dumps([
            "私信我", "私聊我", "加V", "加v", "➕V", "＋V", "加威", "加薇",
            "加微", "➕微", "威信", "薇信", "微信号", "VX", "vx", "Vx",
            "wx号", "WX号", "企鹅号", "QQ号", "扣扣", "私我", "滴滴我",
            "d我", "D我", "dd我", "DD我"
        ], ensure_ascii=False),
        "category": "ad",
        "purpose": "filter",
        "priority": 90,
        "description": "过滤引导用户私信、添加微信/QQ等引流话术"
    },
    {
        "name": "电商-引流-链接主页",
        "type": "keyword",
        "content": json.dumps([
            "链接在主页", "主页有链接", "戳主页", "看主页", "点主页",
            "简介有链接", "个签有", "头像点进去", "点头像", "置顶有",
            "橱窗有", "店铺在", "淘口令", "复制这段", "打开淘宝"
        ], ensure_ascii=False),
        "category": "ad",
        "purpose": "filter",
        "priority": 88,
        "description": "过滤引导用户点击主页、简介等引流行为"
    },
    {
        "name": "电商-引流-拼团助力",
        "type": "keyword",
        "content": json.dumps([
            "拼多多助力", "帮我砍一刀", "砍价免费拿", "助力一下", "帮忙点一下",
            "帮我助力", "点击链接助力", "免费领取", "0元购", "一分钱抢"
        ], ensure_ascii=False),
        "category": "spam",
        "purpose": "filter",
        "priority": 85,
        "description": "过滤拼团、砍价、助力等营销spam内容"
    },
    {
        "name": "电商-违规-广告法禁词",
        "type": "keyword",
        "content": json.dumps([
            "全网最低", "史上最强", "第一品牌", "顶级品质", "极致体验",
            "绝无仅有", "独一无二", "国家级", "最佳", "最好", "最优",
            "第一", "唯一", "首选", "100%有效", "无敌"
        ], ensure_ascii=False),
        "category": "ad",
        "purpose": "filter",
        "priority": 80,
        "description": "过滤违反广告法的绝对化用语"
    },
    {
        "name": "电商-垃圾-刷单特征",
        "type": "regex",
        "content": json.dumps([
            r"收到.*好评",  # 刷单话术
            r"五星好评.*返",  # 好评返现
            r"评价.*截图.*返",  # 晒图返现
        ], ensure_ascii=False),
        "category": "spam",
        "purpose": "filter",
        "priority": 85,
        "description": "过滤刷单、好评返现等虚假评价特征"
    },
    # --- 保留规则 (select) ---
    {
        "name": "电商-种草-真实评测词",
        "type": "keyword",
        "content": json.dumps([
            "好用", "踩雷", "回购", "性价比", "测评", "开箱", "使用感受",
            "用了一段时间", "亲测", "实测", "上手体验", "优缺点",
            "值得买", "不值得", "入手", "种草", "拔草", "空瓶"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 70,
        "description": "保留包含真实产品评测、种草拔草词汇的内容"
    },
    {
        "name": "电商-种草-购买体验词",
        "type": "keyword",
        "content": json.dumps([
            "价格", "优惠", "划算", "便宜", "贵", "物流", "发货",
            "包装", "正品", "假货", "质量", "材质", "做工", "颜色",
            "尺码", "大小", "适合", "推荐", "不推荐"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 65,
        "description": "保留包含购买体验、产品属性描述的内容"
    },

    # ==================== 3. NEWS 新闻资讯 ====================
    # --- 剔除规则 (filter) ---
    {
        "name": "新闻-垃圾-震惊体标题党",
        "type": "keyword",
        "content": json.dumps([
            "震惊", "惊呆了", "万万没想到", "竟然是这样", "真相令人",
            "不转不是中国人", "速看", "已删", "赶紧看", "疯传",
            "刚刚发生", "出大事了", "太可怕了", "吓死人"
        ], ensure_ascii=False),
        "category": "spam",
        "purpose": "filter",
        "priority": 75,
        "description": "过滤震惊体、标题党等情绪化无实质内容"
    },
    {
        "name": "新闻-谣言-常见谣言特征",
        "type": "keyword",
        "content": json.dumps([
            "听说", "据说", "有人说", "网传", "未经证实",
            "内部消息", "小道消息", "圈内爆料", "知情人士透露"
        ], ensure_ascii=False),
        "category": "spam",
        "purpose": "filter",
        "priority": 70,
        "description": "过滤无明确信源、疑似谣言的内容"
    },
    {
        "name": "新闻-敏感-政治敏感词",
        "type": "keyword",
        "content": json.dumps([
            "政变", "暴动", "起义", "推翻政府", "独立公投",
            "民族分裂", "恐怖袭击策划", "极端主义"
        ], ensure_ascii=False),
        "category": "sensitive",
        "purpose": "filter",
        "priority": 100,
        "description": "新闻场景政治敏感词，需严格过滤"
    },
    # --- 保留规则 (select) ---
    {
        "name": "新闻-权威-官方语态词",
        "type": "keyword",
        "content": json.dumps([
            "发布", "通报", "公告", "声明", "官宣", "据悉",
            "刚刚", "突发", "快讯", "最新消息", "权威发布",
            "新华社", "央视", "人民日报", "官方回应"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 80,
        "description": "保留包含官方、权威媒体语态的新闻内容"
    },
    {
        "name": "新闻-质量-新闻要素词",
        "type": "keyword",
        "content": json.dumps([
            "记者", "报道", "采访", "现场", "目击者", "当事人",
            "调查", "核实", "确认", "证实", "回应", "表示"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 70,
        "description": "保留包含新闻采访、调查要素的内容"
    },

    # ==================== 4. SOCIAL 社交内容 ====================
    # --- 剔除规则 (filter) ---
    {
        "name": "社交-引流-营销推广",
        "type": "keyword",
        "content": json.dumps([
            "优惠券", "折扣码", "促销", "限时抢购", "秒杀",
            "扫码领取", "二维码", "扫一扫", "关注领取", "转发抽奖",
            "点赞抽奖", "互关", "互粉", "求关注"
        ], ensure_ascii=False),
        "category": "ad",
        "purpose": "filter",
        "priority": 80,
        "description": "过滤社交场景中的营销推广、互粉互关内容"
    },
    {
        "name": "社交-负面-极端负能量",
        "type": "keyword",
        "content": json.dumps([
            "想死", "活不下去", "自杀", "轻生", "跳楼", "割腕",
            "不想活了", "解脱", "遗书", "告别"
        ], ensure_ascii=False),
        "category": "sensitive",
        "purpose": "filter",
        "priority": 95,
        "description": "过滤极端负能量、自杀倾向内容，需转入心理干预"
    },
    {
        "name": "社交-垃圾-机器生成特征",
        "type": "regex",
        "content": json.dumps([
            r"【.*?】{3,}",  # 过多方括号标签
            r"#\S+#\s*#\S+#\s*#\S+#\s*#\S+#",  # 连续4个以上话题标签
        ], ensure_ascii=False),
        "category": "spam",
        "purpose": "filter",
        "priority": 70,
        "description": "过滤机器批量生成的格式化内容"
    },
    # --- 保留规则 (select) ---
    {
        "name": "社交-生活-日常话题标签",
        "type": "keyword",
        "content": json.dumps([
            "#日常", "#生活", "#心情", "#随手拍", "#今日份",
            "#打卡", "#记录", "#分享", "#感悟", "#碎碎念",
            "#vlog", "#plog", "#日记"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 65,
        "description": "保留包含生活日常类话题标签的内容"
    },
    {
        "name": "社交-情感-口语化表达",
        "type": "regex",
        "content": json.dumps([
            r"哈哈+",  # 笑声
            r"[呢吧啊呀哦噢嘛]$",  # 语气词结尾
            r"[😀😁😂🤣😃😄😅😆😉😊😋😎😍😘🥰😗😙🥲😚☺😌😛😝😜🤪🤨🧐🤓😏🥳🤩😔😟😕🙁☹😣😖😫😩🥺😢😭😤😠😡🤬]{2,}",  # 多个emoji
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 60,
        "description": "保留口语化、情感表达丰富的社交内容"
    },

    # ==================== 5. FINANCE 金融财经 ====================
    # --- 剔除规则 (filter) ---
    {
        "name": "财经-违规-非法荐股",
        "type": "keyword",
        "content": json.dumps([
            "稳赚不赔", "保本收益", "内幕消息", "带你飞", "跟我买",
            "老师指导", "股神", "翻倍", "必涨", "必跌",
            "加群", "进群", "股票群", "荐股群", "分成合作"
        ], ensure_ascii=False),
        "category": "ad",
        "purpose": "filter",
        "priority": 95,
        "description": "过滤非法荐股、诈骗引流等违规金融内容"
    },
    {
        "name": "财经-违规-虚假承诺",
        "type": "keyword",
        "content": json.dumps([
            "保证收益", "零风险", "稳定回报", "日赚", "月入百万",
            "躺赚", "睡后收入", "财务自由", "一夜暴富"
        ], ensure_ascii=False),
        "category": "ad",
        "purpose": "filter",
        "priority": 90,
        "description": "过滤虚假收益承诺、夸大宣传的金融内容"
    },
    {
        "name": "财经-垃圾-情绪化喊单",
        "type": "regex",
        "content": json.dumps([
            r"明天(必|肯定)(涨|跌)",
            r"(抄底|逃顶|满仓|空仓)!+",
            r"(冲|梭哈|all in|allin)[!！]+",
        ], ensure_ascii=False),
        "category": "spam",
        "purpose": "filter",
        "priority": 75,
        "description": "过滤无逻辑支撑的情绪化喊单内容"
    },
    # --- 保留规则 (select) ---
    {
        "name": "财经-专业-股票术语",
        "type": "keyword",
        "content": json.dumps([
            "K线", "均线", "MACD", "KDJ", "RSI", "布林带",
            "市盈率", "市净率", "ROE", "EPS", "换手率", "成交量",
            "涨停", "跌停", "龙头股", "板块", "概念股", "主力"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 70,
        "description": "保留包含专业股票分析术语的内容"
    },
    {
        "name": "财经-专业-股票代码",
        "type": "regex",
        "content": json.dumps([
            r"[036]\d{5}",  # A股代码
            r"[Ss][HhZz]\d{6}",  # 带前缀股票代码
            r"\d{5}\.HK",  # 港股代码
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 65,
        "description": "保留包含具体股票代码的内容"
    },
    {
        "name": "财经-分析-研究语态",
        "type": "keyword",
        "content": json.dumps([
            "分析", "研报", "财报", "业绩", "预测", "趋势",
            "估值", "基本面", "技术面", "利好", "利空",
            "逻辑", "原因", "观点", "看法", "策略"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 68,
        "description": "保留包含分析研究语态的财经内容"
    },

    # ==================== 6. MEDICAL 医疗健康 ====================
    # --- 剔除规则 (filter) ---
    {
        "name": "医疗-违规-虚假疗效",
        "type": "keyword",
        "content": json.dumps([
            "根治", "治愈率100%", "药到病除", "包治百病", "祖传秘方",
            "神药", "特效药", "偏方", "奇效", "立竿见影",
            "无副作用", "纯天然无害"
        ], ensure_ascii=False),
        "category": "ad",
        "purpose": "filter",
        "priority": 95,
        "description": "过滤虚假疗效宣传、夸大医疗效果的内容"
    },
    {
        "name": "医疗-违规-伪科学",
        "type": "keyword",
        "content": json.dumps([
            "排毒", "酸碱体质", "以形补形", "食物相克", "负离子治病",
            "量子医学", "磁疗", "能量水", "碱性水治病"
        ], ensure_ascii=False),
        "category": "spam",
        "purpose": "filter",
        "priority": 90,
        "description": "过滤伪科学、无医学依据的健康谣言"
    },
    {
        "name": "医疗-违规-处方药交易",
        "type": "keyword",
        "content": json.dumps([
            "代购药品", "药品代购", "处方药出售", "卖药",
            "有货私聊", "需要的联系", "渠道药"
        ], ensure_ascii=False),
        "category": "sensitive",
        "purpose": "filter",
        "priority": 95,
        "description": "过滤涉及处方药非法交易的内容"
    },
    {
        "name": "医疗-隐私-患者信息",
        "type": "regex",
        "content": json.dumps([
            r"病历号[：:]\s*\d+",
            r"住院号[：:]\s*\d+",
            r"身份证[号]?[：:]\s*\d{17}[\dXx]",
        ], ensure_ascii=False),
        "category": "sensitive",
        "purpose": "filter",
        "priority": 100,
        "description": "过滤包含患者隐私信息（病历号、身份证等）的内容"
    },
    # --- 保留规则 (select) ---
    {
        "name": "医疗-经验-就医体验词",
        "type": "keyword",
        "content": json.dumps([
            "康复经历", "就诊", "就医", "挂号", "门诊", "住院",
            "手术", "复查", "副作用", "疗程", "医生说",
            "检查报告", "化验单", "诊断", "治疗方案"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 75,
        "description": "保留真实就医体验、康复经历分享的内容"
    },
    {
        "name": "医疗-科普-专业医学词",
        "type": "keyword",
        "content": json.dumps([
            "症状", "病因", "病理", "临床", "医学", "药理",
            "适应症", "禁忌症", "不良反应", "用法用量",
            "谨遵医嘱", "咨询医生", "专业指导"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 70,
        "description": "保留专业医学科普、用药指导类内容"
    },

    # ==================== 7. EDUCATION 教育培训 ====================
    # --- 剔除规则 (filter) ---
    {
        "name": "教育-引流-焦虑营销",
        "type": "keyword",
        "content": json.dumps([
            "不学就废", "再不学就晚了", "同龄人已经", "你还在",
            "月薪过万", "年薪百万", "躺赚", "速成", "7天精通",
            "21天", "零基础月入", "小白也能"
        ], ensure_ascii=False),
        "category": "ad",
        "purpose": "filter",
        "priority": 85,
        "description": "过滤制造焦虑、夸大培训效果的营销内容"
    },
    {
        "name": "教育-违规-虚假承诺",
        "type": "keyword",
        "content": json.dumps([
            "包过", "保过", "不过退款", "内部名额", "内部渠道",
            "考试答案", "原题", "泄题", "押题必中", "VIP通道"
        ], ensure_ascii=False),
        "category": "ad",
        "purpose": "filter",
        "priority": 90,
        "description": "过滤虚假承诺、疑似考试作弊的违规内容"
    },
    {
        "name": "教育-引流-课程推销",
        "type": "keyword",
        "content": json.dumps([
            "私信领取", "领取资料", "免费资料", "扫码领课",
            "限时免费", "原价", "现价", "优惠价", "拼团价",
            "报名链接", "课程链接"
        ], ensure_ascii=False),
        "category": "ad",
        "purpose": "filter",
        "priority": 80,
        "description": "过滤引导购买课程、领取资料的引流内容"
    },
    # --- 保留规则 (select) ---
    {
        "name": "教育-干货-学习资源词",
        "type": "keyword",
        "content": json.dumps([
            "笔记", "真题", "考点", "知识点", "学习路径", "上岸",
            "备考", "复习", "刷题", "错题", "总结", "攻略",
            "经验贴", "心得", "方法论"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 75,
        "description": "保留学习笔记、备考经验等干货内容"
    },
    {
        "name": "教育-经验-考试类型词",
        "type": "keyword",
        "content": json.dumps([
            "高考", "中考", "考研", "考公", "考编", "事业编",
            "法考", "司考", "CPA", "CFA", "雅思", "托福",
            "四六级", "计算机等级", "教资", "医考"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 70,
        "description": "保留包含具体考试类型的经验分享内容"
    },
    {
        "name": "教育-认证-院校机构词",
        "type": "keyword",
        "content": json.dumps([
            "985", "211", "双一流", "清华", "北大", "复旦", "交大",
            "新东方", "学而思", "猿辅导", "作业帮", "得到", "混沌"
        ], ensure_ascii=False),
        "category": "other",
        "purpose": "select",
        "priority": 65,
        "description": "保留提及知名院校、正规机构的内容"
    },
]


def init_rules():
    """初始化场景规则"""
    print("=" * 60)
    print("开始初始化场景规则...")
    print("=" * 60)
    
    rule_manager = RuleManager(settings.DATABASE_PATH)
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for rule_data in SCENARIO_RULES:
        try:
            # 检查是否已存在同名规则
            existing = rule_manager.get_by_name(rule_data["name"])
            if existing:
                print(f"⏭️  跳过（已存在）: {rule_data['name']}")
                skip_count += 1
                continue
            
            # 创建规则
            rule_create = RuleCreate(
                name=rule_data["name"],
                type=RuleType(rule_data["type"]),
                content=rule_data["content"],
                category=RuleCategory(rule_data["category"]) if rule_data.get("category") else None,
                purpose=RulePurpose(rule_data["purpose"]),
                priority=rule_data.get("priority", 50),
                enabled=True,
                description=rule_data.get("description", ""),
            )
            
            rule = rule_manager.create(rule_create)
            purpose_icon = "🚫" if rule_data["purpose"] == "filter" else "✅"
            print(f"{purpose_icon} 创建成功: {rule.name} (ID: {rule.id})")
            success_count += 1
            
        except Exception as e:
            print(f"❌ 创建失败: {rule_data['name']} - {e}")
            error_count += 1
    
    print("=" * 60)
    print(f"初始化完成!")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ⏭️  跳过: {skip_count}")
    print(f"  ❌ 失败: {error_count}")
    print(f"  📊 总计: {len(SCENARIO_RULES)}")
    print("=" * 60)
    
    # 统计各场景规则数
    print("\n📈 规则分布统计:")
    scenarios = {}
    for rule in SCENARIO_RULES:
        scenario = rule["name"].split("-")[0]
        purpose = rule["purpose"]
        key = f"{scenario}"
        if key not in scenarios:
            scenarios[key] = {"filter": 0, "select": 0}
        scenarios[key][purpose] += 1
    
    for scenario, counts in scenarios.items():
        print(f"  {scenario}: 过滤 {counts['filter']} 条, 保留 {counts['select']} 条")


if __name__ == "__main__":
    init_rules()
