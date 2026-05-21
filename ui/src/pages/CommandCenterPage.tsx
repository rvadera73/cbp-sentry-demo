import React, { useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import Header from '../components/layout/Header';
import CaseLens from '../components/command-center/CaseLens';
import CommodityLens from '../components/command-center/CommodityLens';
import CorridorLens from '../components/command-center/CorridorLens';
import '../styles/command-center/CommandCenter.css';

interface LensSelectorProps {
  selectedLens: 'case' | 'commodity' | 'corridor';
  onLensChange: (lens: 'case' | 'commodity' | 'corridor') => void;
  onUploadClick: () => void;
}

function LensSelector({ selectedLens, onLensChange, onUploadClick }: LensSelectorProps) {
  const lenses: { id: 'case' | 'commodity' | 'corridor'; label: string; description: string }[] = [
    { id: 'case', label: 'Cases', description: 'All active cases by risk priority' },
    { id: 'commodity', label: 'Commodity Lens', description: 'Industry-level risk analysis' },
    { id: 'corridor', label: 'Corridor Lens', description: 'Port of Entry vessel tracking' },
  ];

  return (
    <div className="lens-selector">
      <div className="lens-selector__controls">
        <div className="lens-selector__label">ANALYTICAL TASK LENSES:</div>
        <button
          className="lens-selector__upload-btn"
          onClick={onUploadClick}
          aria-label="Upload manifest data from Excel file"
        >
          📁 Upload Manifest
        </button>
      </div>
      <div className="lens-selector__group" role="radiogroup" aria-label="Select analytical lens">
        {lenses.map(lens => (
          <label key={lens.id} className={`lens-selector__option ${selectedLens === lens.id ? 'active' : ''}`}>
            <input
              type="radio"
              name="lens"
              value={lens.id}
              checked={selectedLens === lens.id}
              onChange={() => onLensChange(lens.id)}
              aria-label={`${lens.label}: ${lens.description}`}
            />
            <span className="lens-selector__label-text">{lens.label}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

interface Shipment {
  id: string;
  manifest_id: string;
  shipper_name: string;
  consignee_name: string;
  origin_country: string;
  destination_country: string;
  hs_code: string;
  declared_value_usd: number;
  risk_score: number;
  status: string;
}

interface CommandCenterContentProps {
  selectedLens: 'case' | 'commodity' | 'corridor';
}

function CommandCenterContent({ selectedLens }: CommandCenterContentProps) {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(undefined);
      try {
        if (selectedLens === 'case') {
          // Load shipments for case lens using CommandCenter-specific endpoint
          // Fetch 500 records to allow searching across a substantial portion of the dataset
          const response = await fetch('/api/command-center/shipments?limit=500&offset=0');
          if (!response.ok) throw new Error('Failed to fetch shipments');
          const data = await response.json();
          setShipments(data.shipments || []);
        }
      } catch (err) {
        setError(`Failed to load data: ${err}`);
        console.error('Command Center data load error:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [selectedLens]);


  return (
    <div className="command-center__content">
      {loading && (
        <div className="command-center__loading">
          <p>Loading data...</p>
        </div>
      )}

      {error && (
        <div className="command-center__error">
          <p>{error}</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      )}

      {!loading && !error && (
        <>
          {selectedLens === 'case' && <CaseLens cases={shipments} />}
          {selectedLens === 'commodity' && <CommodityLens />}
          {selectedLens === 'corridor' && <CorridorLens />}
        </>
      )}
    </div>
  );
}

export default function CommandCenterPage() {
  const [selectedLens, setSelectedLens] = useState<'case' | 'commodity' | 'corridor'>('case');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/ingest/manifest', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        alert('Manifest uploaded and processed successfully!');
        // Refresh the cases list
        window.location.reload();
      } else {
        alert('Failed to upload manifest');
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Error uploading manifest');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="command-center">
      <Header title="Sentry Command Center" />
      <LensSelector selectedLens={selectedLens} onLensChange={setSelectedLens} onUploadClick={handleUploadClick} />
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xls"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        aria-label="Upload Excel manifest file"
      />
      <CommandCenterContent selectedLens={selectedLens} />
    </div>
  );
}
