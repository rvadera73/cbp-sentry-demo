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
import { CBPColors, CBPTypography, CBPTabs } from '../../styles/CBPDesignSystem'
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
        <div className="max-w-7xl mx-auto px-6 py-3">
          <h1 className={CBPTypography.pageTitle}>Risk Model Management</h1>
        </div>
      </div>

      {/* Horizontal Tabs */}
      <div className="bg-white">
        <div className="max-w-7xl mx-auto px-2">
          <div className={CBPTabs.bar}>
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTabId(tab.id)}
                className={`${CBPTabs.button} ${activeTabId === tab.id ? CBPTabs.active : CBPTabs.inactive}`}
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
        <div className="max-w-7xl mx-auto px-6 py-5">
          {activeTab && (
            <div>
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
