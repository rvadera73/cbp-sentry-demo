import React, { useState, useEffect } from 'react'
import { CheckCircle, AlertCircle, Clock, Play } from 'lucide-react'
import { useTrainingHistory } from '../../v2/hooks/useMCPEngine'

interface TrainingHistoryProps {
  onViewDetails?: (jobId: string) => void
  onRetry?: (jobId: string) => void
}

interface TrainingMetrics {
  trainingAccuracy: number
  testAccuracy: number
  aucRoc: number
  validationStatus: string
}

interface TrainingJob {
  id: string
  jobId: string
  modelId: string
  status: 'completed' | 'in_progress' | 'failed'
  startedAt: string
  completedAt?: string
  duration?: string
  dataset: {
    name: string
    records: number
    features: number
    trainTestSplit: string
  }
  hyperparameters: {
    maxDepth: number
    learningRate: number
    nEstimators: number
  }
  trainingMetrics?: TrainingMetrics
  topFeatures?: Array<{ name: string; importance: number }>
  progress?: number
  currentStep?: string
  eta?: string
  errorMessage?: string
}

const TrainingHistory: React.FC<TrainingHistoryProps> = ({ onViewDetails, onRetry }) => {
  const { jobs: mcpJobs, loading, error, triggerTraining } = useTrainingHistory()
  const [jobs, setJobs] = useState<TrainingJob[]>([])
  const [filter, setFilter] = useState<'all' | 'completed' | 'in_progress' | 'failed'>('all')
  const [sort, setSort] = useState<'date' | 'status'>('date')

  useEffect(() => {
    if (!mcpJobs.length) return
    setJobs(mcpJobs.map(j => ({
      id: j.job_id,
      jobId: j.job_id,
      modelId: j.model_type,
      status: j.status as TrainingJob['status'],
      startedAt: j.started_at,
      completedAt: j.completed_at,
      duration: j.completed_at
        ? `${Math.round((new Date(j.completed_at).getTime() - new Date(j.started_at).getTime()) / 60000)}m`
        : undefined,
      dataset: { name: 'cbp-sentry-db', records: 1396, features: 36, trainTestSplit: '80/20' },
      hyperparameters: { maxDepth: (j as any).hyperparameters?.maxDepth ?? 6, learningRate: (j as any).hyperparameters?.learningRate ?? 0.1, nEstimators: (j as any).hyperparameters?.nEstimators ?? 100 },
      trainingMetrics: j.metrics
        ? { trainingAccuracy: j.metrics.training_accuracy * 100, testAccuracy: j.metrics.test_accuracy * 100,
            aucRoc: j.metrics.auc_roc, validationStatus: 'PASSED' }
        : undefined,
      errorMessage: j.error,
    })))
  }, [mcpJobs])

  const handleTrigger = async () => {
    try {
      await triggerTraining('all', 'Manual trigger from UI')
    } catch (e) {
      console.error('Training trigger failed:', e)
    }
  }

  const filteredJobs = jobs.filter(j => filter === 'all' || j.status === filter)

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="text-green-600" size={20} />
      case 'in_progress':
        return <Clock className="text-blue-600 animate-spin" size={20} />
      case 'failed':
        return <AlertCircle className="text-red-600" size={20} />
      default:
        return null
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'in_progress':
        return 'bg-blue-100 text-blue-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sentry-slate">Loading training history...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-sentry-navy mb-2">Training History & Jobs</h1>
        <p className="text-sentry-slate">Track all training jobs and view results</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div>
          <label className="text-sm font-semibold text-gray-700 mb-2 block">Filter by Status:</label>
          <div className="flex flex-wrap gap-2">
            {(['all', 'completed', 'in_progress', 'failed'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  filter === f
                    ? 'bg-sentry-navy text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {f === 'in_progress' ? 'In Progress' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm font-semibold text-gray-700 mb-2 block">Sort by:</label>
          <div className="flex gap-2">
            {(['date', 'status'] as const).map(s => (
              <button
                key={s}
                onClick={() => setSort(s)}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  sort === s
                    ? 'bg-sentry-navy text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Training Jobs List */}
      <div className="space-y-4">
        {filteredJobs.map(job => (
          <div key={job.id} className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                {getStatusIcon(job.status)}
                <div>
                  <h3 className="text-lg font-semibold text-sentry-navy">
                    TRAINING JOB {job.modelId.toUpperCase()}
                  </h3>
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium mt-1 ${getStatusColor(job.status)}`}>
                    {job.status === 'in_progress' ? 'IN PROGRESS' : job.status.toUpperCase()}
                  </span>
                </div>
              </div>
            </div>

            {/* Basic Info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 pb-6 border-b border-gray-200">
              <div>
                <p className="text-xs text-gray-600 font-semibold uppercase">Model</p>
                <p className="text-sm font-semibold text-sentry-navy mt-1">{job.modelId}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 font-semibold uppercase">Job ID</p>
                <p className="text-sm font-semibold text-sentry-navy mt-1 font-mono text-xs">{job.jobId}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 font-semibold uppercase">Started</p>
                <p className="text-sm font-semibold text-sentry-navy mt-1">{job.startedAt}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 font-semibold uppercase">Duration</p>
                <p className="text-sm font-semibold text-sentry-navy mt-1">
                  {job.duration || (job.eta ? `ETA: ${job.eta}` : 'N/A')}
                </p>
              </div>
            </div>

            {/* Dataset Info */}
            <div className="mb-6 pb-6 border-b border-gray-200">
              <h4 className="text-sm font-semibold text-sentry-navy mb-2">Dataset:</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Name:</span>
                  <p className="font-semibold text-sentry-navy">{job.dataset.name}</p>
                </div>
                <div>
                  <span className="text-gray-600">Records:</span>
                  <p className="font-semibold text-sentry-navy">{(job.dataset.records / 1000000).toFixed(1)}M</p>
                </div>
                <div>
                  <span className="text-gray-600">Features:</span>
                  <p className="font-semibold text-sentry-navy">{job.dataset.features}</p>
                </div>
                <div>
                  <span className="text-gray-600">Train/Test:</span>
                  <p className="font-semibold text-sentry-navy">{job.dataset.trainTestSplit}</p>
                </div>
              </div>
            </div>

            {/* Hyperparameters */}
            <div className="mb-6 pb-6 border-b border-gray-200">
              <h4 className="text-sm font-semibold text-sentry-navy mb-2">Hyperparameters:</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">max_depth:</span>
                  <p className="font-semibold text-sentry-navy">{job.hyperparameters.maxDepth}</p>
                </div>
                <div>
                  <span className="text-gray-600">learning_rate:</span>
                  <p className="font-semibold text-sentry-navy">{job.hyperparameters.learningRate}</p>
                </div>
                <div>
                  <span className="text-gray-600">n_estimators:</span>
                  <p className="font-semibold text-sentry-navy">{job.hyperparameters.nEstimators}</p>
                </div>
              </div>
            </div>

            {/* Training Results or Progress */}
            {job.status === 'completed' && job.trainingMetrics && (
              <div className="mb-6 pb-6 border-b border-gray-200">
                <h4 className="text-sm font-semibold text-sentry-navy mb-3">Training Results:</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
                  <div>
                    <span className="text-gray-600">Training Accuracy:</span>
                    <p className="font-semibold text-sentry-navy">{job.trainingMetrics.trainingAccuracy.toFixed(1)}%</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Test Accuracy:</span>
                    <p className="font-semibold text-sentry-navy">{job.trainingMetrics.testAccuracy.toFixed(1)}%</p>
                  </div>
                  <div>
                    <span className="text-gray-600">AUC-ROC:</span>
                    <p className="font-semibold text-sentry-navy">{job.trainingMetrics.aucRoc.toFixed(3)}</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Validation:</span>
                    <p className="font-semibold text-green-600">
                      {job.trainingMetrics.validationStatus}
                      {job.trainingMetrics.validationStatus === 'PASSED' ? ' ✓' : ''}
                    </p>
                  </div>
                </div>

                {job.topFeatures && (
                  <div>
                    <h5 className="text-sm font-semibold text-sentry-navy mb-2">Top Features by Importance:</h5>
                    <div className="space-y-1">
                      {job.topFeatures.map((feature, idx) => (
                        <div key={idx} className="flex justify-between text-sm">
                          <span className="text-gray-700">
                            {idx + 1}. {feature.name}
                          </span>
                          <span className="font-semibold text-sentry-navy">({feature.importance.toFixed(1)}%)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {job.status === 'in_progress' && (
              <div className="mb-6 pb-6 border-b border-gray-200">
                <h4 className="text-sm font-semibold text-sentry-navy mb-3">Progress:</h4>
                <div className="mb-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-gray-700">{job.progress}% (Step 3/6)</span>
                    <span className="text-sm text-gray-600">{job.currentStep}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${job.progress}%` }}
                    ></div>
                  </div>
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-700">Data Prep:</span>
                    <span className="text-green-600">✓ Complete</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-700">Feature Engineering:</span>
                    <span className="text-green-600">✓ Complete</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-700">Model Training:</span>
                    <span className="text-blue-600">⏳ In Progress...</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-700">Validation:</span>
                    <span className="text-gray-600">⏜ Queued</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-700">Artifact Storage:</span>
                    <span className="text-gray-600">⏜ Queued</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mt-3">ETA: {job.eta}</p>
              </div>
            )}

            {job.status === 'failed' && (
              <div className="mb-6 pb-6 border-b border-gray-200 bg-red-50 rounded p-4">
                <h4 className="text-sm font-semibold text-red-900 mb-2">Error Details:</h4>
                <p className="text-sm text-red-800">{job.errorMessage}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => onViewDetails?.(job.jobId)}
                className="px-3 py-1 text-sm font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90"
              >
                View Full Report
              </button>
              {job.status === 'completed' && (
                <button className="px-3 py-1 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
                  Create Comparison
                </button>
              )}
              {job.status === 'in_progress' && (
                <button className="px-3 py-1 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
                  View Logs
                </button>
              )}
              {job.status === 'in_progress' && (
                <button className="px-3 py-1 text-sm font-medium bg-red-200 text-red-800 rounded hover:bg-red-300">
                  Cancel
                </button>
              )}
              {job.status === 'failed' && (
                <button
                  onClick={() => onRetry?.(job.jobId)}
                  className="px-3 py-1 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-1"
                >
                  <Play size={14} />
                  Retry
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default TrainingHistory
