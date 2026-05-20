import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkflow } from '../context/WorkflowContext'
import { api } from '../services/api'
import type { ManifestRow } from '../types/sentry'

const IngestPage: React.FC = () => {
  const navigate = useNavigate()
  const { state, setState } = useWorkflow()
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [showAllRows, setShowAllRows] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] || null)
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setLoading(true)
    setError('')
    setState({ ingestLoading: true })

    try {
      const response = await api.ingestManifest(file)

      if (response && response.manifest_id) {
        // Convert API response preview to manifest rows for display
        const rows: ManifestRow[] = (response.preview || []).map((item: any, idx: number) => ({
          rowNumber: idx + 1,
          shipperName: item.shipper || 'N/A',
          shipperCountry: 'XX',
          consigneeName: item.consignee || 'N/A',
          htsCode: item.hts_code || 'N/A',
          declaredOrigin: 'XX',
          declaredValue: item.value_usd || 0,
          status: item.flag_suspicious ? 'flagged' : 'received',
        }))

        setState({
          manifestId: response.manifest_id,
          manifestData: response,
          manifestRows: rows,
          ingestLoading: false,
        })

        setFile(null)
      } else {
        setError('Error ingesting manifest: Invalid response')
        setState({ ingestLoading: false })
      }
    } catch (err) {
      setError(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`)
      setState({ ingestLoading: false })
    } finally {
      setLoading(false)
    }
  }

  const displayedRows = showAllRows ? state.manifestRows : state.manifestRows.slice(0, 5)

  return (
    <div className="max-w-5xl">
      <h2 className="text-3xl font-bold text-sentry-navy mb-4">Manifest Ingest</h2>
      <p className="text-sentry-slate mb-6">
        Upload a CBP manifest (Excel, CSV, or JSON) to begin the Sentry workflow.
      </p>

      {!state.manifestId && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow mb-6">
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

          {error && (
            <div className="mt-4 p-3 rounded bg-red-100 text-red-800">
              {error}
            </div>
          )}
        </form>
      )}

      {state.manifestId && (
        <div>
          <div className="mb-6 p-4 bg-green-100 border border-green-400 rounded-lg">
            <p className="text-green-800 font-semibold">
              Manifest ingested successfully! ({state.manifestRows.length} rows loaded)
            </p>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead className="bg-sentry-navy text-white">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">Shipper</th>
                    <th className="px-4 py-3 text-left font-semibold">Country</th>
                    <th className="px-4 py-3 text-left font-semibold">Consignee</th>
                    <th className="px-4 py-3 text-left font-semibold">HTS Code</th>
                    <th className="px-4 py-3 text-left font-semibold">Origin</th>
                    <th className="px-4 py-3 text-right font-semibold">Value</th>
                    <th className="px-4 py-3 text-left font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedRows.map((row, idx) => (
                    <tr
                      key={idx}
                      className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}
                    >
                      <td className="px-4 py-3 border-b border-gray-200 text-sm">{row.shipperName}</td>
                      <td className="px-4 py-3 border-b border-gray-200 font-mono text-xs font-semibold">{row.shipperCountry}</td>
                      <td className="px-4 py-3 border-b border-gray-200 text-sm">{row.consigneeName}</td>
                      <td className="px-4 py-3 border-b border-gray-200 font-mono text-xs">{row.htsCode}</td>
                      <td className="px-4 py-3 border-b border-gray-200 font-mono text-xs">{row.declaredOrigin}</td>
                      <td className="px-4 py-3 border-b border-gray-200 text-right font-semibold">
                        ${row.declaredValue.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 border-b border-gray-200">
                        {row.status && (
                          <span className={`px-2 py-1 rounded text-xs font-semibold ${
                            row.status === 'flagged'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-green-100 text-green-800'
                          }`}>
                            {row.status === 'flagged' ? 'Flagged' : 'Normal'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {state.manifestRows.length > 5 && !showAllRows && (
              <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
                <button
                  onClick={() => setShowAllRows(true)}
                  className="text-sm text-sentry-teal font-semibold hover:underline"
                >
                  Show all {state.manifestRows.length} rows
                </button>
              </div>
            )}

            {showAllRows && state.manifestRows.length > 5 && (
              <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
                <button
                  onClick={() => setShowAllRows(false)}
                  className="text-sm text-sentry-teal font-semibold hover:underline"
                >
                  Show first 5 rows
                </button>
              </div>
            )}
          </div>

          <div className="flex gap-4">
            <button
              onClick={() => navigate('/entity-resolution')}
              className="px-6 py-3 bg-sentry-teal text-white font-semibold rounded-lg hover:bg-sentry-dark-teal transition-all"
            >
              Analyze Entities →
            </button>
            <button
              onClick={() => {
                setState({
                  manifestId: null,
                  manifestData: null,
                  manifestRows: [],
                  entities: null,
                  entitiesResolved: false,
                  score: null,
                  scoringComplete: false,
                  referralId: null,
                  referralPackage: null,
                })
              }}
              className="px-6 py-3 bg-gray-200 text-sentry-navy font-semibold rounded-lg hover:bg-gray-300 transition-all"
            >
              Upload Another
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default IngestPage
