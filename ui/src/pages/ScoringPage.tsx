import React, { useState } from 'react'

const ScoringPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string>('')
  const [selectedEntity, setSelectedEntity] = useState<string>('')

  const handleScore = async () => {
    if (!selectedEntity) {
      setStatus('Please select an entity')
      return
    }

    setLoading(true)
    setStatus('Scoring entity...')

    try {
      const response = await fetch(`/api/scoring/score?entity_id=${selectedEntity}`)
      if (response.ok) {
        const data = await response.json()
        setStatus(`Risk Score: ${data.risk_score} | Threat Score: ${data.threat_score}`)
      } else {
        setStatus('Error scoring entity')
      }
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleWhy = async () => {
    if (!selectedEntity) {
      setStatus('Please select an entity')
      return
    }

    setLoading(true)
    setStatus('Fetching explanation...')

    try {
      const response = await fetch(`/api/scoring/why?entity_id=${selectedEntity}`)
      if (response.ok) {
        const data = await response.json()
        setStatus(`Why: ${data.explanation}`)
      } else {
        setStatus('Error fetching explanation')
      }
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-3xl font-bold text-sentry-navy mb-4">Risk Scoring</h2>
      <p className="text-sentry-slate mb-6">
        Apply risk and threat scoring models to resolved entities.
      </p>

      <div className="bg-white p-6 rounded-lg shadow space-y-6">
        <div>
          <label className="block text-sm font-semibold text-sentry-navy mb-2">
            Select Entity
          </label>
          <input
            type="text"
            placeholder="Entity ID"
            value={selectedEntity}
            onChange={(e) => setSelectedEntity(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded"
          />
        </div>

        <div className="flex gap-4">
          <button
            onClick={handleScore}
            disabled={loading || !selectedEntity}
            className={`px-6 py-2 rounded font-semibold transition-all ${
              !loading && selectedEntity
                ? 'bg-sentry-teal text-white hover:bg-sentry-dark-teal'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Score Entity
          </button>

          <button
            onClick={handleWhy}
            disabled={loading || !selectedEntity}
            className={`px-6 py-2 rounded font-semibold transition-all ${
              !loading && selectedEntity
                ? 'bg-sentry-orange text-white hover:opacity-80'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Explain (Why)
          </button>
        </div>

        {status && (
          <div className={`p-3 rounded text-sm ${
            status.includes('Error') ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
          }`}>
            {status}
          </div>
        )}
      </div>
    </div>
  )
}

export default ScoringPage
