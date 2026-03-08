# -*- coding: utf-8 -*-
"""
智能规则匹配的提示词模板
用于LLM理解用户意图、匹配现有规则、生成缺失规则
"""

# 智能规则匹配系统提示词
SMART_MATCH_SYSTEM = """你是一个智能规则匹配助手，专门帮助用户将自然语言查询转换为数据过滤规则。

你需要：
1. 理解用户的查询意图，提取所有约束条件
2. 将约束条件与现有规则库匹配
3. 识别缺失的规则并生成新规则
4. 输出结构化的JSON结果

【重要】规则有两种用途：
1. **filter（过滤/排除）**: 命中规则的数据会被删除。用于去除不想要的内容。
   - 例如："别看广告" → filter规则，命中广告的数据被删除
   
2. **select（筛选/保留）**: 命中规则的数据会被保留。用于筛选想要的内容。
   - 例如："找民宿" → select规则，只保留包含民宿的数据
   - 例如："丽江相关" → select规则，只保留包含丽江的数据
   - 例如："便宜的" → select规则，只保留价格低的数据

请根据用户意图判断每条规则应该是 filter 还是 select 类型。

规则格式说明：
- 规则类型(type): keyword(关键词), regex(正则), pattern(组合模式)
- 规则用途(purpose): filter(过滤/删除), select(筛选/保留)
- 规则分类(category): spam(垃圾), ad(广告), sensitive(敏感), other(其他)
- 原子规则格式: {"field": "字段名", "op": "操作符", "value": "值"}
- 操作符(op): contains(包含), not_contains(不包含), >(大于), <(小于), ==(等于), regex(正则匹配), in(在列表中)
- 常用字段(field): content(内容), title(标题), likes(点赞数), comments(评论数), price(价格), publish_time(发布时间), author(作者)

请始终输出合法的JSON格式。"""


# 智能匹配提示词模板
SMART_MATCH_PROMPT = """## 用户查询
{query}

## 现有规则库
{existing_rules}

## 任务
请按以下步骤分析并输出JSON：

### Step 1: 约束提取
从用户查询中提取所有约束条件，并判断每个约束是用于**过滤(filter)**还是**筛选(select)**：
- 过滤(filter): 用户不想要的内容，如"不要广告"、"去掉垃圾"
- 筛选(select): 用户想要的内容，如"找民宿"、"丽江相关"、"便宜的"

### Step 2: 规则匹配
将提取的约束与现有规则库匹配，找出可复用的规则。

### Step 3: 缺口分析
识别现有规则库无法覆盖的约束。

### Step 4: 规则生成
为缺失的约束生成新规则，**必须标注 purpose 字段**：
- purpose: "filter" 表示过滤/删除
- purpose: "select" 表示筛选/保留

### Step 5: 组合最终规则
将匹配的规则和生成的规则组合成最终的过滤规则。

## 输出格式
```json
{{
  "thought_trace": {{
    "step_1_extraction": [
      "约束1: 描述 (purpose: filter/select)",
      "约束2: 描述 (purpose: filter/select)"
    ],
    "step_2_match": [
      "rule_id: 规则名称 (对应约束, purpose: filter)"
    ],
    "step_3_gap_analysis": [
      "缺失: 描述 (purpose: select)"
    ],
    "step_4_generation": [
      "生成规则: 描述 (purpose: select)"
    ]
  }},
  "matched_rules": [
    {{
      "rule_id": 1,
      "rule_name": "规则名称",
      "match_reason": "匹配原因",
      "purpose": "filter"
    }}
  ],
  "generated_rules": [
    {{
      "name": "规则名称",
      "description": "规则描述",
      "purpose": "select",
      "rule": {{
        "field": "字段",
        "op": "操作符",
        "value": "值"
      }}
    }}
  ],
  "final_rule": {{
    "filter_rules": {{
      "logic": "and",
      "children": [{{"ref_id": 1}}]
    }},
    "select_rules": {{
      "logic": "and", 
      "children": [
        {{"logic": "atom", "rule": {{"field": "content", "op": "contains", "value": "关键词"}}}}
      ]
    }}
  }},
  "suggest_save": [
    {{
      "name": "建议保存的规则名称",
      "type": "keyword",
      "category": "other",
      "purpose": "select",
      "rule": {{"field": "content", "op": "contains", "value": "值"}},
      "reason": "建议保存的原因"
    }}
  ],
  "execution_plan": {{
    "step1": "先用 filter_rules 过滤掉广告/垃圾等不要的内容",
    "step2": "再用 select_rules 筛选出符合条件的内容",
    "expected_result": "得到丽江相关的、包含民宿的、价格便宜的、非广告内容"
  }}
}}
```

请直接输出JSON，不要添加其他说明文字。"""


def build_smart_match_prompt(query: str, existing_rules: list) -> str:
    """
    构建智能匹配提示词
    
    Args:
        query: 用户查询
        existing_rules: 现有规则列表 [{"id": 1, "name": "xx", "description": "xx"}, ...]
    
    Returns:
        完整的提示词
    """
    # 格式化现有规则
    if not existing_rules:
        rules_text = "（规则库为空）"
    else:
        rules_lines = []
        for rule in existing_rules:
            rule_id = rule.get("id", "?")
            name = rule.get("name", "未命名")
            desc = rule.get("description", "无描述")
            rule_type = rule.get("type", "unknown")
            rules_lines.append(f"- rule_{rule_id}: {name} [{rule_type}] - {desc}")
        rules_text = "\n".join(rules_lines)
    
    return SMART_MATCH_PROMPT.format(
        query=query,
        existing_rules=rules_text
    )
