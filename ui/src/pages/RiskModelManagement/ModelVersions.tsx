import React, { useState, useEffect } from 'react'
import { CheckCircle, Clock, AlertCircle, Trash2 } from 'lucide-react'
import { useModelVersions } from '../../v2/hooks/useMCPEngine'

interface ModelVersionsProps {
  onCompare?: (model1: string, model2: string) => void
  onVote?: (versionId: string) => void
}

interface PerformanceMetrics {
  accuracy: number
  aucRoc: number
  latencyP95: number
  falsePositiveRate: number
}

interface ApprovalVote {
  voter: string
  status: 'approved' | 'pending' | 'rejected'
}

interface ModelVersion {
  id: string
  version: string
  status: 'production' | 'staging' | 'candidate' | 'deprecated'
  deployedAt: string
  trainedOn: number
  features: number
  weightsSum: number
  performance: PerformanceMetrics
  approvedBy?: string
  approvalDate?: string
  approvalVotes?: ApprovalVote[]
  comparisonMetrics?: {
    accuracyDiff: number
    aucRocDiff: number
    latencyDiff: number
    fprDiff: number
  }
}

const ModelVersions: React.FC<ModelVersionsProps> = ({ onCompare, onVote }) => {
  const { versions: mcpVersions, loading, error, approveModel, promoteModel } = useModelVersions()
  const [models, setModels] = useState<ModelVersion[]>([])
  const [filter, setFilter] = useState<'all' | 'production' | 'staging' | 'candidate' | 'deprecated'>('all')

  useEffect(() => {
    if (!mcpVersions.length) return
    setModels(mcpVersions.map(v => ({
      id: v.version_id,
      version: v.version_id,
      status: (v.status === 'pending_review' ? 'candidate' : v.status) as ModelVersion['status'],
      deployedAt: v.deployed_at ?? v.created_at,
      trainedOn: 0,
      features: 36,
      weightsSum: 100,
      performance: {
        accuracy: v.metrics?.accuracy ?? 0,
        aucRoc: v.metrics?.auc_roc ?? 0,
        latencyP95: 0,
        falsePositiveRate: 0,
      },
      approvalVotes: v.approval_votes?.map(av => ({
        voter: av.voter_id,
        status: av.vote as 'approved' | 'pending' | 'rejected',
      })),
    })))
  }, [mcpVersions])

  const filteredModels = models.filter(m => filter === 'all' || m.status === filter)

  const getStatusBadge = (status: string) => {
    const styles = {
      production: 'bg-green-100 text-green-800',
      staging: 'bg-blue-100 text-blue-800',
      candidate: 'bg-yellow-100 text-yellow-800',
      deprecated: 'bg-gray-100 text-gray-800',
    }
    const labels = {
      production: 'PRODUCTION',
      staging: 'STAGING',
      candidate: 'CANDIDATE',
      deprecated: 'DEPRECATED',
    }
    return { style: styles[status as keyof typeof styles], label: labels[status as keyof typeof labels] }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'production':
        return <CheckCircle className="text-green-600" size={18} />
      case 'staging':
        return <Clock className="text-blue-600" size={18} />
      case 'candidate':
        return <Clock className="text-yellow-600" size={18} />
      default:
        return <AlertCircle className="text-gray-600" size={18} />
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sentry-slate">Loading model versions...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-sentry-navy mb-2">Model Versions</h1>
        <p className="text-sentry-slate">Compare all available model versions and manage status</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      {/* Filter */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex flex-wrap gap-2">
          {(['all', 'production', 'staging', 'candidate', 'deprecated'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                filter === f
                  ? 'bg-sentry-navy text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Model List */}
      <div className="space-y-4">
        {filteredModels.map(model => (
          <div key={model.id} className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                {getStatusIcon(model.status)}
                <div>
                  <h3 className="text-lg font-semibold text-sentry-navy">
                    MODEL {model.version.toUpperCase()}
                  </h3>
                  <div className={`inline-block px-2 py-1 rounded text-xs font-medium mt-1 ${getStatusBadge(model.status).style}`}>
                    {getStatusBadge(model.status).label}
                  </div>
                </div>
              </div>
            </div>

            {/* Key Details Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 pb-6 border-b border-gray-200">
              <div>
                <p className="text-xs text-gray-600 font-semibold uppercase">Status</p>
                <p className="text-sm font-semibold text-sentry-navy mt-1">
                  {model.status === 'production'
                    ? 'ACTIVE IN PRODUCTION'
                    : model.status === 'candidate'
                      ? 'AWAITING APPROVAL'
                      : 'ARCHIVED (LEGACY)'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600 font-semibold uppercase">Deployed/Trained</p>
                <p className="text-sm font-semibold text-sentry-navy mt-1">{model.deployedAt}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 font-semibold uppercase">Training Records</p>
                <p className="text-sm font-semibold text-sentry-navy mt-1">{(model.trainedOn / 1000000).toFixed(1)}M</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 font-semibold uppercase">Features</p>
                <p className="text-sm font-semibold text-sentry-navy mt-1">{model.features}</p>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-sentry-navy mb-3">Performance Metrics:</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-gray-600">Accuracy</p>
                  <p className="text-lg font-bold text-sentry-navy">{model.performance.accuracy.toFixed(1)}%</p>
                  {model.comparisonMetrics && (
                    <p className={`text-xs font-semibold ${model.comparisonMetrics.accuracyDiff > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {model.comparisonMetrics.accuracyDiff > 0 ? '+' : ''}{model.comparisonMetrics.accuracyDiff.toFixed(2)}%
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-xs text-gray-600">AUC-ROC</p>
                  <p className="text-lg font-bold text-sentry-navy">{model.performance.aucRoc.toFixed(3)}</p>
                  {model.comparisonMetrics && (
                    <p className={`text-xs font-semibold ${model.comparisonMetrics.aucRocDiff > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {model.comparisonMetrics.aucRocDiff > 0 ? '+' : ''}{model.comparisonMetrics.aucRocDiff.toFixed(4)}
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-xs text-gray-600">Latency (p95)</p>
                  <p className="text-lg font-bold text-sentry-navy">{model.performance.latencyP95}ms</p>
                  {model.comparisonMetrics && (
                    <p className={`text-xs font-semibold ${model.comparisonMetrics.latencyDiff < 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {model.comparisonMetrics.latencyDiff > 0 ? '+' : ''}{model.comparisonMetrics.latencyDiff}ms
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-xs text-gray-600">False Positive Rate</p>
                  <p className="text-lg font-bold text-sentry-navy">{model.performance.falsePositiveRate.toFixed(1)}%</p>
                  {model.comparisonMetrics && (
                    <p className={`text-xs font-semibold ${model.comparisonMetrics.fprDiff < 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {model.comparisonMetrics.fprDiff > 0 ? '+' : ''}{model.comparisonMetrics.fprDiff.toFixed(2)}%
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Approval Info */}
            {model.approvedBy && (
              <div className="mb-6 pb-6 border-t border-gray-200 pt-4">
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">Approved By:</span> {model.approvedBy}
                </p>
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">Approval Date:</span> {model.approvalDate}
                </p>
              </div>
            )}

            {model.approvalVotes && (
              <div className="mb-6 pb-6 border-t border-gray-200 pt-4">
                <h4 className="text-sm font-semibold text-sentry-navy mb-3">Approval Votes:</h4>
                <div className="space-y-2">
                  {model.approvalVotes.map((vote, idx) => (
                    <div key={idx} className="flex justify-between items-center text-sm">
                      <span className="text-gray-700">{vote.voter}</span>
                      <span
                        className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                          vote.status === 'approved'
                            ? 'bg-green-100 text-green-800'
                            : vote.status === 'pending'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {vote.status === 'approved'
                          ? '✓ APPROVE'
                          : vote.status === 'pending'
                            ? '⏳ PENDING'
                            : '✗ REJECT'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Weights Validation */}
            <div className="mb-6 pb-6 border-t border-gray-200 pt-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">Weights Sum:</span> {model.weightsSum.toFixed(1)}%
                </p>
                {model.weightsSum === 100.0 ? (
                  <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                    ✓ Valid
                  </span>
                ) : (
                  <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800">
                    ✗ Invalid
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap gap-2">
              <button className="px-3 py-1 text-sm font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90">
                View Details
              </button>
              <button
                onClick={() => onCompare?.(model.version, 'v3.0')}
                className="px-3 py-1 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Compare
              </button>
              {model.status === 'candidate' && (
                <button
                  onClick={() => onVote?.(model.id)}
                  className="px-3 py-1 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Vote
                </button>
              )}
              {model.status === 'production' && (
                <button className="px-3 py-1 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
                  Rollback
                </button>
              )}
              {model.status === 'deprecated' && (
                <button className="px-3 py-1 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300 flex items-center gap-1">
                  <Trash2 size={14} />
                  Archive
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ModelVersions
