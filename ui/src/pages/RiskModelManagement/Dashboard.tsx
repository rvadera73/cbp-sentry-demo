import React, { useState, useEffect } from 'react'
import { AlertTriangle, TrendingUp, CheckCircle, Clock } from 'lucide-react'

interface DashboardProps {
  onNavigate?: (screen: string) => void
}

interface ActiveModelMetrics {
  version: string
  status: string
  deployedAt: string
  approvedBy: string
  accuracy: number
  aucRoc: number
  latencyP95: number
  confidenceAvg: number
  predictionsProcessed: number
  dataDriftScore: number
  modelDriftScore: number
}

interface PendingApproval {
  modelVersion: string
  requestedBy: string
  requestedAt: string
  approvalStatus: string
  newAccuracy: number
  accuracyDiff: number
}

interface MonitoringAlert {
  type: 'warning' | 'success'
  title: string
  description: string
  timestamp: string
  actionRequired: boolean
}

const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [activeModel, setActiveModel] = useState<ActiveModelMetrics | null>(null)
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null)
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setLoading(true)
    setError(null)
    try {
      // TODO: Replace with actual API calls
      setActiveModel({
        version: 'CBP Risk v3.0',
        status: 'PRODUCTION',
        deployedAt: '2026-06-12 14:35 UTC',
        approvedBy: 'Sarah Chen (Manager)',
        accuracy: 92.4,
        aucRoc: 0.94,
        latencyP95: 85,
        confidenceAvg: 0.87,
        predictionsProcessed: 15432,
        dataDriftScore: 0.12,
        modelDriftScore: 0.08,
      })

      setPendingApproval({
        modelVersion: 'v3.1',
        requestedBy: 'ML Team',
        requestedAt: '2026-06-11 10:00 UTC',
        approvalStatus: '1/2 votes (50%)',
        newAccuracy: 93.1,
        accuracyDiff: 0.7,
      })

      setAlerts([
        {
          type: 'warning',
          title: 'High Data Drift Detected',
          description: 'Feature: origin_country, Drift Score: 0.34 (Elevated), Detected: 2 hours ago',
          timestamp: '2 hours ago',
          actionRequired: true,
        },
        {
          type: 'success',
          title: 'All Other Metrics Normal',
          description: 'All performance and drift metrics within acceptable ranges',
          timestamp: 'Current',
          actionRequired: false,
        },
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <p className="text-sentry-slate">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-sentry-navy mb-2">Risk Model Management Dashboard</h1>
        <p className="text-sentry-slate">At-a-glance model health and status</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      {/* Active Model Section */}
      {activeModel && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-sentry-navy mb-4">Active Model</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Model:</span>
                  <span className="font-semibold text-sentry-navy">{activeModel.version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Status:</span>
                  <span className="inline-block px-2 py-1 rounded bg-green-100 text-green-800 font-medium text-xs">
                    {activeModel.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Deployed:</span>
                  <span className="font-semibold text-sentry-navy">{activeModel.deployedAt}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Approved By:</span>
                  <span className="font-semibold text-sentry-navy">{activeModel.approvedBy}</span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-sentry-navy mb-3">Performance (Last 24h)</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Accuracy:</span>
                  <span className="font-semibold text-sentry-navy">{activeModel.accuracy.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">AUC-ROC:</span>
                  <span className="font-semibold text-sentry-navy">{activeModel.aucRoc.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Latency (p95):</span>
                  <span className="font-semibold text-sentry-navy">{activeModel.latencyP95}ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Confidence (avg):</span>
                  <span className="font-semibold text-sentry-navy">{activeModel.confidenceAvg.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Predictions Processed:</span>
                <p className="text-lg font-semibold text-sentry-navy">{activeModel.predictionsProcessed.toLocaleString()}</p>
              </div>
              <div>
                <span className="text-gray-600">Data Drift Score:</span>
                <p className="text-lg font-semibold text-green-700">{activeModel.dataDriftScore.toFixed(2)} (Normal)</p>
              </div>
              <div>
                <span className="text-gray-600">Model Drift Score:</span>
                <p className="text-lg font-semibold text-green-700">{activeModel.modelDriftScore.toFixed(2)} (Normal)</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pending Actions Section */}
      {pendingApproval && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-sentry-navy mb-4">Pending Actions</h2>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-4">
              <Clock className="text-blue-600 flex-shrink-0 mt-1" size={20} />
              <div className="flex-1">
                <h3 className="font-semibold text-sentry-navy mb-2">
                  Candidate Model: {pendingApproval.modelVersion} (Under Review)
                </h3>
                <div className="space-y-1 text-sm text-gray-700 mb-4">
                  <div className="flex justify-between">
                    <span>Requested By:</span>
                    <span>{pendingApproval.requestedBy}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Requested:</span>
                    <span>{pendingApproval.requestedAt}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Approval Status:</span>
                    <span className="font-semibold">{pendingApproval.approvalStatus}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>New Accuracy:</span>
                    <span className="font-semibold text-green-700">
                      {pendingApproval.newAccuracy.toFixed(1)}% (+{pendingApproval.accuracyDiff.toFixed(1)}%)
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => onNavigate?.('details')}
                    className="px-3 py-1 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    View Details
                  </button>
                  <button
                    onClick={() => onNavigate?.('approvals')}
                    className="px-3 py-1 text-sm font-medium bg-white border border-blue-600 text-blue-600 rounded hover:bg-blue-50"
                  >
                    Vote
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Monitoring Alerts Section */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-sentry-navy mb-4">Monitoring Alerts</h2>
        <div className="space-y-3">
          {alerts.map((alert, idx) => (
            <div
              key={idx}
              className={`border rounded-lg p-4 flex items-start gap-3 ${
                alert.type === 'warning'
                  ? 'bg-yellow-50 border-yellow-200'
                  : 'bg-green-50 border-green-200'
              }`}
            >
              {alert.type === 'warning' ? (
                <AlertTriangle className="text-yellow-600 flex-shrink-0 mt-0.5" size={18} />
              ) : (
                <CheckCircle className="text-green-600 flex-shrink-0 mt-0.5" size={18} />
              )}
              <div className="flex-1">
                <h3 className={`font-semibold ${alert.type === 'warning' ? 'text-yellow-900' : 'text-green-900'}`}>
                  {alert.title}
                </h3>
                <p className={`text-sm ${alert.type === 'warning' ? 'text-yellow-800' : 'text-green-800'}`}>
                  {alert.description}
                </p>
              </div>
              {alert.actionRequired && (
                <button className="flex-shrink-0 px-3 py-1 text-sm font-medium bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200">
                  Investigate
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions Section */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-sentry-navy mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <button
            onClick={() => onNavigate?.('versions')}
            className="px-4 py-2 text-sm font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90"
          >
            View All Versions
          </button>
          <button
            onClick={() => onNavigate?.('versions')}
            className="px-4 py-2 text-sm font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90"
          >
            Compare Models
          </button>
          <button
            onClick={() => onNavigate?.('training')}
            className="px-4 py-2 text-sm font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90"
          >
            Run Training Job
          </button>
          <button
            onClick={() => onNavigate?.('metrics')}
            className="px-4 py-2 text-sm font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90"
          >
            View Metrics
          </button>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
