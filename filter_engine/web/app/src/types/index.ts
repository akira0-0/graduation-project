// ======================== 规则相关 ========================
export type RuleType = 'keyword' | 'regex' | 'semantic' | 'llm'
export type RuleCategory = 'spam' | 'ad' | 'political' | 'nsfw' | 'irrelevant' | 'custom'
export type RuleAction = 'filter' | 'select' | 'flag'

export interface Rule {
  id: number
  name: string
  type: RuleType
  content: string
  category: RuleCategory | null
  priority: number
  description: string
  enabled: boolean
  action: RuleAction
  created_at: string
  updated_at: string
}

export interface RuleCreate {
  name: string
  type: RuleType
  content: string
  category?: RuleCategory
  priority?: number
  description?: string
  action?: RuleAction
}

export interface RuleStats {
  total: number
  enabled: number
  by_type: Record<string, number>
  by_category: Record<string, number>
}

// ======================== 页面导航 ========================
export type PageId = 1 | 2 | 3 | 4

// ======================== 数据库统计 ========================
export interface DbStats {
  total_posts: number
  total_comments: number
  platforms: Record<string, number>
}

// ======================== 异步任务启动 ========================
export interface AsyncStartResponse {
  session_id: string
  status: 'processing'
  poll_url: string
  result_url: string
}

// ======================== Layer-2 信息（来自 status.layer2_info） ========================
export interface L2MatchedRule {
  rule_id: number
  rule_name: string
  purpose: string   // filter | select
  match_reason: string
}

export interface L2GapRule {
  name: string
  type: string
  content: string[]
  purpose: string
  description: string
}

export interface L2ThoughtTrace {
  step1_extraction: string[]
  step2_rule_match: string[]
  step3_gap_analysis: string[]
  step4_generation: string[]
}

export interface L2Info {
  stage: string
  scenario: string
  scenario_coverage: string
  thought_trace: L2ThoughtTrace | null
  matched_rules: L2MatchedRule[]
  gap_rules: L2GapRule[]
  execution_plan: { strategy?: string } | null
  l2_stats: {
    l1_total_posts: number
    l2_passed_posts: number
    pass_rate: number
    rule_stats: Record<string, number>
  } | null
  layer2_elapsed_s: number
}

// ======================== 轮询状态 ========================
export interface SessionStatusResponse {
  session_id: string
  status: 'processing' | 'completed' | 'failed'
  progress: number   // 0-100
  query: string
  stats: {
    l1_total_posts: number
    l2_passed_posts: number
    l3_passed_posts: number
  }
  layer2_info: L2Info | null
  error: string | null
}

// ======================== 数据集条目 ========================
export interface DatasetItem {
  id: string
  user: string
  content: string
  platform: string
  timestamp: string
  likes: number
  status: string
  rejectionReason: string | null
  _fallback_layer?: string
}

export interface DatasetResponse {
  session_id: string
  total: number
  offset: number
  limit: number
  data: DatasetItem[]
  fallback_layer?: string
}

// ======================== 场景选项 ========================
export interface ScenarioOption {
  value: string
  label: string
  description: string
}
