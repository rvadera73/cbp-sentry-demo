import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
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
  const location = useLocation()
  const navigate = useNavigate()

  const currentStepIndex = steps.findIndex(s => s.path === location.pathname)

  return (
    <aside className="w-64 bg-white border-r border-sentry-slate p-4">
      <h2 className="text-lg font-bold text-sentry-navy mb-6">Demo Workflow</h2>
      <nav className="space-y-3">
        {steps.map((step, idx) => (
          <button
            key={step.path}
            onClick={() => navigate(step.path)}
            className={clsx(
              'w-full text-left p-3 rounded transition-all',
              idx <= currentStepIndex
                ? 'bg-sentry-teal text-white font-semibold'
                : 'bg-gray-100 text-sentry-slate cursor-not-allowed opacity-50'
            )}
            disabled={idx > currentStepIndex}
          >
            <div className="flex items-center gap-3">
              <div
                className={clsx(
                  'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold',
                  idx <= currentStepIndex
                    ? 'bg-white text-sentry-teal'
                    : 'bg-gray-300 text-gray-500'
                )}
              >
                {step.icon}
              </div>
              <span className="text-sm">{step.label}</span>
            </div>
          </button>
        ))}
      </nav>
    </aside>
  )
}

export default DemoStepper
