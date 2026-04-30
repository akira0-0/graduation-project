import { useState, useEffect } from 'react'
import { Search, Database, ChevronRight } from 'lucide-react'
import { useAppStore } from '../store/app'
import { dbApi, filterApi, scenariosApi } from '../lib/api'
import type { ScenarioOption, DbStats } from '../types'

const QUERY_EXAMPLES = [
  '丽江旅游攻略，排除广告和引流',
  '小红书美食探店推荐，过滤好评返现',
  '理财知识科普，去除广告软文',
  '健身减肥方法，排除代购和推销',
]

const PLATFORM_OPTIONS = [
  { value: '', label: '全部平台' },
  { value: 'xhs', label: '小红书' },
  { value: 'weibo', label: '微博' },
]

const RELEVANCE_OPTIONS = [
  { value: 'high', label: '高相关' },
  { value: 'medium', label: '中相关' },
  { value: 'low', label: '低相关' },
]

export default function Page1Query() {
  const {
    query, setQuery,
    scenario, setScenario,
    platform, setPlatform,
    maxPosts, setMaxPosts,
    minRelevance, setMinRelevance,
    startSession,
    unlockPage, goToPage,
  } = useAppStore()

  const [scenarios, setScenarios] = useState<ScenarioOption[]>([])
  const [dbStats, setDbStats] = useState<DbStats | null>(null)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    dbApi.stats().then(setDbStats).catch(() => {})
    scenariosApi.list().then(setScenarios).catch(() => {})
  }, [])

  const handleStart = async () => {
    if (!query.trim()) { setError('请输入查询内容'); return }
    setError('')
    setStarting(true)

    try {
      const res = await filterApi.startAsync({
        query: query.trim(),
        platform: platform || undefined,
        max_posts: maxPosts,
        force_scenario: scenario || null,
        layer2_mode: 'strict',
        min_relevance: minRelevance as 'high' | 'medium' | 'low',
        auto_save: true,
        save_gap_rules: false,
      })
      startSession(res.session_id, query.trim())
      unlockPage(2)
      goToPage(2)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold text-slate-900">🔍 智能内容筛选</h1>
        <p className="text-slate-500 text-sm">输入你的筛选需求，系统将自动完成三层过滤分析</p>
      </div>

      {dbStats && (
        <div className="glass rounded-2xl px-5 py-3 flex flex-wrap items-center gap-3 text-sm">
          <Database size={14} className="text-indigo-400 shrink-0" />
          <span className="text-slate-500">数据库共</span>
          <span className="font-bold text-indigo-700">{dbStats.total_posts.toLocaleString()}</span>
          <span className="text-slate-500">帖子 /</span>
          <span className="font-bold text-violet-700">{dbStats.total_comments.toLocaleString()}</span>
          <span className="text-slate-500">评论</span>
          {Object.entries(dbStats.platforms).map(([k, v]) => (
            <span key={k} className="text-xs bg-slate-100 text-slate-400 rounded px-2 py-0.5">{k}:{v}</span>
          ))}
        </div>
      )}

      <div className="glass-strong rounded-2xl p-5 space-y-4">
        <label className="block text-sm font-semibold text-slate-700">筛选需求描述</label>
        <textarea
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="例：丽江旅游攻略，排除广告和引流内容..."
          rows={3}
          className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 resize-none transition-all"
        />
        <div className="flex flex-wrap gap-2">
          {QUERY_EXAMPLES.map(ex => (
            <button key={ex} onClick={() => setQuery(ex)}
              className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-500 hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50 transition-all">
              {ex.length > 22 ? ex.slice(0, 22) + '…' : ex}
            </button>
          ))}
        </div>
      </div>

      <div className="glass rounded-2xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-700">筛选配置</h2>

        <div className="space-y-1.5">
          <label className="text-xs text-slate-500 font-medium">数据平台</label>
          <div className="flex gap-2">
            {PLATFORM_OPTIONS.map(o => (
              <button key={o.value} onClick={() => setPlatform(o.value)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-all ${platform === o.value ? 'bg-indigo-50 border-indigo-300 text-indigo-700 font-medium' : 'border-slate-200 text-slate-500 hover:border-indigo-200'}`}>
                {o.label}
              </button>
            ))}
          </div>
        </div>

        {scenarios.length > 0 && (
          <div className="space-y-1.5">
            <label className="text-xs text-slate-500 font-medium">过滤场景（留空自动识别）</label>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setScenario('')}
                className={`text-xs px-3 py-1.5 rounded-full border transition-all ${!scenario ? 'bg-indigo-50 border-indigo-300 text-indigo-700 font-medium' : 'border-slate-200 text-slate-500'}`}>
                自动识别
              </button>
              {scenarios.map(s => (
                <button key={s.value} onClick={() => setScenario(s.value)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition-all ${scenario === s.value ? 'bg-indigo-50 border-indigo-300 text-indigo-700 font-medium' : 'border-slate-200 text-slate-500 hover:border-indigo-200'}`}>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-1.5">
          <label className="text-xs text-slate-500 font-medium">最低相关性</label>
          <div className="flex gap-2">
            {RELEVANCE_OPTIONS.map(o => (
              <button key={o.value} onClick={() => setMinRelevance(o.value)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-all ${minRelevance === o.value ? 'bg-indigo-50 border-indigo-300 text-indigo-700 font-medium' : 'border-slate-200 text-slate-500 hover:border-indigo-200'}`}>
                {o.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <label className="text-xs text-slate-500 font-medium whitespace-nowrap">最大帖子数</label>
          <input type="range" min={50} max={10000} step={50} value={maxPosts}
            onChange={e => setMaxPosts(Number(e.target.value))}
            className="flex-1 accent-indigo-500" />
          <span className="text-xs font-semibold text-indigo-600 w-12 text-right">{maxPosts}</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
          ⚠️ {error}
        </div>
      )}

      <button onClick={handleStart} disabled={starting}
        className="w-full py-4 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-2xl transition-all flex items-center justify-center gap-2 text-sm shadow-sm shadow-indigo-200">
        {starting ? (
          <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />提交中…</>
        ) : (
          <><Search size={16} />开始筛选<ChevronRight size={16} /></>
        )}
      </button>
    </div>
  )
}
