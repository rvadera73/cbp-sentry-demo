import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkflow } from '../../context/WorkflowContext'
import clsx from 'clsx'

interface Step {
  path: string
  label: string
  icon: string
}

const steps: Step[] = [
  { path: '/ingest', label: 'Manifest Ingest', icon: '1' },
  { path: '/entity-resolution', label: 'Entity Resolution', icon: '2' },
  { path: '/scoring', label: 'Risk Scoring', icon: '3' },
  { path: '/graph', label: 'Knowledge Graph', icon: '4' },
]

const DemoStepper: React.FC = () => {
  const navigate = useNavigate()
  const { state } = useWorkflow()

  const isStepUnlocked = (stepIndex: number): boolean => {
    if (stepIndex === 0) return true // Step 1 always unlocked
    if (stepIndex === 1) return state.manifestId !== null // Step 2: needs manifestId
    if (stepIndex === 2) return state.entitiesResolved // Step 3: needs entities resolved
    if (stepIndex === 3) return state.scoringComplete // Step 4: needs scoring complete
    return false
  }

  const isStepComplete = (stepIndex: number): boolean => {
    if (stepIndex === 0) return state.manifestId !== null
    if (stepIndex === 1) return state.entities !== null && state.entities.length > 0
    if (stepIndex === 2) return state.score !== null
    if (stepIndex === 3) return state.referralId !== null
    return false
  }

  return (
    <aside className="w-64 bg-white border-r border-sentry-slate p-4">
      <h2 className="text-lg font-bold text-sentry-navy mb-6">Demo Workflow</h2>
      <nav className="space-y-3">
        {steps.map((step, idx) => {
          const unlocked = isStepUnlocked(idx)
          const complete = isStepComplete(idx)

          return (
            <button
              key={step.path}
              onClick={() => unlocked && navigate(step.path)}
              className={clsx(
                'w-full text-left p-3 rounded transition-all flex items-center gap-3',
                unlocked
                  ? 'hover:bg-gray-50 cursor-pointer'
                  : 'bg-gray-100 cursor-not-allowed opacity-50'
              )}
              disabled={!unlocked}
            >
              <div
                className={clsx(
                  'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0',
                  unlocked
                    ? complete
                      ? 'bg-sentry-teal text-white'
                      : 'bg-sentry-teal text-white'
                    : 'bg-gray-300 text-gray-500'
                )}
              >
                {complete ? '✓' : step.icon}
              </div>
              <div className="flex-1">
                <p className={clsx('text-sm font-semibold', unlocked ? 'text-sentry-navy' : 'text-sentry-slate')}>
                  {step.label}
                </p>
                {!unlocked && (
                  <p className="text-xs text-gray-500 mt-1">
                    {idx === 1 && 'Unlock by uploading manifest'}
                    {idx === 2 && 'Unlock after entity resolution'}
                    {idx === 3 && 'Unlock after scoring'}
                  </p>
                )}
              </div>
            </button>
          )
        })}
      </nav>
    </aside>
  )
}

export default DemoStepper
