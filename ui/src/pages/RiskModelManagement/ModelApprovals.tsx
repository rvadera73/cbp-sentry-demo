import React, { useState, useEffect } from 'react'
import { CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react'

interface ModelApprovalsProps {
  onVote?: (approvalId: string, vote: 'approve' | 'reject' | 'abstain') => void
  onCompare?: (model1: string, model2: string) => void
}

interface Voter {
  name: string
  role: string
  vote?: 'approve' | 'reject' | 'pending'
  comment?: string
  votedAt?: string
  emailSent?: string
  reminderSent?: string
}

interface ApprovalRequest {
  id: string
  modelVersion: string
  requestedBy: string
  requestedByRole: string
  requestedAt: string
  reason: string
  performanceImprovement: {
    accuracy: number
    aucRoc: number
    latency: number
    fpr: number
  }
  trainingData: {
    records: number
    dateRange: string
    validationStatus: string
  }
  fairnessAnalysis: {
    byOrigin: string
    byCommodity: string
    fairnessScore: number
  }
  voters: Voter[]
  status: 'pending' | 'approved' | 'rejected'
  votingDeadline: string
  historicalApprovals: Array<{
    modelVersion: string
    requestedDate: string
    approvedDate: string
    voters: string[]
    deployedDate: string
  }>
  historicalRejections: Array<{
    modelVersion: string
    requestedDate: string
    rejectedDate: string
    reason: string
    rejector: string
  }>
}

const ModelApprovals: React.FC<ModelApprovalsProps> = ({ onVote, onCompare }) => {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [votingComments, setVotingComments] = useState<Record<string, string>>({})

  useEffect(() => {
    loadApprovals()
  }, [])

  const loadApprovals = async () => {
    setLoading(true)
    setError(null)
    try {
      // TODO: Replace with actual API calls to /api/risk-models/approvals
      setApprovals([
        {
          id: 'approval-v3.1',
          modelVersion: 'v3.1',
          requestedBy: 'Alex Kim',
          requestedByRole: 'ML Engineer',
          requestedAt: '2026-06-11 10:30 UTC',
          reason: '+0.7% accuracy, lower FPR',
          performanceImprovement: {
            accuracy: 0.7,
            aucRoc: 0.007,
            latency: -0.2,
            fpr: -0.4,
          },
          trainingData: {
            records: 2500000,
            dateRange: '2024 full year',
            validationStatus: 'PASSED',
          },
          fairnessAnalysis: {
            byOrigin: 'All segments within ±1%',
            byCommodity: 'All segments balanced',
            fairnessScore: 0.94,
          },
          voters: [
            {
              name: 'Sarah Chen',
              role: 'Manager',
              vote: 'approve',
              comment: 'Solid improvement. FPR reduction is significant',
              votedAt: '2026-06-11 14:22 UTC',
            },
            {
              name: 'John Davis',
              role: 'Tech Lead',
              vote: 'pending',
              emailSent: '2026-06-11 10:35 UTC',
              reminderSent: '2026-06-12 10:35 UTC',
            },
          ],
          status: 'pending',
          votingDeadline: '2026-06-14 10:30 UTC',
          historicalApprovals: [
            {
              modelVersion: 'v3.0',
              requestedDate: '2026-06-12 12:00 UTC',
              approvedDate: '2026-06-12 14:35 UTC',
              voters: ['Sarah Chen', 'John Davis'],
              deployedDate: '2026-06-12 14:35 UTC',
            },
          ],
          historicalRejections: [
            {
              modelVersion: 'v2.2',
              requestedDate: '2026-06-10 14:00 UTC',
              rejectedDate: '2026-06-10 16:30 UTC',
              reason: 'Test accuracy < 0.90 threshold',
              rejector: 'Sarah Chen',
            },
          ],
        },
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load approvals')
    } finally {
      setLoading(false)
    }
  }

  const handleVote = (approvalId: string, vote: 'approve' | 'reject' | 'abstain') => {
    onVote?.(approvalId, vote)
  }

  const filteredApprovals = approvals.filter(a => filter === 'all' || a.status === filter)

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="text-green-600" size={20} />
      case 'rejected':
        return <XCircle className="text-red-600" size={20} />
      case 'pending':
        return <Clock className="text-yellow-600" size={20} />
      default:
        return null
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-800'
      case 'rejected':
        return 'bg-red-100 text-red-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sentry-slate">Loading approvals...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-sentry-navy mb-2">Model Approvals & Voting</h1>
        <p className="text-sentry-slate">Workflow for approving/rejecting model changes</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      {/* Filter */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex flex-wrap gap-2">
          {(['all', 'pending', 'approved', 'rejected'] as const).map(f => (
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

      {/* Approval Requests */}
      <div className="space-y-6">
        {filteredApprovals.map(approval => (
          <div key={approval.id}>
            {/* Main Approval Card */}
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  {getStatusIcon(approval.status)}
                  <div>
                    <h3 className="text-lg font-semibold text-sentry-navy">
                      APPROVAL REQUEST: {approval.modelVersion.toUpperCase()}
                    </h3>
                    <span className={`inline-block px-2 py-1 rounded text-xs font-medium mt-1 ${getStatusColor(approval.status)}`}>
                      {approval.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Request Details */}
              <div className="mb-6 pb-6 border-b border-gray-200">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Requested By:</span>
                    <p className="font-semibold text-sentry-navy">{approval.requestedBy}</p>
                    <p className="text-xs text-gray-600">({approval.requestedByRole})</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Requested Date:</span>
                    <p className="font-semibold text-sentry-navy">{approval.requestedAt}</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Request Reason:</span>
                    <p className="font-semibold text-sentry-navy">{approval.reason}</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Deadline:</span>
                    <p className="font-semibold text-sentry-navy">{approval.votingDeadline}</p>
                  </div>
                </div>
              </div>

              {/* Performance Improvement */}
              <div className="mb-6 pb-6 border-b border-gray-200">
                <h4 className="text-sm font-semibold text-sentry-navy mb-3">Performance Improvement:</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div className="bg-green-50 rounded p-3">
                    <span className="text-gray-600">Accuracy:</span>
                    <p className="font-semibold text-green-700 mt-1">
                      92.4% → 93.1% <span className="text-green-600">(+{approval.performanceImprovement.accuracy.toFixed(1)}%)</span>
                    </p>
                    <span className="text-xs text-green-600">✓</span>
                  </div>
                  <div className="bg-green-50 rounded p-3">
                    <span className="text-gray-600">AUC-ROC:</span>
                    <p className="font-semibold text-green-700 mt-1">
                      0.944 → 0.951 <span className="text-green-600">(+{approval.performanceImprovement.aucRoc.toFixed(3)})</span>
                    </p>
                    <span className="text-xs text-green-600">✓</span>
                  </div>
                  <div className="bg-green-50 rounded p-3">
                    <span className="text-gray-600">Latency:</span>
                    <p className="font-semibold text-gray-700 mt-1">
                      85ms → 87ms <span className="text-green-600">({approval.performanceImprovement.latency.toFixed(1)}%)</span>
                    </p>
                    <span className="text-xs text-green-600">✓</span>
                  </div>
                  <div className="bg-green-50 rounded p-3">
                    <span className="text-gray-600">False Positive Rate:</span>
                    <p className="font-semibold text-green-700 mt-1">
                      3.2% → 2.8% <span className="text-green-600">({approval.performanceImprovement.fpr.toFixed(1)}%)</span>
                    </p>
                    <span className="text-xs text-green-600">✓</span>
                  </div>
                </div>
              </div>

              {/* Training Data */}
              <div className="mb-6 pb-6 border-b border-gray-200">
                <h4 className="text-sm font-semibold text-sentry-navy mb-2">Training Data:</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Records:</span>
                    <span className="font-semibold text-sentry-navy">{(approval.trainingData.records / 1000000).toFixed(1)}M shipments</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Date Range:</span>
                    <span className="font-semibold text-sentry-navy">{approval.trainingData.dateRange}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Validation:</span>
                    <span className="font-semibold text-green-600">{approval.trainingData.validationStatus} ✓</span>
                  </div>
                </div>
              </div>

              {/* Fairness Analysis */}
              <div className="mb-6 pb-6 border-b border-gray-200">
                <h4 className="text-sm font-semibold text-sentry-navy mb-2">Fairness Analysis:</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">By Origin:</span>
                    <span className="font-semibold text-green-600">{approval.fairnessAnalysis.byOrigin} ✓</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">By Commodity:</span>
                    <span className="font-semibold text-green-600">{approval.fairnessAnalysis.byCommodity} ✓</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Overall Fairness Score:</span>
                    <span className="font-semibold text-green-600">{approval.fairnessAnalysis.fairnessScore.toFixed(2)} ✓</span>
                  </div>
                </div>
              </div>

              {/* Approval Votes */}
              <div className="mb-6 pb-6 border-b border-gray-200">
                <h4 className="text-sm font-semibold text-sentry-navy mb-3">Approval Votes ({approval.voters.filter(v => v.vote).length}/{approval.voters.length} required)</h4>
                <div className="space-y-4">
                  {approval.voters.map((voter, idx) => (
                    <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className="font-semibold text-sentry-navy">{voter.name}</p>
                          <p className="text-xs text-gray-600">({voter.role})</p>
                        </div>
                        {voter.vote === 'approve' && (
                          <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                            ✓ APPROVE
                          </span>
                        )}
                        {voter.vote === 'reject' && (
                          <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800">
                            ✗ REJECT
                          </span>
                        )}
                        {voter.vote === 'pending' && (
                          <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                            ⏳ PENDING
                          </span>
                        )}
                      </div>

                      {voter.vote === 'pending' && approval.status === 'pending' && (
                        <div>
                          <div className="mb-3 space-y-2 text-xs">
                            <label className="flex items-center gap-2 cursor-pointer">
                              <input type="checkbox" className="rounded" />
                              I agree this model is better
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                              <input type="checkbox" className="rounded" />
                              Risk is within acceptable range
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                              <input type="checkbox" className="rounded" />
                              I recommend approval
                            </label>
                          </div>

                          <textarea
                            placeholder="Add optional comment..."
                            value={votingComments[approval.id] || ''}
                            onChange={e => setVotingComments({ ...votingComments, [approval.id]: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded text-xs mb-3 resize-none"
                            rows={2}
                          />

                          <div className="flex gap-2">
                            <button
                              onClick={() => handleVote(approval.id, 'approve')}
                              className="flex-1 px-3 py-2 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700"
                            >
                              APPROVE
                            </button>
                            <button
                              onClick={() => handleVote(approval.id, 'reject')}
                              className="flex-1 px-3 py-2 text-xs font-medium bg-red-600 text-white rounded hover:bg-red-700"
                            >
                              REJECT
                            </button>
                            <button
                              onClick={() => handleVote(approval.id, 'abstain')}
                              className="flex-1 px-3 py-2 text-xs font-medium bg-gray-400 text-white rounded hover:bg-gray-500"
                            >
                              ABSTAIN
                            </button>
                          </div>
                        </div>
                      )}

                      {voter.vote && voter.vote !== 'pending' && (
                        <div className="space-y-1 text-sm">
                          {voter.comment && (
                            <p className="text-gray-700 italic">"{voter.comment}"</p>
                          )}
                          {voter.votedAt && (
                            <p className="text-xs text-gray-600">Voted: {voter.votedAt}</p>
                          )}
                        </div>
                      )}

                      {voter.vote === 'pending' && (
                        <div className="space-y-1 text-xs text-gray-600">
                          {voter.emailSent && <p>Email Sent: {voter.emailSent}</p>}
                          {voter.reminderSent && <p>Reminder Sent: {voter.reminderSent}</p>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Status */}
              <div className="mb-6 pb-6 border-b border-gray-200">
                <p className="text-sm font-semibold text-sentry-navy">
                  Status: {approval.voters.filter(v => v.vote === 'approve').length}/{approval.voters.length} voted, {approval.voters.filter(v => !v.vote).length} approval(s) remaining
                </p>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap gap-2">
                <button className="px-4 py-2 text-sm font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90">
                  View Full Training Report
                </button>
                <button
                  onClick={() => onCompare?.(approval.modelVersion, 'v3.0')}
                  className="px-4 py-2 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
                >
                  Compare Metrics
                </button>
                <button className="px-4 py-2 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
                  Notify Reviewers
                </button>
              </div>
            </div>

            {/* Historical Info */}
            {approval.historicalApprovals.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-semibold text-sentry-navy mb-3">Approval History</h4>
                <div className="space-y-2">
                  {approval.historicalApprovals.map((hist, idx) => (
                    <div key={idx} className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <CheckCircle className="text-green-600" size={18} />
                        <p className="font-semibold text-green-900">
                          ✓ APPROVED: {hist.modelVersion.toUpperCase()} ({hist.approvedDate.split(' ')[0]})
                        </p>
                      </div>
                      <div className="ml-6 space-y-1 text-sm text-gray-700">
                        <p>Requested: {hist.requestedDate}</p>
                        <p>Approved: {hist.approvedDate}</p>
                        <p>Voters: {hist.voters.join(', ')}</p>
                        <p>Deployed: {hist.deployedDate}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {approval.historicalRejections.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-semibold text-sentry-navy mb-3">Rejection History</h4>
                <div className="space-y-2">
                  {approval.historicalRejections.map((hist, idx) => (
                    <div key={idx} className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <XCircle className="text-red-600" size={18} />
                        <p className="font-semibold text-red-900">
                          ✗ REJECTED: {hist.modelVersion.toUpperCase()} ({hist.rejectedDate.split(' ')[0]})
                        </p>
                      </div>
                      <div className="ml-6 space-y-1 text-sm text-gray-700">
                        <p>Requested: {hist.requestedDate}</p>
                        <p>Rejected: {hist.rejectedDate}</p>
                        <p>Reason: {hist.reason}</p>
                        <p>Rejector: {hist.rejector}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default ModelApprovals
