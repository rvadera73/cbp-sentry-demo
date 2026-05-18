import React, { useState } from 'react'

const IngestPage: React.FC = () => {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string>('')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] || null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setLoading(true)
    setStatus('Uploading manifest...')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/ingest/manifest', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        setStatus('Manifest ingested successfully!')
        setFile(null)
      } else {
        setStatus('Error ingesting manifest')
      }
    } catch (error) {
      setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-3xl font-bold text-sentry-navy mb-4">Manifest Ingest</h2>
      <p className="text-sentry-slate mb-6">
        Upload a CBP manifest (Excel, CSV, or JSON) to begin the Sentry workflow.
      </p>

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow">
        <div className="mb-6">
          <label className="block text-sm font-semibold text-sentry-navy mb-2">
            Select Manifest File
          </label>
          <input
            type="file"
            onChange={handleFileChange}
            accept=".xlsx,.csv,.json"
            className="w-full"
            disabled={loading}
          />
        </div>

        <button
          type="submit"
          disabled={!file || loading}
          className={`px-6 py-2 rounded font-semibold transition-all ${
            file && !loading
              ? 'bg-sentry-teal text-white hover:bg-sentry-dark-teal'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          {loading ? 'Ingesting...' : 'Ingest Manifest'}
        </button>

        {status && (
          <div className={`mt-4 p-3 rounded ${
            status.includes('Error') ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
          }`}>
            {status}
          </div>
        )}
      </form>
    </div>
  )
}

export default IngestPage
