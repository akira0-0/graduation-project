import { useState } from 'react'
import { useAppStore } from '../../store/app'
import { rulesApi } from '../../lib/api'
import { ChevronRight, Shield, CheckCircle, XCircle } from 'lucide-react'
import type { Rule } from '../../types'

const TYPE_COLOR: Record<string, string> = {
  keyword:  'bg-blue-50 text-blue-600 border-blue-200',
  regex:    'bg-purple-50 text-purple-600 border-purple-200',
  semantic: 'bg-amber-50 text-amber-600 border-amber-200',
  llm:      'bg-emerald-50 text-emerald-600 border-emerald-200',
}

function RuleCard({ rule }: { rule: Rule }) {
  return (
    <div className="glass rounded-xl p-3 flex items-center gap-3">
      <div className="shrink-0">
        {rule.enabled
          ? <CheckCircle size={16} className="text-emerald-500" />
          : <XCircle size={16} className="text-slate-400" />
        }
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-slate-900 truncate">{rule.name}</div>
        <div className="text-xs text-slate-400 truncate">{rule.content}</div>
      </div>
      <span className={`shrink-0 text-[10px] px-2 py-0.5 rounded border ${TYPE_COLOR[rule.type] ?? 'text-slate-400'}`}>
        {rule.type}
      </span>
    </div>
  )
}

export default function Step3Rules() {
  const { queryIntent, setMatchResult, completeStep, sseStart, ssePush, sseDone, sseError, sseClear } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [rules, setRules] = useState<Rule[]>([])
  const [fetched, setFetched] = useState(false)

  const fetchRules = async () => {
    setLoading(true)
    sseClear()
    sseStart()
    ssePush({ type: 'start', message: '正在加载规则库...', progress: 20 })

    try {
      const scenario = queryIntent?.scenario
      const list = await rulesApi.list({ category: scenario !== 'normal' ? scenario : undefined })
      ssePush({ type: 'matching', message: `⚡ 共加载 ${list.length} 条规则`, progress: 60 })

      // 按场景/关键词初步筛选
      const keywords = queryIntent?.custom_keywords ?? []
      const relevant = keywords.length > 0
        ? list.filter(r =>
            keywords.some(kw =>
              r.content.toLowerCase().includes(kw.toLowerCase()) ||
              r.name.toLowerCase().includes(kw.toLowerCase())
            )
          )
        : list.slice(0, 20)

      ssePush({ type: 'complete', message: `✅ 找到 ${relevant.length} 条相关规则`, progress: 100 })
      sseDone()
      setRules(relevant.length > 0 ? relevant : list.slice(0, 15))
      setFetched(true)

      // 构造 matchResult 供后续步骤使用
      setMatchResult({
        query: queryIntent?.query ?? '',
        scenario: queryIntent?.scenario ?? 'normal',
        matched_rules: relevant.map(r => ({ rule: r, relevance_score: 0.8, match_reason: '规则库匹配' })),
        gap_analysis: { has_gaps: relevant.length < 3, gap_description: '', suggested_keywords: [] },
        generated_rules: [],
        recommendation: '',
        total_matched: relevant.length,
        coverage_score: Math.min(relevant.length / 10, 1),
      })
    } catch (e) {
      sseError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="text-center space-y-1">
        <div className="text-4xl animate-float">⚡</div>
        <h2 className="text-xl font-bold text-slate-900">规则库匹配</h2>
        <p className="text-slate-500 text-xs">基于意图从规则库中检索相关过滤规则</p>
      </div>

      {!fetched ? (
        <div className="glass-strong rounded-3xl p-6 space-y-4">
          <div className="flex items-center gap-3 text-slate-600 text-sm">
            <Shield size={16} className="text-indigo-500" />
            <span>场景：<span className="text-indigo-600 font-medium">{queryIntent?.scenario ?? 'normal'}</span></span>
          </div>
          <button
            onClick={fetchRules}
            disabled={loading}
            className="w-full gradient-bg-primary glow-primary text-white font-semibold py-3 rounded-2xl hover:scale-[1.02] transition-all disabled:opacity-40"
          >
            {loading ? '🔍 检索中...' : '检索规则库'}
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {rules.map(r => <RuleCard key={r.id} rule={r} />)}
          </div>

          <div className="glass rounded-2xl p-3 flex items-center justify-between text-sm">
            <span className="text-slate-500">共匹配 <span className="text-indigo-600 font-bold">{rules.length}</span> 条规则</span>
            <span className="text-slate-500">覆盖度 <span className="text-emerald-600 font-bold">{Math.min(rules.length * 7, 100)}%</span></span>
          </div>

          <button
            onClick={() => completeStep(3)}
            className="w-full flex items-center justify-center gap-2 gradient-bg-primary glow-primary text-white font-semibold py-3 rounded-2xl hover:scale-[1.02] transition-all"
          >
            继续输入内容 <ChevronRight size={16} />
          </button>
        </>
      )}
    </div>
  )
}
