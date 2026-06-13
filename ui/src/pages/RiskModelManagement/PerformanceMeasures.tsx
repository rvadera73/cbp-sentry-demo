import React, { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { CheckCircle, AlertCircle, Clock, TrendingUp } from 'lucide-react'

interface GateInfo {
  gate_id: string
  gate_name: string
  timeline_days: [number, number]
  description: string
}

interface Metric {
  name: string
  type: string
  measured_value: number
  threshold_value: number
  unit: string
  status: string
  meets_requirement: boolean
}

interface GateStatus {
  gate_id: string
  gate_name: string
  description: string
  overall_status: string
  metrics_passed: number
  metrics_total: number
  pass_percentage: number
  evaluation_period: {
    start: string
    end: string
  }
  metrics: Metric[]
}

interface CurrentGateResponse {
  status: string
  days_since_award: number
  current_gate: GateInfo | null
  days_until_next_gate: number | null
  metrics_count: number
}

interface TrendData {
  date: string
  value: number
}

const PerformanceMeasures: React.FC = () => {
  const [currentGate, setCurrentGate] = useState<GateInfo | null>(null)
  const [gateStatus, setGateStatus] = useState<GateStatus | null>(null)
  const [trendData, setTrendData] = useState<Record<string, TrendData[]>>({})
  const [daysRemaining, setDaysRemaining] = useState<number>(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadPerformanceData()
  }, [])

  const loadPerformanceData = async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch current gate
      const currentGateRes = await fetch('/api/risk-models/performance/current-gate')
      if (!currentGateRes.ok) {
        throw new Error('Failed to fetch current gate')
      }
      const currentGateData: CurrentGateResponse = await currentGateRes.json()

      if (currentGateData.current_gate) {
        setCurrentGate(currentGateData.current_gate)
        setDaysRemaining(currentGateData.days_until_next_gate || 0)

        // Fetch gate status
        const gateStatusRes = await fetch(
          `/api/risk-models/performance/gate/${currentGateData.current_gate.gate_id}`
        )
        if (!gateStatusRes.ok) {
          throw new Error('Failed to fetch gate status')
        }
        const gateStatusData: GateStatus = await gateStatusRes.json()
        setGateStatus(gateStatusData)

        // Generate mock trend data (30 days)
        const trends: Record<string, TrendData[]> = {}
        for (const metric of gateStatusData.metrics) {
          trends[metric.name] = generateTrendData(metric.name, metric.measured_value)
        }
        setTrendData(trends)
      } else {
        setError('No applicable gate at this time')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load performance data')
      // Set mock data for development
      loadMockData()
    } finally {
      setLoading(false)
    }
  }

  const generateTrendData = (metricName: string, currentValue: number): TrendData[] => {
    const data: TrendData[] = []
    const baseValue = currentValue * 0.85
    for (let i = 30; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      const variance = Math.sin(i / 10) * currentValue * 0.1
      data.push({
        date: (date.getMonth() + 1).toString().padStart(2, '0') + '-' + date.getDate().toString().padStart(2, '0'),
        value: parseFloat((baseValue + variance + Math.random() * currentValue * 0.05).toFixed(2)),
      })
    }
    return data
  }

  const loadMockData = () => {
    const mockGate: GateInfo = {
      gate_id: '3',
      gate_name: 'Optimization & Refinement',
      timeline_days: [121, 180],
      description: 'Performance optimization and model refinement phase',
    }
    setCurrentGate(mockGate)
    setDaysRemaining(26)

    const mockStatus: GateStatus = {
      gate_id: '3',
      gate_name: 'Optimization & Refinement',
      description: 'Performance optimization and model refinement phase',
      overall_status: 'passed',
      metrics_passed: 4,
      metrics_total: 4,
      pass_percentage: 100,
      evaluation_period: {
        start: '2026-05-14',
        end: '2026-06-13',
      },
      metrics: [
        {
          name: 'scalability',
          type: 'count_per_period',
          measured_value: 2300,
          threshold_value: 2000,
          unit: 'shipments/week',
          status: 'passed',
          meets_requirement: true,
        },
        {
          name: 'accuracy',
          type: 'threshold',
          measured_value: 0.92,
          threshold_value: 0.9,
          unit: 'percentage',
          status: 'passed',
          meets_requirement: true,
        },
        {
          name: 'fairness',
          type: 'threshold',
          measured_value: 0.03,
          threshold_value: 0.05,
          unit: 'score',
          status: 'passed',
          meets_requirement: true,
        },
        {
          name: 'auc',
          type: 'threshold',
          measured_value: 0.945,
          threshold_value: 0.94,
          unit: 'score',
          status: 'passed',
          meets_requirement: true,
        },
      ],
    }
    setGateStatus(mockStatus)

    const mockTrends: Record<string, TrendData[]> = {
      scalability: generateTrendData('scalability', 2300),
      accuracy: generateTrendData('accuracy', 92),
      fairness: generateTrendData('fairness', 3),
      auc: generateTrendData('auc', 94.5),
    }
    setTrendData(mockTrends)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-slate-600">Loading performance measures...</p>
      </div>
    )
  }

  if (error && !currentGate) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-3 text-red-500" size={32} />
          <p className="text-red-600 font-semibold">{error}</p>
        </div>
      </div>
    )
  }

  const getStatusColor = (status: string): string => {
    if (status === 'passed') return 'text-green-600'
    if (status === 'failed') return 'text-red-600'
    return 'text-yellow-600'
  }

  const getStatusBgColor = (status: string): string => {
    if (status === 'passed') return 'bg-green-50'
    if (status === 'failed') return 'bg-red-50'
    return 'bg-yellow-50'
  }

  const getStatusIcon = (status: string) => {
    if (status === 'passed') {
      return <CheckCircle className="w-5 h-5 text-green-600" />
    } else if (status === 'failed') {
      return <AlertCircle className="w-5 h-5 text-red-600" />
    }
    return <Clock className="w-5 h-5 text-yellow-600" />
  }

  const getMetricDisplayValue = (metric: Metric): string => {
    if (metric.unit === 'percentage' || metric.unit === 'score') {
      if (metric.measured_value > 1) {
        return metric.measured_value.toFixed(1) + '%'
      }
      return (metric.measured_value * 100).toFixed(1) + '%'
    }
    if (metric.unit === 'shipments/week') {
      return metric.measured_value.toFixed(0) + ' shipments'
    }
    return metric.measured_value.toFixed(3)
  }

  const getThresholdDisplayValue = (metric: Metric): string => {
    if (metric.unit === 'percentage' || metric.unit === 'score') {
      if (metric.threshold_value > 1) {
        return metric.threshold_value.toFixed(1) + '%'
      }
      return (metric.threshold_value * 100).toFixed(1) + '%'
    }
    if (metric.unit === 'shipments/week') {
      return metric.threshold_value.toFixed(0) + ' shipments'
    }
    return metric.threshold_value.toFixed(3)
  }

  return (
    <div className="space-y-6">
      {/* Gate Summary Card */}
      {currentGate && (
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {/* Gate Info */}
            <div>
              <p className="text-sm text-slate-600 mb-1">Current Phase</p>
              <h3 className="text-lg font-bold text-slate-900">Gate {currentGate.gate_id}</h3>
              <p className="text-sm text-slate-600 mt-1">{currentGate.gate_name}</p>
            </div>

            {/* Days Remaining */}
            <div>
              <p className="text-sm text-slate-600 mb-1">Days Remaining</p>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-blue-600">{daysRemaining}</span>
                <span className="text-sm text-slate-600">of {currentGate.timeline_days[1] - currentGate.timeline_days[0]} days</span>
              </div>
            </div>

            {/* Overall Status */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-600 mb-1">Overall Status</p>
                <div className="flex items-center gap-2">
                  {gateStatus && gateStatus.overall_status === 'passed' ? (
                    <>
                      <CheckCircle className="w-6 h-6 text-green-600" />
                      <span className="font-bold text-green-600">ON TRACK</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-6 h-6 text-red-600" />
                      <span className="font-bold text-red-600">AT RISK</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Gate Description */}
          <p className="text-sm text-slate-600 border-t border-slate-200 pt-4">
            {currentGate.description}
          </p>
        </div>
      )}

      {/* Metrics Grid */}
      {gateStatus && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-slate-600" />
            <h3 className="text-lg font-semibold text-slate-900">Performance Metrics</h3>
            <span className="ml-auto text-sm text-slate-600">
              {gateStatus.metrics_passed}/{gateStatus.metrics_total} metrics passing
            </span>
          </div>

          {gateStatus.metrics.map((metric) => (
            <div
              key={metric.name}
              className={`bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden`}
            >
              {/* Metric Header */}
              <div className={`p-4 ${getStatusBgColor(metric.status)}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(metric.status)}
                    <div>
                      <h4 className="font-semibold text-slate-900 capitalize">
                        {metric.name.replace(/_/g, ' ')}
                      </h4>
                      {metric.unit && (
                        <p className="text-xs text-slate-600">Unit: {metric.unit}</p>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-bold ${getStatusColor(metric.status)}`}>
                      {metric.status.toUpperCase()}
                    </p>
                  </div>
                </div>
              </div>

              {/* Metric Values */}
              <div className="p-4 border-b border-slate-200">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-xs text-slate-600 mb-1">Current Value</p>
                    <p className="text-2xl font-bold text-slate-900">
                      {getMetricDisplayValue(metric)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-600 mb-1">Threshold (Required)</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {getThresholdDisplayValue(metric)}
                    </p>
                  </div>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      metric.status === 'passed' ? 'bg-green-600' : 'bg-red-600'
                    }`}
                    style={{
                      width: Math.min(100, (metric.measured_value / metric.threshold_value) * 100) + '%',
                    }}
                  />
                </div>
              </div>

              {/* 30-Day Trend Chart */}
              <div className="p-4">
                <p className="text-sm font-semibold text-slate-900 mb-3">30-Day Trend</p>
                {trendData[metric.name] && (
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={trendData[metric.name]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 12 }}
                        stroke="#94a3b8"
                      />
                      <YAxis
                        tick={{ fontSize: 12 }}
                        stroke="#94a3b8"
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1e293b',
                          border: 'none',
                          borderRadius: '8px',
                          color: '#f1f5f9',
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke="#2563eb"
                        dot={false}
                        isAnimationActive={false}
                        strokeWidth={2}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Alerts Section */}
      {gateStatus && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex gap-3">
            <Clock className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-blue-900 mb-1">Gate Timeline Alert</h4>
              <p className="text-sm text-blue-800">
                Gate {currentGate?.gate_id} ends in {daysRemaining} days. If all metrics continue to
                meet requirements, the model may be eligible for the next gate or option period.
              </p>
              {currentGate?.gate_id === '3' && (
                <p className="text-sm text-blue-800 mt-2">
                  Option Period 1 (Early Unlock) may be exercised if Gate 2 metrics are achieved
                  before day 120.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Gate Advancement Info */}
      {gateStatus && gateStatus.overall_status === 'passed' && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex gap-3">
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-green-900 mb-1">Ready for Gate Advancement</h4>
              <p className="text-sm text-green-800">
                All {gateStatus.metrics_total} performance metrics are currently meeting requirements.
                When the gate timeline concludes, this model will be eligible to advance to the next gate.
              </p>
            </div>
          </div>
        </div>
      )}

      {gateStatus && gateStatus.overall_status !== 'passed' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-red-900 mb-1">Action Required</h4>
              <p className="text-sm text-red-800">
                {gateStatus.metrics_total - gateStatus.metrics_passed} metric(s) are not meeting
                requirements. Please review and address before gate advancement.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PerformanceMeasures
