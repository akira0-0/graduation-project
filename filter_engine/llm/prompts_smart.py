# 极简场景识别prompt
SCENARIO_DETECT_PROMPT = (
  "你是一个文本分类器。请从下列标签中选择一个最贴切的返回，严禁输出任何解释文字：\n"
  "- ecommerce: 电商、商品、购物、物流、客服投诉\n"
  "- news: 时政、社会新闻、媒体报道\n"
  "- social: 社交平台动态、用户评论、粉丝互动\n"
  "- finance: 股票、理财、银行、经济分析\n"
  "- medical: 疾病、药物、医生咨询、健康建议\n"
  "- education: 学习、考试、课程、学术资料\n"
  "- normal: 无法归类的日常对话或通用内容\n\n"
  "内容：{{query}}"
)
# -*- coding: utf-8 -*-
"""
智能规则匹配的提示词模板
用于LLM理解用户意图、识别场景、匹配现有规则、分析语义缺口、生成补充规则
"""

# 场景名称中文映射
SCENARIO_NAMES = {
    "normal":     "通用",
    "ecommerce":  "电商",
    "news":       "新闻",
    "social":     "社交",
    "finance":    "财经",
    "medical":    "医疗",
    "education":  "教育",
}

# 智能规则匹配系统提示词（重构版）
SMART_MATCH_SYSTEM = """你是一个内容过滤引擎的"智能大脑"，负责处理规则无法覆盖的语义模糊、上下文相关、新颖未知的垃圾或敏感信息。

## 你的核心职责
1. **意图解析**：深度理解用户过滤意图，区分“要过滤的内容”(filter)和“要保留的内容”(select)
2. **规则匹配**：基于系统已识别并传入的场景（见下方提示），只需对该场景的规则库进行匹配和分析
3. **缺口分析**：识别规则库无法覆盖的需求，并生成补充规则

## 重要说明
- 场景已由系统识别并传入，你无需自行判断场景，只需基于传入场景分析
- 基础垃圾过滤（通用规则）已完成，你只需处理特定场景下的复杂逻辑

## 规则用途说明
- **filter（过滤删除）**：命中即删除。用于去除不想要的内容，如广告、垃圾、敏感词
- **select（筛选保留）**：命中即保留。用于保留想要的内容，如特定主题、质量标准

## 规则格式
- type: keyword（关键词列表匹配）| regex（正则表达式匹配）| pattern（组合逻辑）
- content: JSON 数组，如 ["词1", "词2"] 或正则数组
- category: spam | ad | sensitive | profanity | other

## 何时生成补充规则
只在以下情况生成，不要重复已有规则：
- 规则库的 content_keywords（关键词/正则）中没有能直接覆盖该意图的具体词汇时，必须生成新规则
- 需要正则表达式才能描述的模式（如“数字+单位”组合）
- 用户明确提到但规则库完全没有的概念

请始终输出合法的 JSON 格式，不要添加任何说明文字。
"""


