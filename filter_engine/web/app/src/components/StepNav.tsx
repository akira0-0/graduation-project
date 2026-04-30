import { useAppStore, STEP_CONFIGS } from '../store/app'
import type { StepId } from '../types'
import { CheckCircle, Lock } from 'lucide-react'

export default function StepNav() {
  const { currentStep, unlockedSteps, completedSteps, goToStep } = useAppStore()

  return (
    <nav className="flex items-center justify-center gap-0 py-6 overflow-x-auto">
      {STEP_CONFIGS.map((step, idx) => {
        const unlocked = unlockedSteps.has(step.id)
        const completed = completedSteps.has(step.id)
        const active = currentStep === step.id
        const isLast = idx === STEP_CONFIGS.length - 1

        return (
          <div key={step.id} className="flex items-center">
            {/* 步骤按钮 */}
            <button
              onClick={() => unlocked && goToStep(step.id as StepId)}
              disabled={!unlocked}
              className={`
                relative flex flex-col items-center gap-1.5 px-4 py-2 rounded-2xl
                transition-all duration-300 group
                ${active
                  ? 'glass-strong glow-primary scale-105'
                  : unlocked
                    ? 'glass hover:glass-strong cursor-pointer'
                    : 'opacity-40 cursor-not-allowed'
                }
              `}
            >
              {/* 圆形图标区 */}
              <div className={`
                relative w-10 h-10 rounded-full flex items-center justify-center text-lg
                transition-all duration-300
                ${active ? 'gradient-bg-primary shadow-lg' : 'bg-slate-100'}
              `}>
                {completed
                  ? <CheckCircle size={18} className="text-emerald-500" />
                  : !unlocked
                    ? <Lock size={14} className="text-slate-400" />
                    : <span>{step.emoji}</span>
                }

                {/* 活跃光环 */}
                {active && (
                  <span className="absolute inset-0 rounded-full animate-pulse-ring border border-indigo-500/60" />
                )}
              </div>

              {/* 文字 */}
              <div className="text-center min-w-[64px]">
                <div className={`text-xs font-semibold ${active ? 'text-indigo-600' : 'text-slate-400'}`}>
                  Step {step.id}
                </div>
                <div className={`text-[11px] leading-tight ${active ? 'text-slate-900' : 'text-slate-500'}`}>
                  {step.title}
                </div>
              </div>
            </button>

            {/* 连接线 */}
            {!isLast && (
              <div className={`
                w-8 h-px mx-1 transition-all duration-500
                ${completedSteps.has(step.id)
                  ? 'bg-indigo-400'
                  : 'bg-slate-200'
                }
              `} />
            )}
          </div>
        )
      })}
    </nav>
  )
}
