import { useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, XCircle, ArrowRight } from 'lucide-react'
import { useAppStore } from '../store/app'
import { filterApi } from '../lib/api'
import ProgressBar from '../components/ProgressBar'
import type { L2ThoughtTrace } from '../types'

function ThoughtStep({ title, items, color, badge }: { title: string; items: string[]; color: string; badge: string }) {
  const [open, setOpen] = useState(true)
  if (!items || items.length === 0) return null
  return (
    <div className={`border-2 ${color} rounded-xl overflow-hidden`}>
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-50 transition-colors">
        <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${badge}`}>{title}</span>
        {open ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
      </button>
      {open && (
        <ul className="px-4 pb-3 space-y-1.5">
          {items.map((item, i) => (
            <li key={i} className="text-xs text-slate-600 leading-relaxed flex gap-2">
              <span className="text-slate-300 shrink-0">▶</span><span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function ThinkingChain({ trace }: { trace: L2ThoughtTrace }) {
  return (
    <div className="space-y-2">
      <ThoughtStep title="步骤一：意图提取" items={trace.step1_extraction ?? []} color="border-blue-300" badge="bg-blue-100 text-blue-700" />
      <ThoughtStep title="步骤二：规则匹配" items={trace.step2_rule_match ?? []} color="border-indigo-300" badge="bg-indigo-100 text-indigo-700" />
      <ThoughtStep title="步骤三：缺口分析" items={trace.step3_gap_analysis ?? []} color="border-amber-300" badge="bg-amber-100 text-amber-700" />
      <ThoughtStep title="步骤四：规则生成" items={trace.step4_generation ?? []} color="border-emerald-300" badge="bg-emerald-100 text-emerald-700" />
    </div>
  )
}

export default function Page2Layer2() {
  const {
    sessionId, sessionStatus, sessionProgress, sessionStats,
    layer2Info, sessionError,
    updateSessionStatus, setPollingActive,
    unlockPage, goToPage,
  } = useAppStore()

  const [l3Starting, setL3Starting] = useState(false)

  // 轮询
  useEffect(() => {
    if (!sessionId || sessionStatus === 'completed' || sessionStatus === 'failed') return
    setPollingActive(true)
    const timer = setInterval(async () => {
      try {
        const res = await filterApi.pollStatus(sessionId)
        updateSessionStatus(res.status, res.progress, res.stats, res.layer2_info, res.error ?? null)
        if (res.status === 'completed' || res.status === 'failed') {
          clearInterval(timer)
          setPollingActive(false)
        }
      } catch { /* ignore */ }
    }, 3000)
    return () => { clearInterval(timer); setPollingActive(false) }
  }, [sessionId])

  const handleGoLayer3 = () => {
    if (sessionStatus !== 'completed') return
    setL3Starting(true)
    unlockPage(3)
    goToPage(3)
  }

  if (!sessionId) {
    return <div className="max-w-2xl mx-auto text-center text-slate-400 py-12">请先在第一页输入查询并开始筛选</div>
  }

  const l2 = layer2Info
  const isProcessing = sessionStatus === 'processing' || sessionStatus === 'idle'

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center space-y-1">
        <h2 className="text-xl font-bold text-slate-900">⚡ Layer-2 过滤</h2>
        <p className="text-slate-500 text-sm">场景规则匹配 + LLM 缺口分析</p>
      </div>

      {/* 进度条 */}
      <ProgressBar loading={isProcessing} progress={sessionProgress}
        label={isProcessing ? 'LLM 场景分析中，请稍候…' : 'Layer-2 分析完成'} />

      {/* 统计 */}
      {sessionStats && (
        <div className="grid grid-cols-3 gap-3">
          <div className="glass rounded-xl p-3 text-center">
            <div className="text-xl font-bold text-slate-900">{sessionStats.l1_total_posts}</div>
            <div className="text-xs text-slate-500 mt-0.5">L1 输入</div>
          </div>
          <div className="glass rounded-xl p-3 text-center">
            <div className="text-xl font-bold text-emerald-600">{sessionStats.l2_passed_posts}</div>
            <div className="text-xs text-slate-500 mt-0.5">L2 通过</div>
          </div>
          <div className="glass rounded-xl p-3 text-center">
            <div className="text-xl font-bold text-violet-600">{sessionStats.l3_passed_posts}</div>
            <div className="text-xs text-slate-500 mt-0.5">L3 通过</div>
          </div>
        </div>
      )}

      {/* 场景信息 */}
      {l2 && (
        <div className="glass rounded-xl px-4 py-3 flex flex-wrap items-center gap-3">
          <span className="text-xs text-slate-500">识别场景：</span>
          <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-1 rounded-full border border-indigo-200">
            {l2.scenario || '通用'}
          </span>
          <span className="text-xs text-slate-500">覆盖度：</span>
          <span className={`text-xs font-semibold px-2 py-1 rounded-full border ${
            l2.scenario_coverage === 'full' ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
            : 'bg-amber-50 text-amber-700 border-amber-200'
          }`}>
            {l2.scenario_coverage === 'full' ? '充分覆盖' : '需要补充'}
          </span>
          {l2.layer2_elapsed_s > 0 && (
            <span className="text-xs text-slate-400 ml-auto">{l2.layer2_elapsed_s.toFixed(1)}s</span>
          )}
        </div>
      )}

      {/* 思维链 */}
      {l2?.thought_trace && (
        <div className="glass-strong rounded-2xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-slate-800">🧠 LLM 思维链</h3>
          <ThinkingChain trace={l2.thought_trace} />
        </div>
      )}

      {/* 匹配规则 */}
      {l2 && l2.matched_rules.length > 0 && (
        <div className="glass-strong rounded-2xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-slate-800">📚 命中规则库 ({l2.matched_rules.length} 条)</h3>
          <div className="space-y-2">
            {l2.matched_rules.map((r, i) => (
              <div key={i} className="flex items-start gap-3 bg-white rounded-xl px-3 py-2.5 border border-slate-100">
                <span className={`shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                  r.purpose === 'select' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-600 border-red-200'
                }`}>{r.purpose === 'select' ? '保留' : '过滤'}</span>
                <div>
                  <div className="text-xs font-semibold text-slate-800">{r.rule_name}</div>
                  {r.match_reason && <div className="text-[11px] text-slate-500 mt-0.5">{r.match_reason}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 缺口规则 */}
      {l2 && l2.gap_rules.length > 0 && (
        <div className="glass-strong rounded-2xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-slate-800">✨ LLM 补充规则 ({l2.gap_rules.length} 条)</h3>
          <div className="space-y-2">
            {l2.gap_rules.map((r, i) => (
              <div key={i} className="bg-white rounded-xl px-3 py-2.5 border border-slate-100 space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    r.purpose === 'select' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>{r.purpose === 'select' ? '保留' : '过滤'} · {r.type}</span>
                  <span className="text-xs font-semibold text-slate-800">{r.name}</span>
                </div>
                {r.description && <div className="text-[11px] text-slate-500">{r.description}</div>}
                {r.content.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {r.content.map((c, j) => (
                      <span key={j} className="text-[10px] px-2 py-0.5 bg-slate-50 border border-slate-200 rounded text-slate-600">{c}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 错误 */}
      {sessionError && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600 flex items-center gap-2">
          <XCircle size={14} />{sessionError}
        </div>
      )}

      {/* 进入 Layer-3 */}
      {sessionStatus === 'completed' && (
        <button onClick={handleGoLayer3} disabled={l3Starting}
          className="w-full py-4 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white font-semibold rounded-2xl transition-all flex items-center justify-center gap-2 text-sm shadow-sm shadow-indigo-200">
          {l3Starting
            ? <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />跳转中…</>
            : <>进入 Layer-3 数据集<ArrowRight size={16} /></>
          }
        </button>
      )}

      {isProcessing && (
        <div className="glass rounded-2xl p-6 text-center text-slate-400 text-sm animate-pulse">
          ⏳ 后台正在处理，每3秒自动刷新…
        </div>
      )}
    </div>
  )
}
