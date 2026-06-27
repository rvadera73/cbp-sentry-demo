/**
 * Risk Model Management Tab V2 — Complete Implementation
 * Horizontal tabs at top, single content pane below.
 *
 * Each tab is fully self-contained and fetches its own data directly from the
 * cbp-risk-engine API (/metrics/*, /models, /jobs, /feedback/*). This parent
 * only owns tab navigation — no shared data fetching, no hardcoded fallbacks.
 */

import React, { useState } from 'react'
import {
  BarChart3,
  TrendingUp,
  GitBranch,
  Activity,
  Zap,
} from 'lucide-react'
import { CBPColors } from '../../styles/CBPDesignSystem'
import OverviewTab from './tabs/OverviewTab'
import ModelRegistryTab from './tabs/ModelRegistryTab'
import PerformanceTab from './tabs/PerformanceTab'
import TrainingDataTab from './tabs/TrainingDataTab'
import MonitoringTab from './tabs/MonitoringTab'

const RiskModelManagementV2: React.FC = () => {
  const [activeTabId, setActiveTabId] = useState('overview')

  const tabs = [
    { id: 'overview', label: 'Overview', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'registry', label: 'Model Registry', icon: <GitBranch className="w-4 h-4" /> },
    { id: 'performance', label: 'Performance', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'training', label: 'Training & Data', icon: <Activity className="w-4 h-4" /> },
    { id: 'monitoring', label: 'Monitoring', icon: <Zap className="w-4 h-4" /> },
  ]

  const activeTab = tabs.find(t => t.id === activeTabId)

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b-2" style={{ borderColor: CBPColors.primary }}>
        <div className="max-w-7xl mx-auto px-6 py-4">
          <h1 className="text-3xl font-bold text-slate-900">Risk Model Management</h1>
        </div>
      </div>

      {/* Horizontal Tabs */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex overflow-x-auto">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTabId(tab.id)}
                className={`flex items-center gap-2 px-4 py-4 text-sm font-medium whitespace-nowrap border-b-2 transition-all ${
                  activeTabId === tab.id
                    ? 'text-[#005EA2] border-[#005EA2]'
                    : 'text-slate-600 hover:text-slate-900 border-transparent'
                }`}
              >
                <span className={activeTabId === tab.id ? 'text-[#005EA2]' : 'text-slate-400'}>
                  {tab.icon}
                </span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto bg-white">
        <div className="max-w-7xl mx-auto px-6 py-6">
          {activeTab && (
            <div>
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[#005EA2]">{activeTab.icon}</span>
                  <h2 className="text-2xl font-bold text-slate-900">{activeTab.label}</h2>
                </div>
              </div>

              {activeTabId === 'overview' && <OverviewTab />}
              {activeTabId === 'registry' && <ModelRegistryTab />}
              {activeTabId === 'performance' && <PerformanceTab />}
              {activeTabId === 'training' && <TrainingDataTab />}
              {activeTabId === 'monitoring' && <MonitoringTab />}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default RiskModelManagementV2
