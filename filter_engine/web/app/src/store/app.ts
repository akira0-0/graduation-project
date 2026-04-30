import { create } from 'zustand'
import type { PageId, Rule, RuleStats, L2Info, DatasetItem, DbStats } from '../types'

// ── 页面配置 ──────────────────────────────────
export interface PageConfig {
  id: PageId
  title: string
  subtitle: string
  emoji: string
}

export const PAGE_CONFIGS: PageConfig[] = [
  { id: 1, title: '输入查询',     subtitle: '描述你的筛选需求',        emoji: '🔍' },
  { id: 2, title: 'Layer-2 过滤', subtitle: '场景规则 + LLM 缺口分析', emoji: '⚡' },
  { id: 3, title: 'Layer-3 研判', subtitle: 'LLM 语义逐条研判',        emoji: '🧠' },
  { id: 4, title: '数据集',       subtitle: '查看并勾选筛选结果',       emoji: '✅' },
]

// ── 全局状态 ──────────────────────────────────
export interface AppState {
  // 导航
  currentPage: PageId
  unlockedPages: Set<PageId>

  // Page 1 - 查询配置
  query: string
  scenario: string        // '' | 'normal' | 'ecommerce' | ...
  platform: string        // '' | 'xhs' | 'weibo'
  maxPosts: number
  minRelevance: string    // 'high' | 'medium' | 'low'

  // 数据库统计（Page1展示）
  dbStats: DbStats | null

  // 异步任务
  sessionId: string | null
  sessionStatus: 'idle' | 'processing' | 'completed' | 'failed'
  sessionProgress: number   // 0-100
  sessionQuery: string
  sessionStats: {
    l1_total_posts: number
    l2_passed_posts: number
    l3_passed_posts: number
  }
  sessionError: string | null
  pollingActive: boolean

  // Layer-2 数据（从轮询 status.layer2_info 得到）
  layer2Info: L2Info | null

  // Layer-3 数据集（从 /dataset 接口获取）
  datasetItems: DatasetItem[]
  datasetTotal: number
  datasetFallback: boolean  // 是否降级到 l2dataset

  // Layer-3 流动展示计数
  revealedCount: number

  // Page 4 - 勾选
  selectedIndices: Set<number>

  // 规则面板
  rules: Rule[]
  ruleStats: RuleStats | null

  // Actions
  setQuery: (q: string) => void
  setScenario: (s: string) => void
  setPlatform: (p: string) => void
  setMaxPosts: (n: number) => void
  setMinRelevance: (r: string) => void
  goToPage: (page: PageId) => void
  unlockPage: (page: PageId) => void

  setDbStats: (s: DbStats) => void

  startSession: (sessionId: string, query: string) => void
  updateSessionStatus: (
    status: AppState['sessionStatus'],
    progress: number,
    stats: AppState['sessionStats'],
    layer2Info: L2Info | null,
    error: string | null,
  ) => void
  setPollingActive: (v: boolean) => void

  setDataset: (items: DatasetItem[], total: number, fallback: boolean) => void
  appendDataset: (items: DatasetItem[]) => void
  setRevealedCount: (n: number) => void

  toggleSelected: (index: number) => void
  selectAll: (indices: number[]) => void
  clearSelected: () => void

  setRules: (rules: Rule[]) => void
  setRuleStats: (stats: RuleStats) => void
}

export const useAppStore = create<AppState>()((set) => ({
  currentPage: 1,
  unlockedPages: new Set<PageId>([1]),

  query: '',
  scenario: '',
  platform: '',
  maxPosts: 10000,
  minRelevance: 'medium',

  dbStats: null,

  sessionId: null,
  sessionStatus: 'idle',
  sessionProgress: 0,
  sessionQuery: '',
  sessionStats: { l1_total_posts: 0, l2_passed_posts: 0, l3_passed_posts: 0 },
  sessionError: null,
  pollingActive: false,

  layer2Info: null,

  datasetItems: [],
  datasetTotal: 0,
  datasetFallback: false,
  revealedCount: 0,

  selectedIndices: new Set<number>(),

  rules: [],
  ruleStats: null,

  setQuery: (q) => set({ query: q }),
  setScenario: (s) => set({ scenario: s }),
  setPlatform: (p) => set({ platform: p }),
  setMaxPosts: (n) => set({ maxPosts: n }),
  setMinRelevance: (r) => set({ minRelevance: r }),

  goToPage: (page) => set((state) => {
    if (!state.unlockedPages.has(page)) return state
    return { currentPage: page }
  }),

  unlockPage: (page) => set((state) => ({
    unlockedPages: new Set([...state.unlockedPages, page]),
  })),

  setDbStats: (s) => set({ dbStats: s }),

  startSession: (sessionId, query) => set({
    sessionId,
    sessionQuery: query,
    sessionStatus: 'processing',
    sessionProgress: 10,
    sessionError: null,
    sessionStats: { l1_total_posts: 0, l2_passed_posts: 0, l3_passed_posts: 0 },
    layer2Info: null,
    datasetItems: [],
    datasetTotal: 0,
    revealedCount: 0,
    selectedIndices: new Set<number>(),
  }),

  updateSessionStatus: (status, progress, stats, layer2Info, error) => set((state) => ({
    sessionStatus: status,
    sessionProgress: progress,
    sessionStats: stats,
    layer2Info: layer2Info ?? state.layer2Info,
    sessionError: error,
  })),

  setPollingActive: (v) => set({ pollingActive: v }),

  setDataset: (items, total, fallback) => set({
    datasetItems: items,
    datasetTotal: total,
    datasetFallback: fallback,
    revealedCount: 0,
  }),

  appendDataset: (items) => set((state) => ({
    datasetItems: [...state.datasetItems, ...items],
  })),

  setRevealedCount: (n) => set({ revealedCount: n }),

  toggleSelected: (index) => set((state) => {
    const s = new Set(state.selectedIndices)
    if (s.has(index)) s.delete(index)
    else s.add(index)
    return { selectedIndices: s }
  }),
  selectAll: (indices) => set({ selectedIndices: new Set(indices) }),
  clearSelected: () => set({ selectedIndices: new Set<number>() }),

  setRules: (rules) => set({ rules }),
  setRuleStats: (stats) => set({ ruleStats: stats }),
}))
