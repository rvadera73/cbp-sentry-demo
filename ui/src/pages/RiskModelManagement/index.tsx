/**
 * Risk Model Management Tab - Screen Components
 *
 * Phase 1 Implementation: CBP Risk Model (v2.1 → v3.0)
 * Purpose: End-to-end lifecycle management for risk scoring models
 *
 * All components are TypeScript functional components with stub implementations
 * ready for API integration via the backend REST API.
 */

import React, { useState } from 'react'
import {
  BarChart3,
  TrendingUp,
  Settings,
  CheckCircle,
  Activity,
  Zap,
  GitBranch,
  AlertCircle,
  ChevronRight,
  Target,
} from 'lucide-react'
import Dashboard from './Dashboard'
import ModelVersions from './ModelVersions'
import TrainingHistory from './TrainingHistory'
import PerformanceMetrics from './PerformanceMetrics'
import DataDriftMonitoring from './DataDriftMonitoring'
import PredictionExplanations from './PredictionExplanations'
import ModelApprovals from './ModelApprovals'
import RetrainingConfig from './RetrainingConfig'
import PerformanceMeasures from './PerformanceMeasures'

// Sub-component exports for barrel imports
export { default as Dashboard } from './Dashboard'
export { default as ModelVersions } from './ModelVersions'
export { default as TrainingHistory } from './TrainingHistory'
export { default as PerformanceMetrics } from './PerformanceMetrics'
export { default as DataDriftMonitoring } from './DataDriftMonitoring'
export { default as PredictionExplanations } from './PredictionExplanations'
export { default as ModelApprovals } from './ModelApprovals'
export { default as RetrainingConfig } from './RetrainingConfig'
export { default as PerformanceMeasures } from './PerformanceMeasures'

interface SubTab {
  id: string
  label: string
  icon: React.ReactNode
  component: React.ReactNode
  description: string
}

function RiskModelManagement() {
  const [activeSubTab, setActiveSubTab] = useState('dashboard')

  const subTabs: SubTab[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: <BarChart3 className="w-4 h-4" />,
      component: <Dashboard />,
      description: 'Model overview & status',
    },
    {
      id: 'versions',
      label: 'Model Versions',
      icon: <GitBranch className="w-4 h-4" />,
      component: <ModelVersions />,
      description: 'Version control & rollback',
    },
    {
      id: 'training',
      label: 'Training History',
      icon: <Activity className="w-4 h-4" />,
      component: <TrainingHistory />,
      description: 'Training runs & logs',
    },
    {
      id: 'performance',
      label: 'Performance Metrics',
      icon: <TrendingUp className="w-4 h-4" />,
      component: <PerformanceMetrics />,
      description: 'Accuracy & validation',
    },
    {
      id: 'drift',
      label: 'Data Drift',
      icon: <AlertCircle className="w-4 h-4" />,
      component: <DataDriftMonitoring />,
      description: 'Production data quality',
    },
    {
      id: 'explanations',
      label: 'Prediction Explanations',
      icon: <Zap className="w-4 h-4" />,
      component: <PredictionExplanations />,
      description: 'Feature importance & SHAP',
    },
    {
      id: 'approvals',
      label: 'Model Approvals',
      icon: <CheckCircle className="w-4 h-4" />,
      component: <ModelApprovals />,
      description: 'Deployment authorization',
    },
    {
      id: 'config',
      label: 'Retraining Config',
      icon: <Settings className="w-4 h-4" />,
      component: <RetrainingConfig />,
      description: 'Schedule & parameters',
    },
    {
      id: 'performance-measures',
      label: 'Performance Measures',
      icon: <Target className="w-4 h-4" />,
      component: <PerformanceMeasures />,
      description: 'CBP gate requirements & timeline',
    },
  ]

  const activeTab = subTabs.find(tab => tab.id === activeSubTab)

  return (
    <div className="flex flex-col h-full bg-[#F7F9FC]">
      {/* Page Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-[#1B1B1B] mb-1">Risk Model Management</h1>
          <p className="text-sm text-slate-600">CBP Risk Scoring Engine - Lifecycle Management</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sub-Navigation Sidebar */}
        <aside className="w-64 bg-white border-r border-slate-200 overflow-y-auto">
          <nav className="p-4 space-y-1">
            {subTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                className={`w-full flex items-start gap-3 px-3 py-3 rounded-lg transition-all text-left text-sm ${
                  activeSubTab === tab.id
                    ? 'bg-blue-50 border border-blue-200'
                    : 'text-slate-700 hover:bg-slate-50 border border-transparent'
                }`}
              >
                <div
                  className={`flex-shrink-0 mt-0.5 ${
                    activeSubTab === tab.id ? 'text-blue-600' : 'text-slate-400'
                  }`}
                >
                  {tab.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div
                    className={`font-semibold ${
                      activeSubTab === tab.id ? 'text-blue-900' : 'text-slate-900'
                    }`}
                  >
                    {tab.label}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">{tab.description}</div>
                </div>
                {activeSubTab === tab.id && (
                  <ChevronRight className="w-4 h-4 text-blue-600 flex-shrink-0" />
                )}
              </button>
            ))}
          </nav>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto">
          <div className="p-6">
            {activeTab && (
              <div>
                {/* Sub-page Header */}
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="text-blue-600">{activeTab.icon}</div>
                    <h2 className="text-2xl font-bold text-slate-900">{activeTab.label}</h2>
                  </div>
                  <p className="text-slate-600">{activeTab.description}</p>
                </div>

                {/* Component Content */}
                <div className="max-w-7xl">
                  {activeTab.component}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

export default RiskModelManagement
