import { useState } from 'react'
import { useAppStore } from '../../store/app'
import { Plus, Trash2, ChevronRight, Upload } from 'lucide-react'

const SAMPLE_TEXTS = [
  '丽江古城真的很美，推荐大家去玩！束河古镇也不错，比古城少很多游客',
  '【限时优惠】丽江民宿特价198元/晚，包含早餐，扫码立享9折！',
  '我在丽江住了一周，分享几个私藏景点：玉龙雪山日出最美，建议早上5点出发',
  '丽江旅游攻略大全，包含交通、住宿、美食，建议收藏！\n点击购买专业攻略PDF',
  '第一次来丽江，不知道有什么必去的地方吗？求推荐',
  '丽江的纳西古乐真的很有特色，在四方街随处可以听到，免费的那种',
]

export default function Step4Contents() {
  const { setContents, completeStep } = useAppStore()
  const [texts, setTexts] = useState<string[]>([''])

  const updateText = (i: number, val: string) => {
    const next = [...texts]
    next[i] = val
    setTexts(next)
  }

  const addRow = () => setTexts(t => [...t, ''])
  const removeRow = (i: number) => setTexts(t => t.filter((_, idx) => idx !== i))

  const loadSamples = () => setTexts(SAMPLE_TEXTS)

  const handleNext = () => {
    const valid = texts.filter(t => t.trim())
    if (valid.length === 0) return
    setContents(valid)
    completeStep(4)
  }

  const validCount = texts.filter(t => t.trim()).length

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="text-center space-y-1">
        <div className="text-4xl animate-float">📝</div>
        <h2 className="text-xl font-bold text-slate-900">输入待筛选内容</h2>
        <p className="text-slate-500 text-xs">每行一条，支持批量粘贴</p>
      </div>

      <div className="glass-strong rounded-3xl p-5 space-y-3">
        {/* 快速操作 */}
        <div className="flex gap-2">
          <button
            onClick={loadSamples}
            className="flex items-center gap-1.5 glass rounded-xl px-3 py-2 text-xs text-slate-500 hover:text-slate-900 transition-colors"
          >
            <Upload size={12} />
            加载示例内容
          </button>
          <button
            onClick={addRow}
            className="flex items-center gap-1.5 glass rounded-xl px-3 py-2 text-xs text-slate-500 hover:text-slate-900 transition-colors"
          >
            <Plus size={12} />
            添加一行
          </button>
        </div>

        {/* 文本输入列表 */}
        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
          {texts.map((text, i) => (
            <div key={i} className="flex gap-2 items-start">
              <span className="text-slate-400 text-xs mt-3 w-5 text-right shrink-0">{i + 1}</span>
              <textarea
                value={text}
                onChange={e => updateText(i, e.target.value)}
                placeholder={`第 ${i + 1} 条内容...`}
                rows={2}
                className="
                  flex-1 bg-white border border-slate-200 rounded-xl
                  px-3 py-2 text-slate-900 placeholder-slate-400
                  focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100
                  resize-none text-sm leading-relaxed transition-all
                "
              />
              {texts.length > 1 && (
                <button
                  onClick={() => removeRow(i)}
                  className="mt-2.5 p-1.5 text-slate-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>已输入 <span className="text-indigo-600">{validCount}</span> 条有效内容</span>
          {validCount > 0 && <span className="text-emerald-600">✓ 可以进行过滤</span>}
        </div>

        <button
          onClick={handleNext}
          disabled={validCount === 0}
          className="w-full flex items-center justify-center gap-2 gradient-bg-primary glow-primary text-white font-semibold py-3 rounded-2xl hover:scale-[1.02] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          开始智能过滤 <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}
