import { useState, useEffect } from 'react';
import { X, Upload, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import { API_BASE_URL } from '../../services/apiUrl';

interface Props {
  onClose: () => void;
  onComplete: () => void;
}

interface JobStatus {
  id: string;
  filename: string;
  status: 'pending' | 'processing' | 'complete' | 'failed';
  total_rows: number;
  processed_rows: number;
  inserted_rows: number;
  duplicate_rows: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  error_count: number;
  errors?: any[];
  elapsed_seconds?: number;
  progress_pct?: number;
}

export default function UploadPipelineModal({ onClose, onComplete }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/ingest/manifest`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      setUploading(false);

      setTimeout(() => {
        onComplete();
        onClose();
      }, 2000);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'An unexpected error occurred during upload';
      setError(errorMsg);
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Upload Manifest</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" disabled={uploading && !result}>
            <X size={20} />
          </button>
        </div>

        {error ? (
          <div className="space-y-4">
            <div className="p-4 bg-red-50 border border-red-300 rounded-lg flex gap-3">
              <AlertCircle size={24} className="text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold text-red-900">Upload failed</p>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
            <button
              onClick={() => {
                setError(null);
                setFile(null);
                setResult(null);
              }}
              className="w-full py-2 px-4 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        ) : result ? (
          <div className="space-y-6 py-4">
            <div className="text-center">
              <div className="flex justify-center mb-4">
                <CheckCircle size={64} className="text-green-600" />
              </div>
              <p className="font-bold text-green-900 text-2xl">Upload Successful!</p>
              <p className="text-green-700 mt-2">Manifest has been processed and added to the system.</p>
            </div>

            <div className="bg-gray-50 p-6 rounded-lg space-y-4">
              <h3 className="font-bold text-lg text-gray-900">Upload Summary Report</h3>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white p-4 rounded border border-gray-200">
                  <p className="text-sm text-gray-600 font-medium">Total Rows Parsed</p>
                  <p className="text-3xl font-bold text-gray-900 mt-1">{result.total_rows}</p>
                </div>

                <div className="bg-white p-4 rounded border border-gray-200">
                  <p className="text-sm text-gray-600 font-medium">Records Inserted</p>
                  <p className="text-3xl font-bold text-blue-600 mt-1">{result.inserted_rows}</p>
                </div>

                <div className="bg-white p-4 rounded border border-gray-200">
                  <p className="text-sm text-gray-600 font-medium">Duplicates Skipped</p>
                  <p className="text-3xl font-bold text-amber-600 mt-1">{result.duplicate_rows}</p>
                </div>

                <div className="bg-white p-4 rounded border border-gray-200">
                  <p className="text-sm text-gray-600 font-medium">Parse Errors</p>
                  <p className="text-3xl font-bold text-red-600 mt-1">{result.error_count}</p>
                </div>
              </div>

              <div className="bg-white p-4 rounded border border-gray-200">
                <p className="font-bold text-gray-900 mb-3">Risk Score Breakdown</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-600"></div>
                      <span className="text-sm font-medium text-gray-700">High Risk (≥80)</span>
                    </div>
                    <span className="text-lg font-bold text-red-600">{result.high_risk_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                      <span className="text-sm font-medium text-gray-700">Medium Risk (50-79)</span>
                    </div>
                    <span className="text-lg font-bold text-amber-600">{result.medium_risk_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-green-600"></div>
                      <span className="text-sm font-medium text-gray-700">Low Risk (&lt;50)</span>
                    </div>
                    <span className="text-lg font-bold text-green-600">{result.low_risk_count}</span>
                  </div>
                </div>
              </div>

              {result.elapsed_seconds && (
                <p className="text-xs text-gray-500 text-center">Completed in {result.elapsed_seconds}s</p>
              )}
            </div>
          </div>
        ) : uploading ? (
          <div className="space-y-6 py-4">
            <div className="flex items-center justify-center mb-6">
              <Loader size={40} className="text-blue-600 animate-spin" />
            </div>
            <p className="text-center text-gray-600">Processing manifest... this may take a minute</p>
          </div>
        ) : (
          <>
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center mb-4 transition-colors ${
                error ? 'border-red-300 bg-red-50' : 'border-gray-300 hover:border-blue-400'
              }`}
              onDrop={(e) => {
                e.preventDefault();
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                  setFile(files[0]);
                  setError(null);
                  setResult(null);
                  console.log('File selected via drag-drop:', files[0].name);
                }
              }}
              onDragOver={(e) => e.preventDefault()}
            >
              <Upload size={32} className={`mx-auto mb-2 ${error ? 'text-red-400' : 'text-gray-400'}`} />
              <p className="text-sm font-semibold text-gray-700 mb-1">
                {file ? file.name : 'Drop Excel file or click to select'}
              </p>
              {file && <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)}K</p>}
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={(e) => {
                  const selectedFile = e.target.files?.[0] || null;
                  setFile(selectedFile);
                  setError(null);
                  setResult(null);
                  if (selectedFile) {
                    console.log('File selected via file picker:', selectedFile.name);
                  }
                }}
                className="hidden"
                id="file-input"
              />
              <label htmlFor="file-input" className="text-sm text-blue-600 hover:underline cursor-pointer inline-block mt-2">
                Select file
              </label>
            </div>

            <button
              onClick={handleUpload}
              disabled={!file}
              className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
            >
              Upload & Analyze
            </button>
          </>
        )}
      </div>
    </div>
  );
}