# 智能匹配主提示词（场景感知版，精简优化）
SMART_MATCH_PROMPT = """
## 用户查询
{query}

## 已识别场景
{scene_info}

## 场景专属规则库（本次匹配的操作对象）
{scene_rules}

---

## ⚠️ 重要约束

1. 你只需匹配“场景专属规则库”中的规则，禁止匹配通用规则。
2. 必须逐条检查每一条规则的 content_keywords，不能遗漏。规则过多时可分批处理，确保不遗漏。
3. 只有当规则的 content_keywords（关键词/正则）中没有能直接覆盖该意图的具体词汇时，才生成新规则。
4. matched_rules 的 rule_id 必须是上方规则库中真实存在的 ID。

---

## 分析步骤

### Step 1：意图识别
- 提取所有过滤/保留约束，标注每条约束是 filter 还是 select
- 识别是否存在语义模糊、上下文相关、新颖未知的过滤需求

### Step 2：场景规则匹配（仅操作"场景专属规则库"）
- 遍历场景专属规则库中每一条规则，查看其 content_keywords
- 判断 content_keywords 与用户约束是否语义相关（同义/近义/包含均视为覆盖）
- 覆盖的规则记入 matched_rules（真实 ID + 名称 + 匹配原因）
- 未覆盖的约束进入 Step 3
- 若场景专属规则库为空，则所有约束均进入 Step 3

### Step 3：语义缺口分析
- 仅分析 Step 2 中未被覆盖的约束
- 区分两类缺口：
  a. 场景规则库中完全没有的概念/词汇 → 需生成新规则（进入 Step 4）
  b. 关键词规则无法判断的语义模糊/上下文内容 → 标记 needs_llm_semantic=true，不生成规则

### Step 4：补充规则生成（仅限 Step 3 a 类缺口）
- 为场景专属词汇缺口生成关键词/正则规则
- 规则名称使用场景前缀（如电商-、社交-）
- 不重复场景规则库中已有的任何关键词

---

## 输出格式（严格 JSON，不要添加注释或说明）
```json
{{
  "detected_scenario": "social",
  "scenario_coverage": "sufficient",
  "thought_trace": {{
    "step_1_extraction": [
      "约束1：去掉广告内容 (purpose: filter)",
      "约束2：保留高质量评论 (purpose: select)"
    ],
    "step_2_match": [
      "规则 社交-引流-营销推广 [ID:50] content_keywords含['推广','引流','加我','私信']，覆盖约束1",
      "约束2 在场景规则库中无 select 类型规则 → 进入缺口分析"
    ],
    "step_3_gap_analysis": [
      "缺口a：'高质量评论' 无对应 select 规则，content_keywords中无相关词 → 需生成",
      "缺口b：语义模糊的隐式广告 → needs_llm_semantic=true"
    ],
    "step_4_generation": [
      "生成规则：社交-质量-高质量评论词 (select, keyword)"
    ]
  }},
  "matched_rules": [
    {{
      "rule_id": 50,
      "rule_name": "社交-引流-营销推广",
      "match_reason": "content_keywords含推广/引流词，语义覆盖广告推广约束",
      "purpose": "filter"
    }}
  ],
  "gap_rules": [
    {{
      "name": "社交-质量-高质量评论词",
      "type": "keyword",
      "content": ["写得很好", "非常有用", "干货满满", "亲测有效"],
      "category": "other",
      "purpose": "select",
      "description": "保留高质量互动评论",
      "needs_llm_semantic": false
    }}
  ],
  "needs_llm_filter": true,
  "llm_filter_reason": "存在语义模糊的隐式广告内容，规则引擎无法识别",
  "execution_plan": {{
    "layer_1": "基础规则引擎：通用规则（垃圾/敏感）过滤",
    "layer_2": "场景规则引擎：社交场景规则（引流/营销）过滤 + 高质量词保留",
    "layer_3": "LLM语义过滤：识别隐式广告、语义模糊内容",
    "expected_result": "去除营销推广和垃圾内容，保留真实高质量评论"
  }}
}}
```
"""


def build_smart_match_prompt(
    query: str,
    detected_scenario: str = "normal",
    scene_rules: list = None,
    **kwargs  # 使用关键字参数接收可能传进来的 existing_rules 等旧参数，防止报错
) -> str:
    """
    构建场景感知的智能匹配提示词（精简版）
    """
    scenario_cn = SCENARIO_NAMES.get(detected_scenario, "通用")

    def fmt_scene_rules(rules_list: list) -> str:
        """场景规则格式化"""
        if not rules_list:
            return "（当前场景暂无专属规则，所有需求均由缺口规则覆盖）"
        lines = []
        for r in rules_list:
            rid = r.get("id", "?")
            name = r.get("name", "未命名")
            desc = r.get("description") or "无描述"
            rtype = r.get("type", "keyword")
            purpose = r.get("purpose", "filter")
            purpose_cn = "过滤" if purpose == "filter" else "保留"
            content_kw = r.get("content_preview", "")
            kw_str = f"\n    content_keywords: [{content_kw}]" if content_kw else ""
            lines.append(f"  - [ID:{rid}] {name} [{rtype}/{purpose_cn}] — {desc}{kw_str}")
        return "\n".join(lines)

    scene_info = f"场景：{scenario_cn}（{detected_scenario}）"
    if detected_scenario == "normal":
        scene_info += "\n说明：通用场景下无场景专属规则，由缺口规则进行补充。"

    # 重点：这里只传入模板中存在的变量，彻底移除 base_rules
    return SMART_MATCH_PROMPT.format(
        query=query,
        scene_info=scene_info,
        scene_rules=fmt_scene_rules(scene_rules)
    )
