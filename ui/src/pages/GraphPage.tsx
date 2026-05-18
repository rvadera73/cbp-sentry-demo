import React, { useState } from 'react'

const GraphPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string>('')

  const handleGenerateGraph = async () => {
    setLoading(true)
    setStatus('Generating knowledge graph...')

    try {
      const response = await fetch('/api/graph/build')
      if (response.ok) {
        setStatus('Knowledge graph generated!')
      } else {
        setStatus('Error generating graph')
      }
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-3xl font-bold text-sentry-navy mb-4">Knowledge Graph</h2>
      <p className="text-sentry-slate mb-6">
        Build and explore relationship networks using Neo4j knowledge graph.
      </p>

      <div className="bg-white p-6 rounded-lg shadow">
        <p className="text-sm text-sentry-slate mb-6">
          Generate a network graph showing relationships between entities, organizations,
          locations, and events identified through the Sentry workflow.
        </p>

        <button
          onClick={handleGenerateGraph}
          disabled={loading}
          className={`px-6 py-2 rounded font-semibold transition-all ${
            !loading
              ? 'bg-sentry-teal text-white hover:bg-sentry-dark-teal'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          {loading ? 'Building...' : 'Generate Knowledge Graph'}
        </button>

        {status && (
          <div className={`mt-4 p-3 rounded ${
            status.includes('Error') ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
          }`}>
            {status}
          </div>
        )}

        <div className="mt-6 p-4 bg-gray-50 rounded border border-gray-200 text-sm text-sentry-slate">
          <p className="font-semibold mb-2">Graph Visualization Placeholder</p>
          <p>Network graph will be rendered here once generated.</p>
        </div>
      </div>
    </div>
  )
}

export default GraphPage
