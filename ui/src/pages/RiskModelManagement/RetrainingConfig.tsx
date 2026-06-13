import React, { useState, useEffect } from 'react'
import { Clock, ChevronDown } from 'lucide-react'

interface RetrainingConfigProps {
  onSave?: (config: RetrainingConfigData) => void
  onReset?: () => void
}

interface RetrainingConfigData {
  scheduledRetrainingEnabled: boolean
  scheduleFrequency: 'daily' | 'weekly' | 'monthly'
  scheduleDay?: string
  scheduleTime: string
  dataWindow: number
  datasetVersion: 'v1.0' | 'v1.1' | 'v1.2'
  dataDriftEnabled: boolean
  dataDriftThreshold: number
  dataDriftDuration: number
  dataDriftFeatures: number
  modelDriftEnabled: boolean
  modelDriftThreshold: number
  modelDriftEvaluationWindow: number
  modelDriftMinPredictions: number
  errorSpikeEnabled: boolean
  errorSpikeThreshold: number
  errorSpikeDuration: number
  emailNotification: boolean
  slackNotification: boolean
  alertOnFailure: boolean
}

const RetrainingConfig: React.FC<RetrainingConfigProps> = ({ onSave, onReset }) => {
  const [config, setConfig] = useState<RetrainingConfigData>({
    scheduledRetrainingEnabled: true,
    scheduleFrequency: 'weekly',
    scheduleDay: 'Monday',
    scheduleTime: '02:00',
    dataWindow: 7,
    datasetVersion: 'v1.0',
    dataDriftEnabled: true,
    dataDriftThreshold: 0.3,
    dataDriftDuration: 24,
    dataDriftFeatures: 3,
    modelDriftEnabled: true,
    modelDriftThreshold: -2.0,
    modelDriftEvaluationWindow: 7,
    modelDriftMinPredictions: 10000,
    errorSpikeEnabled: false,
    errorSpikeThreshold: 5.0,
    errorSpikeDuration: 30,
    emailNotification: false,
    slackNotification: true,
    alertOnFailure: true,
  })

  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      // TODO: Replace with actual API calls to PUT /api/risk-models/retraining-config
      onSave?.(config)
      setSuccess('Configuration saved successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    const defaultConfig: RetrainingConfigData = {
      scheduledRetrainingEnabled: true,
      scheduleFrequency: 'weekly',
      scheduleDay: 'Monday',
      scheduleTime: '02:00',
      dataWindow: 7,
      datasetVersion: 'v1.0',
      dataDriftEnabled: true,
      dataDriftThreshold: 0.3,
      dataDriftDuration: 24,
      dataDriftFeatures: 3,
      modelDriftEnabled: true,
      modelDriftThreshold: -2.0,
      modelDriftEvaluationWindow: 7,
      modelDriftMinPredictions: 10000,
      errorSpikeEnabled: false,
      errorSpikeThreshold: 5.0,
      errorSpikeDuration: 30,
      emailNotification: false,
      slackNotification: true,
      alertOnFailure: true,
    }
    setConfig(defaultConfig)
    onReset?.()
  }

  const handleSimulateRetrain = async () => {
    try {
      // Simulate retraining with selected dataset
      const response = await fetch('/api/risk-models/simulate-retrain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          datasetVersion: config.datasetVersion,
          referenceShipments: ['SHP-00142857', 'SHP-00142858', 'SHP-00142859']
        })
      })

      if (!response.ok) {
        throw new Error('Simulation failed')
      }

      const result = await response.json()
      setSuccess(`Simulation complete: ${result.message}`)
      setTimeout(() => setSuccess(null), 5000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-sentry-navy mb-2">Retraining Configuration</h1>
        <p className="text-sentry-slate">Set up automated retraining triggers and schedules</p>
      </div>

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-800">
          {success}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      {/* Scheduled Retraining */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-sentry-navy">Scheduled Retraining</h2>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.scheduledRetrainingEnabled}
              onChange={e => setConfig({ ...config, scheduledRetrainingEnabled: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm font-medium text-gray-700">Enable</span>
          </label>
        </div>

        {config.scheduledRetrainingEnabled && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Frequency:</label>
                <select
                  value={config.scheduleFrequency}
                  onChange={e => setConfig({ ...config, scheduleFrequency: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>

              {config.scheduleFrequency === 'weekly' && (
                <div>
                  <label className="text-sm font-semibold text-gray-700 mb-2 block">Day:</label>
                  <select
                    value={config.scheduleDay || 'Monday'}
                    onChange={e => setConfig({ ...config, scheduleDay: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                  >
                    <option>Monday</option>
                    <option>Tuesday</option>
                    <option>Wednesday</option>
                    <option>Thursday</option>
                    <option>Friday</option>
                    <option>Saturday</option>
                    <option>Sunday</option>
                  </select>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Schedule Time:</label>
                <input
                  type="time"
                  value={config.scheduleTime}
                  onChange={e => setConfig({ ...config, scheduleTime: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                />
                <p className="text-xs text-gray-600 mt-1">UTC</p>
              </div>

              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Data Window (days):</label>
                <input
                  type="number"
                  value={config.dataWindow}
                  onChange={e => setConfig({ ...config, dataWindow: parseInt(e.target.value) })}
                  min="1"
                  max="30"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                />
              </div>
            </div>

            <div className="border-t border-gray-200 pt-4">
              <label className="text-sm font-semibold text-gray-700 mb-2 block">Dataset Version:</label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                {(['v1.0', 'v1.1', 'v1.2'] as const).map(version => (
                  <button
                    key={version}
                    onClick={() => setConfig({ ...config, datasetVersion: version })}
                    className={`px-4 py-3 rounded border-2 text-sm font-medium transition ${
                      config.datasetVersion === version
                        ? 'border-sentry-navy bg-blue-50 text-sentry-navy'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    {version}
                    {version === 'v1.0' && <p className="text-xs text-gray-600 mt-1">(Current)</p>}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-600 mt-2">
                {config.datasetVersion === 'v1.0' && 'Current stable dataset with 10,287 samples'}
                {config.datasetVersion === 'v1.1' && 'Upcoming dataset with improved labeling and 12,500 samples'}
                {config.datasetVersion === 'v1.2' && 'Future dataset with extended feature engineering and 15,000 samples'}
              </p>
            </div>

            <div className="bg-gray-50 rounded p-4 space-y-2 text-sm">
              <p className="text-gray-600">
                <span className="font-semibold">Next Scheduled Run:</span> 2026-06-16 02:00 UTC
              </p>
              <p className="text-gray-600">
                <span className="font-semibold">Last Run:</span> 2026-06-09 02:15 UTC (PASSED)
              </p>
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-700 mb-3 block">Notifications:</label>
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.emailNotification}
                    onChange={e => setConfig({ ...config, emailNotification: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-700">Email on training start</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.slackNotification}
                    onChange={e => setConfig({ ...config, slackNotification: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-700">Email on training completion</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.alertOnFailure}
                    onChange={e => setConfig({ ...config, alertOnFailure: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-700">Alert on failure</span>
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Data Drift Trigger */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-sentry-navy">Automatic Trigger: Data Drift</h2>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.dataDriftEnabled}
              onChange={e => setConfig({ ...config, dataDriftEnabled: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm font-medium text-gray-700">Enable</span>
          </label>
        </div>

        {config.dataDriftEnabled && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Drift Threshold (0-1):</label>
                <input
                  type="number"
                  value={config.dataDriftThreshold}
                  onChange={e => setConfig({ ...config, dataDriftThreshold: parseFloat(e.target.value) })}
                  min="0"
                  max="1"
                  step="0.01"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                />
              </div>

              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Persistence Duration (hours):</label>
                <input
                  type="number"
                  value={config.dataDriftDuration}
                  onChange={e => setConfig({ ...config, dataDriftDuration: parseInt(e.target.value) })}
                  min="1"
                  max="168"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                />
              </div>

              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Affected Features (min):</label>
                <input
                  type="number"
                  value={config.dataDriftFeatures}
                  onChange={e => setConfig({ ...config, dataDriftFeatures: parseInt(e.target.value) })}
                  min="1"
                  max="50"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                />
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded p-4 space-y-2 text-sm">
              <p className="text-blue-900 font-semibold">When triggered:</p>
              <ul className="space-y-1 text-blue-800 ml-4">
                <li>• Collect fresh data from drift period</li>
                <li>• Train new model immediately</li>
                <li>• Create as STAGING version</li>
                <li>• Notify ML team for review</li>
                <li>• Await manual approval before deploy</li>
              </ul>
            </div>

            <div className="bg-gray-50 rounded p-4 space-y-1 text-sm">
              <p className="text-gray-600">
                <span className="font-semibold">Last Trigger:</span> 2026-06-05 (Data drift)
              </p>
              <p className="text-gray-600">
                <span className="font-semibold">Resulting Model:</span> v3.0 (Now PRODUCTION)
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Model Drift Trigger */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-sentry-navy">Automatic Trigger: Model Drift</h2>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.modelDriftEnabled}
              onChange={e => setConfig({ ...config, modelDriftEnabled: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm font-medium text-gray-700">Enable</span>
          </label>
        </div>

        {config.modelDriftEnabled && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Degradation Threshold (%):</label>
                <input
                  type="number"
                  value={config.modelDriftThreshold}
                  onChange={e => setConfig({ ...config, modelDriftThreshold: parseFloat(e.target.value) })}
                  step="0.1"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                />
              </div>

              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Evaluation Window (days):</label>
                <input
                  type="number"
                  value={config.modelDriftEvaluationWindow}
                  onChange={e => setConfig({ ...config, modelDriftEvaluationWindow: parseInt(e.target.value) })}
                  min="1"
                  max="30"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                />
              </div>

              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Min Predictions:</label>
                <input
                  type="number"
                  value={config.modelDriftMinPredictions}
                  onChange={e => setConfig({ ...config, modelDriftMinPredictions: parseInt(e.target.value) })}
                  min="1000"
                  max="1000000"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                />
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded p-4 space-y-2 text-sm">
              <p className="text-blue-900 font-semibold">When triggered:</p>
              <ul className="space-y-1 text-blue-800 ml-4">
                <li>• Flag alert in dashboard</li>
                <li>• Collect training data</li>
                <li>• Queue retraining job</li>
                <li>• Notify ML team + managers</li>
                <li>• Consider auto-rollback if critical</li>
              </ul>
            </div>

            <div className="bg-gray-50 rounded p-4 space-y-1 text-sm">
              <p className="text-gray-600">
                <span className="font-semibold">Last Trigger:</span> 2026-06-02 (Model drift)
              </p>
              <p className="text-gray-600">
                <span className="font-semibold">Resulting Model:</span> v3.0 (Now PRODUCTION)
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Error Spike Trigger */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-sentry-navy">Automatic Trigger: Error Spike</h2>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.errorSpikeEnabled}
              onChange={e => setConfig({ ...config, errorSpikeEnabled: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm font-medium text-gray-700">Enable</span>
          </label>
        </div>

        {config.errorSpikeEnabled ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Error Threshold (%):</label>
                <input
                  type="number"
                  value={config.errorSpikeThreshold}
                  onChange={e => setConfig({ ...config, errorSpikeThreshold: parseFloat(e.target.value) })}
                  min="0.1"
                  max="50"
                  step="0.1"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                />
              </div>

              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Persistence Duration (minutes):</label>
                <input
                  type="number"
                  value={config.errorSpikeDuration}
                  onChange={e => setConfig({ ...config, errorSpikeDuration: parseInt(e.target.value) })}
                  min="5"
                  max="240"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm font-medium"
                />
              </div>
            </div>

            <div className="bg-red-50 border border-red-200 rounded p-4 space-y-2 text-sm">
              <p className="text-red-900 font-semibold">When triggered:</p>
              <ul className="space-y-1 text-red-800 ml-4">
                <li>• Alert to on-call engineer</li>
                <li>• Potentially auto-rollback</li>
                <li>• Post-incident review</li>
                <li>• Trigger retraining</li>
              </ul>
            </div>
          </div>
        ) : (
          <div className="bg-gray-50 rounded p-4">
            <p className="text-sm text-gray-600">Currently disabled</p>
            <button className="mt-3 px-4 py-2 text-sm font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90">
              Enable & Configure
            </button>
          </div>
        )}
      </div>

      {/* Settings */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-sentry-navy mb-4">Settings</h2>
        <div className="space-y-3 text-sm mb-6">
          <div className="flex justify-between py-2">
            <span className="text-gray-700">Default Data Source:</span>
            <span className="font-semibold text-sentry-navy">Production Database</span>
          </div>
          <div className="flex justify-between py-2 border-t border-gray-200">
            <span className="text-gray-700">Training Framework:</span>
            <span className="font-semibold text-sentry-navy">XGBoost v1.7</span>
          </div>
          <div className="flex justify-between py-2 border-t border-gray-200">
            <span className="text-gray-700">Hyperparameter Strategy:</span>
            <span className="font-semibold text-sentry-navy">Use Last Params</span>
          </div>
          <div className="flex justify-between py-2 border-t border-gray-200">
            <span className="text-gray-700">Max Concurrent Jobs:</span>
            <span className="font-semibold text-sentry-navy">1</span>
          </div>
          <div className="flex justify-between py-2 border-t border-gray-200">
            <span className="text-gray-700">Model Auto-Deprecation:</span>
            <span className="font-semibold text-sentry-navy">After 90 days</span>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-6">
          <h3 className="text-sm font-semibold text-sentry-navy mb-3">Test Configuration</h3>
          <p className="text-xs text-gray-600 mb-4">
            Simulate retraining with {config.datasetVersion} on reference shipments to see impact
          </p>
          <button
            onClick={handleSimulateRetrain}
            className="px-4 py-2 text-sm font-medium bg-orange-50 text-orange-700 border border-orange-200 rounded hover:bg-orange-100"
          >
            Simulate Retrain with {config.datasetVersion}
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={loading}
          className="px-6 py-2 font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90 disabled:opacity-50"
        >
          {loading ? 'Saving...' : 'Save Configuration'}
        </button>
        <button
          onClick={handleReset}
          className="px-6 py-2 font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
        >
          Reset to Default
        </button>
      </div>
    </div>
  )
}

export default RetrainingConfig
