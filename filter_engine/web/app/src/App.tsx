import { useState } from 'react'
import { useAppStore } from './store/app'
import ParticleCanvas from './components/ParticleCanvas'
import PageNav from './components/PageNav'
import RulesPanel from './components/RulesPanel'
import Page1Query from './pages/Page1Query'
import Page2Layer2 from './pages/Page2Layer2'
import Page3Layer3 from './pages/Page3Layer3'
import Page4Results from './pages/Page4Results'

type Tab = 'pipeline' | 'rules'

export default function App() {
  const { currentPage } = useAppStore()
  const [tab, setTab] = useState<Tab>('pipeline')

  const PageComponent = {
    1: Page1Query,
    2: Page2Layer2,
    3: Page3Layer3,
    4: Page4Results,
  }[currentPage]

  return (
    <div className="min-h-screen relative">
      <ParticleCanvas />

      {/* 背景光晕 */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-indigo-200/40 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-violet-200/30 blur-[100px]" />
        <div className="absolute top-[40%] left-[40%] w-[30%] h-[30%] rounded-full bg-cyan-200/20 blur-[80px]" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto px-4 pb-12">
        {/* Header */}
        <header className="pt-8 pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 gradient-bg-primary rounded-2xl flex items-center justify-center glow-primary text-xl">
                🔮
              </div>
              <div>
                <h1 className="text-lg font-bold gradient-primary">Filter Engine</h1>
                <p className="text-xs text-slate-500">智能内容过滤系统 v3.0</p>
              </div>
            </div>
          </div>
        </header>

        {/* Tab 切换 */}
        <div className="flex gap-1 glass rounded-2xl p-1 mb-6 w-fit">
          {([['pipeline', '🔗', 'Pipeline'], ['rules', '⚙️', '规则管理']] as const).map(([id, icon, label]) => (
            <button
              key={id}
              onClick={() => setTab(id as Tab)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                tab === id ? 'gradient-bg-primary text-white shadow-lg' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <span>{icon}</span>{label}
            </button>
          ))}
        </div>

        {/* Pipeline 视图 */}
        {tab === 'pipeline' && (
          <div className="space-y-6">
            <div className="glass rounded-3xl py-4 px-4 overflow-x-auto">
              <PageNav />
            </div>
            <div className="glass-strong rounded-3xl p-6 md:p-8">
              <PageComponent key={currentPage} />
            </div>
          </div>
        )}

        {/* 规则管理视图 */}
        {tab === 'rules' && (
          <div className="glass-strong rounded-3xl p-6">
            <RulesPanel />
          </div>
        )}
      </div>
    </div>
  )
}

