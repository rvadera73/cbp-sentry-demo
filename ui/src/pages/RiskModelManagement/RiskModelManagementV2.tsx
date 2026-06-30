/**
 * Risk Model Management Tab V2.
 * Horizontal tabs at top, single content pane below, plus a MODEL SELECTOR in
 * the header. Selecting a model lifts `selectedVersion` to this container and
 * passes it to every tab; each tab refetches scoped to that version, so the
 * dataset refreshes automatically when you toggle between models (e.g. the
 * Gate-1 production model vs the Gate-2 candidate).
 *
 * Tabs fetch their own data from cbp-risk-engine (/models, /metrics/*, /jobs,
 * /feedback/*); this parent owns tab navigation + the selected model.
 */

import React, { useEffect, useState } from 'react'
import {
  BarChart3,
  TrendingUp,
  GitBranch,
  Activity,
  Zap,
  Layers,
} from 'lucide-react'
import { CBPColors, CBPTypography, CBPTabs } from '../../styles/CBPDesignSystem'
import { getMLOpsEndpoint } from '../../services/apiUrl'
import OverviewTab from './tabs/OverviewTab'
import ModelRegistryTab from './tabs/ModelRegistryTab'
import PerformanceTab from './tabs/PerformanceTab'
import TrainingDataTab from './tabs/TrainingDataTab'
import MonitoringTab from './tabs/MonitoringTab'

export interface ModelOption {
  version: string
  status: string
  maturity?: number | null
  framework?: string | null
}

const statusOrder = (s: string) => (s === 'production' ? 0 : s === 'staging' ? 1 : s === 'candidate' ? 2 : 3)

const RiskModelManagementV2: React.FC = () => {
  const [activeTabId, setActiveTabId] = useState('overview')
  const [models, setModels] = useState<ModelOption[]>([])
  const [selectedVersion, setSelectedVersion] = useState<string>('')

  // Load the registry once for the model selector; default to the production model.
  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const res = await fetch(getMLOpsEndpoint('/models'))
        if (!res.ok) return
        const data = await res.json()
        const vs: ModelOption[] = (Array.isArray(data.versions) ? data.versions : []).map((m: any) => ({
          version: String(m.version ?? m.model_id ?? ''),
          status: String(m.status ?? (m.is_production ? 'production' : 'registered')),
          maturity: m.maturity_pct ?? m.metadata?.maturity_pct ?? null,
          framework: m.framework ?? m.metadata?.framework ?? null,
        })).filter((m: ModelOption) => m.version && m.status !== 'deprecated')
        vs.sort((a, b) => statusOrder(a.status) - statusOrder(b.status))
        if (!active) return
        setModels(vs)
        setSelectedVersion(prev => prev || (vs.find(v => v.status === 'production')?.version ?? vs[0]?.version ?? ''))
      } catch { /* selector simply stays empty; tabs fall back to production */ }
    })()
    return () => { active = false }
  }, [])

  const tabs = [
    { id: 'overview', label: 'Overview', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'registry', label: 'Model Registry', icon: <GitBranch className="w-4 h-4" /> },
    { id: 'performance', label: 'Performance', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'training', label: 'Training & Data', icon: <Activity className="w-4 h-4" /> },
    { id: 'monitoring', label: 'Monitoring', icon: <Zap className="w-4 h-4" /> },
  ]

  const activeTab = tabs.find(t => t.id === activeTabId)
  const selectedModel = models.find(m => m.version === selectedVersion)

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header + model selector */}
      <div className="bg-white border-b-2" style={{ borderColor: CBPColors.primary }}>
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
          <h1 className={CBPTypography.pageTitle}>Risk Model Management</h1>
          <label className="flex items-center gap-2 text-[12px] font-semibold text-[#5C5C5C]">
            <Layers className="w-4 h-4 text-[#005EA2]" />
            MODEL
            <select
              value={selectedVersion}
              onChange={e => setSelectedVersion(e.target.value)}
              className="bg-white border border-[#D0D7DE] rounded px-2 py-1 text-[12px] font-mono text-[#0B1F33] focus:outline-none focus:ring-2 focus:ring-[#005EA2]"
              aria-label="Active model version"
            >
              {models.length === 0 && <option value="">production</option>}
              {models.map(m => (
                <option key={m.version} value={m.version}>
                  v{m.version} · {m.status}{m.maturity != null ? ` · ${m.maturity}%` : ''}
                </option>
              ))}
            </select>
            {selectedModel && (
              <span className="text-[10px] font-normal text-[#5C5C5C]">{selectedModel.framework || ''}</span>
            )}
          </label>
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

      {/* Content — every tab is scoped to the selected model version */}
      <div className="flex-1 overflow-auto bg-white">
        <div className="max-w-7xl mx-auto px-6 py-5">
          {activeTab && (
            <div>
              {activeTabId === 'overview' && <OverviewTab selectedVersion={selectedVersion} />}
              {activeTabId === 'registry' && <ModelRegistryTab selectedVersion={selectedVersion} onSelectVersion={setSelectedVersion} />}
              {activeTabId === 'performance' && <PerformanceTab selectedVersion={selectedVersion} />}
              {activeTabId === 'training' && <TrainingDataTab selectedVersion={selectedVersion} />}
              {activeTabId === 'monitoring' && <MonitoringTab selectedVersion={selectedVersion} />}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default RiskModelManagementV2
