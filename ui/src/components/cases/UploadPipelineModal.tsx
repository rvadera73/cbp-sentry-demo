import { useState, useEffect } from 'react';
import { X, Upload, CheckCircle } from 'lucide-react';

interface Props {
  onClose: () => void;
  onComplete: () => void;
}

export default function UploadPipelineModal({ onClose, onComplete }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const hostname = window.location.hostname;
      let apiUrl = '/api';

      const cloudRunMatch = hostname.match(/^sentry-ui-(\d+)\.(.+?)\.run\.app$/);
      if (cloudRunMatch) {
        const [, hash, region] = cloudRunMatch;
        apiUrl = `https://sentry-api-${hash}.${region}.run.app/api`;
      } else if (hostname !== 'localhost' && !hostname.startsWith('localhost:')) {
        apiUrl = `https://sentry-api-${hostname.split('-').slice(1).join('-')}`;
      }

      const response = await fetch(`${apiUrl}/ingest/manifest`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        setProgress(100);
        setTimeout(() => {
          onComplete();
          onClose();
        }, 1000);
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Upload Manifest</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {!uploading ? (
          <>
            <div
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center mb-4"
              onDrop={(e) => {
                e.preventDefault();
                const files = e.dataTransfer.files;
                if (files.length > 0) setFile(files[0]);
              }}
              onDragOver={(e) => e.preventDefault()}
            >
              <Upload size={32} className="mx-auto mb-2 text-gray-400" />
              <p className="text-sm text-gray-600">
                {file ? file.name : 'Drop Excel file or click to select'}
              </p>
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden"
                id="file-input"
              />
              <label htmlFor="file-input" className="text-sm text-blue-600 hover:underline cursor-pointer">
                Select file
              </label>
            </div>

            <button
              onClick={handleUpload}
              disabled={!file}
              className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400"
            >
              Upload & Analyze
            </button>
          </>
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-sm font-semibold mb-2">Processing manifest...</p>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
            {progress === 100 && (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle size={20} />
                <span className="font-semibold">Upload complete!</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
