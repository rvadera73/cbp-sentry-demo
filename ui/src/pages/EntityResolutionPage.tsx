import React, { useState } from 'react'

const EntityResolutionPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string>('')

  const handleResolveEntities = async () => {
    setLoading(true)
    setStatus('Resolving entities...')

    try {
      const response = await fetch('/api/entity-resolution/load')
      if (response.ok) {
        setStatus('Entity resolution complete!')
      } else {
        setStatus('Error resolving entities')
      }
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-3xl font-bold text-sentry-navy mb-4">Entity Resolution</h2>
      <p className="text-sentry-slate mb-6">
        Resolve and deduplicate entities from the ingested manifest using machine learning.
      </p>

      <div className="bg-white p-6 rounded-lg shadow">
        <p className="text-sm text-sentry-slate mb-6">
          This step uses entity resolution models to match and consolidate duplicate entity records
          across the manifest. Resolved entities are linked to their canonical identities.
        </p>

        <button
          onClick={handleResolveEntities}
          disabled={loading}
          className={`px-6 py-2 rounded font-semibold transition-all ${
            !loading
              ? 'bg-sentry-teal text-white hover:bg-sentry-dark-teal'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          {loading ? 'Processing...' : 'Resolve Entities'}
        </button>

        {status && (
          <div className={`mt-4 p-3 rounded ${
            status.includes('Error') ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
          }`}>
            {status}
          </div>
        )}
      </div>
    </div>
  )
}

export default EntityResolutionPage
