import { useState, useEffect } from 'react'
import { Search, Zap, ChevronDown } from 'lucide-react'
import { useAppStore } from '../../store/app'
import { queryApi } from '../../lib/api'

const PLACEHOLDERS = [
  '帮我找丽江好玩的地方，过滤掉广告和营销号',
  '小红书上有关护肤品的真实使用评价，排除广告',
  '寻找关于考研备考的经验分享，不要培训班推广',
  '找一下成都美食推荐，过滤掉团购链接',
  '职场经验分享类内容，屏蔽猎头招聘广告',
]

const SCENARIOS = [
  { value: 'normal', label: '🌐 通用', desc: '默认规则' },
  { value: 'ecommerce', label: '🛒 电商', desc: '商品评论场景' },
  { value: 'social', label: '📱 社交', desc: '社交媒体内容' },
  { value: 'news', label: '📰 新闻', desc: '新闻资讯场景' },
  { value: 'education', label: '📚 教育', desc: '教育学习内容' },
  { value: 'finance', label: '💰 金融', desc: '金融投资场景' },
  { value: 'medical', label: '🏥 医疗', desc: '健康医疗内容' },
]

export default function Step1Query() {
  const { query, scenario, setQuery, setScenario, setQueryIntent, completeStep, sseStart, ssePush, sseDone, sseError, sseClear } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [phIdx, setPhIdx] = useState(0)
  const [showScenario, setShowScenario] = useState(false)

  // Placeholder 轮换
  useEffect(() => {
    const t = setInterval(() => setPhIdx(i => (i + 1) % PLACEHOLDERS.length), 3500)
    return () => clearInterval(t)
  }, [])

  const handleSubmit = async () => {
    if (!query.trim()) return
    setLoading(true)
    sseClear()
    sseStart()
    ssePush({ type: 'start', message: '开始分析查询意图...', progress: 10 })

    try {
      ssePush({ type: 'analyzing', message: '🧠 正在解析场景和语义...', progress: 40 })
      const intent = await queryApi.analyze(query)
      ssePush({ type: 'complete', message: `✅ 识别到场景：${intent.scenario}，严格度：${intent.severity}`, progress: 100 })
      sseDone()
      setQueryIntent(intent)
      if (intent.scenario && intent.scenario !== 'normal') setScenario(intent.scenario)
      completeStep(1)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      sseError(msg)
    } finally {
      setLoading(false)
    }
  }

  const selectedScene = SCENARIOS.find(s => s.value === scenario)

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="text-center space-y-2">
        <div className="text-5xl animate-float">🔍</div>
        <h2 className="text-2xl font-bold text-slate-900">描述你的过滤需求</h2>
        <p className="text-slate-500 text-sm">用自然语言告诉 AI 你想保留什么、过滤什么</p>
      </div>

      <div className="glass-strong rounded-3xl p-6 space-y-4">
        {/* 查询输入 */}
        <div className="relative">
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={PLACEHOLDERS[phIdx]}
            rows={4}
            className="
              w-full bg-white border border-slate-200 rounded-2xl
              px-4 py-3 text-slate-900 placeholder-slate-400
              focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100
              resize-none text-sm leading-relaxed transition-all duration-200
            "
          />
          <div className="absolute bottom-3 right-3 text-xs text-slate-400">
            {query.length}/2000
          </div>
        </div>

        {/* 场景选择 */}
        <div className="relative">
          <button
            onClick={() => setShowScenario(v => !v)}
            className="flex items-center gap-2 glass rounded-xl px-4 py-2.5 text-sm text-slate-600 hover:text-slate-900 transition-colors w-full"
          >
            <span className="font-medium">{selectedScene?.label ?? '🌐 通用'}</span>
            <span className="text-slate-400 text-xs flex-1 text-left">{selectedScene?.desc}</span>
            <ChevronDown size={14} className={`transition-transform ${showScenario ? 'rotate-180' : ''}`} />
          </button>

          {showScenario && (
            <div className="absolute top-full mt-2 w-full glass-strong rounded-2xl overflow-hidden z-20 animate-slide-up">
              {SCENARIOS.map(s => (
                <button
                  key={s.value}
                  onClick={() => { setScenario(s.value); setShowScenario(false) }}
                  className={`
                    w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors
                    ${scenario === s.value ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}
                  `}
                >
                  <span>{s.label}</span>
                  <span className="text-xs text-slate-400">{s.desc}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 提交按钮 */}
        <button
          onClick={handleSubmit}
          disabled={!query.trim() || loading}
          className="
            w-full flex items-center justify-center gap-2
            gradient-bg-primary glow-primary
            text-white font-semibold py-3 rounded-2xl
            transition-all duration-200
            disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none
            hover:scale-[1.02] active:scale-[0.98]
          "
        >
          {loading ? (
            <span className="animate-spin-slow inline-block">⚙️</span>
          ) : (
            <Search size={16} />
          )}
          {loading ? '分析中...' : '开始分析意图'}
          {!loading && <Zap size={14} className="text-yellow-300" />}
        </button>
      </div>
    </div>
  )
}
