import { useAppStore } from '../../store/app'
import { BarChart2, Tag, AlertCircle, ChevronRight } from 'lucide-react'

const SEVERITY_COLOR: Record<string, string> = {
  relaxed: 'text-emerald-600 bg-emerald-50 border border-emerald-200',
  normal:  'text-indigo-600 bg-indigo-50 border border-indigo-200',
  strict:  'text-orange-600 bg-orange-50 border border-orange-200',
}

const SEVERITY_LABEL: Record<string, string> = {
  relaxed: '宽松',
  normal: '适中',
  strict: '严格',
}

const SCENARIO_EMOJI: Record<string, string> = {
  normal: '🌐', ecommerce: '🛒', social: '📱',
  news: '📰', education: '📚', finance: '💰', medical: '🏥',
}

export default function Step2Intent() {
  const { queryIntent, sse, completeStep } = useAppStore()

  if (!queryIntent && sse.events.length === 0) {
    return (
      <div className="glass rounded-3xl p-8 text-center text-slate-500 animate-slide-up">
        <div className="text-4xl mb-3">🧠</div>
        <p>请先完成 Step 1 的查询输入</p>
      </div>
    )
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="text-center space-y-1">
        <div className="text-4xl animate-float">🧠</div>
        <h2 className="text-xl font-bold text-slate-900">意图分析结果</h2>
        <p className="text-slate-500 text-xs">AI 对你查询意图的理解</p>
      </div>

      {queryIntent && (
        <>
          {/* 主要信息卡片 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="glass-strong rounded-2xl p-4 space-y-1">
              <div className="flex items-center gap-2 text-slate-500 text-xs">
                <BarChart2 size={12} />
                <span>识别场景</span>
              </div>
              <div className="text-slate-900 font-bold text-lg">
                {SCENARIO_EMOJI[queryIntent.scenario] ?? '🌐'} {queryIntent.scenario}
              </div>
            </div>

            <div className="glass-strong rounded-2xl p-4 space-y-1">
              <div className="flex items-center gap-2 text-slate-500 text-xs">
                <AlertCircle size={12} />
                <span>严格程度</span>
              </div>
              <div className={`font-bold text-sm rounded-lg px-2 py-0.5 inline-block ${SEVERITY_COLOR[queryIntent.severity] ?? 'text-slate-600'}`}>
                {SEVERITY_LABEL[queryIntent.severity] ?? queryIntent.severity}
              </div>
            </div>
          </div>

          {/* 置信度 */}
          <div className="glass rounded-2xl p-4 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>识别置信度</span>
              <span className="text-indigo-600 font-mono">{Math.round((queryIntent.confidence ?? 0.8) * 100)}%</span>
            </div>
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full gradient-bg-primary rounded-full transition-all duration-700"
                style={{ width: `${Math.round((queryIntent.confidence ?? 0.8) * 100)}%` }}
              />
            </div>
          </div>

          {/* 关键词 */}
          {queryIntent.custom_keywords?.length > 0 && (
            <div className="glass rounded-2xl p-4 space-y-2">
              <div className="flex items-center gap-2 text-slate-500 text-xs">
                <Tag size={12} />
                <span>提取的关键词</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {queryIntent.custom_keywords.map(kw => (
                  <span key={kw} className="px-2.5 py-1 text-xs bg-indigo-50 rounded-full text-indigo-600 border border-indigo-200 font-medium">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 额外关注类别 */}
          {queryIntent.extra_categories?.length > 0 && (
            <div className="glass rounded-2xl p-4 space-y-2">
              <div className="text-slate-500 text-xs mb-2">额外关注类别</div>
              <div className="flex flex-wrap gap-2">
                {queryIntent.extra_categories.map(cat => (
                  <span key={cat} className="px-2.5 py-1 text-xs bg-amber-50 rounded-full text-amber-700 border border-amber-200">
                    {cat}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 下一步 */}
          <button
            onClick={() => completeStep(2)}
            className="w-full flex items-center justify-center gap-2 gradient-bg-primary glow-primary text-white font-semibold py-3 rounded-2xl hover:scale-[1.02] transition-all"
          >
            进入规则匹配 <ChevronRight size={16} />
          </button>
        </>
      )}
    </div>
  )
}
