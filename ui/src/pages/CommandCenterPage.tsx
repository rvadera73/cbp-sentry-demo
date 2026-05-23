import React, { useEffect, useRef, useState } from 'react';
import { FileText, MapPin, Package, Upload } from 'lucide-react';
import Header from '../components/layout/Header';
import CaseLens from '../components/command-center/CaseLens';
import CommodityLens from '../components/command-center/CommodityLens';
import CorridorLens from '../components/command-center/CorridorLens';
import '../styles/command-center/CommandCenter.css';

interface PageTitleBarProps {
  selectedLens: 'case' | 'commodity' | 'corridor';
  uploadMessage: string | null;
}

function PageTitleBar({ selectedLens, uploadMessage }: PageTitleBarProps) {
  const titles = {
    case: 'Command Center',
    commodity: 'Commodity Analysis',
    corridor: 'Corridor Intelligence',
  };

  return (
    <div className="page-title-bar">
      <h1>{titles[selectedLens]}</h1>
      {uploadMessage && (
        <div className="alert-box alert-box--success">
          <div className="alert-box__message">{uploadMessage}</div>
        </div>
      )}
    </div>
  );
}

interface TabBarProps {
  selectedLens: 'case' | 'commodity' | 'corridor';
  onLensChange: (lens: 'case' | 'commodity' | 'corridor') => void;
  onUploadClick: () => void;
}

function TabBar({ selectedLens, onLensChange, onUploadClick }: TabBarProps) {
  const tabs: { id: 'case' | 'commodity' | 'corridor'; label: string; icon: React.ComponentType<any> }[] = [
    { id: 'case', label: 'Cases', icon: FileText },
    { id: 'corridor', label: 'Corridors', icon: MapPin },
    { id: 'commodity', label: 'Commodities', icon: Package },
  ];

  return (
    <div className="tab-bar">
      {tabs.map(tab => {
        const IconComponent = tab.icon;
        return (
          <button
            key={tab.id}
            className={`tab-bar__item ${selectedLens === tab.id ? 'tab-bar__item--active' : ''}`}
            onClick={() => onLensChange(tab.id)}
            aria-selected={selectedLens === tab.id}
            role="tab"
          >
            <IconComponent className="tab-bar__icon" size={16} />
            {tab.label}
          </button>
        );
      })}
      <button
        className="usa-button usa-button--outline"
        style={{ marginLeft: 'auto' }}
        onClick={onUploadClick}
        aria-label="Upload manifest data from Excel file"
      >
        <Upload size={14} />
        Upload Manifest
      </button>
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
  commodity_code: string;
  declared_value: number;
  risk_score: number;
  status: string;
}

interface Corridor {
  id: string;
  route: string;
  industry: string;
  hs_code: string;
  shipment_count: number;
  aggregate_value: number;
  yoy_surge?: {
    volume_surge_pct: number;
    value_surge_pct: number;
  };
  risk_level: string;
}

interface Vessel {
  id: string;
  vessel_name: string;
  imo: number;
  flag_country: string;
  risk_score: number;
  eta: string;
}

interface CommandCenterContentProps {
  selectedLens: 'case' | 'commodity' | 'corridor';
  shipments: Shipment[];
  corridors: Corridor[];
  vessels: Vessel[];
  loading: boolean;
  error?: string;
}

function CommandCenterContent({
  selectedLens,
  shipments,
  corridors,
  vessels,
  loading,
  error,
}: CommandCenterContentProps) {
  return (
    <div className="command-center__content">
      {loading && (
        <div className="command-center__loading">
          <p>Loading data...</p>
        </div>
      )}

      {error && (
        <div className="alert-box alert-box--error">
          <div className="alert-box__message">{error}</div>
        </div>
      )}

      {!loading && !error && (
        <>
          {selectedLens === 'case' && <CaseLens cases={shipments} />}
          {selectedLens === 'commodity' && <CommodityLens corridors={corridors} />}
          {selectedLens === 'corridor' && <CorridorLens vessels={vessels} />}
        </>
      )}
    </div>
  );
}

export default function CommandCenterPage() {
  const [selectedLens, setSelectedLens] = useState<'case' | 'commodity' | 'corridor'>('case');
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [corridors, setCorridors] = useState<Corridor[]>([]);
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load data based on selected lens
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(undefined);
      try {
        if (selectedLens === 'case') {
          const response = await fetch('/api/command-center/shipments?limit=500&offset=0');
          if (!response.ok) throw new Error('Failed to load cases');
          const data = await response.json();
          setShipments(data.shipments || []);
        } else if (selectedLens === 'commodity') {
          const response = await fetch('/api/risk-corridors');
          if (!response.ok) throw new Error('Failed to load corridors');
          const data = await response.json();
          setCorridors(data.corridors || []);
        } else if (selectedLens === 'corridor') {
          const response = await fetch('/api/ports/LA/vessels-of-interest');
          if (!response.ok) throw new Error('Failed to load vessels');
          const data = await response.json();
          setVessels(data.vessels || []);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
        console.error('Data load error:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [selectedLens]);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/ingest/manifest', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        setUploadMessage('Manifest uploaded successfully! Refreshing data...');
        setTimeout(() => {
          setUploadMessage(null);
          window.location.reload();
        }, 2000);
      } else {
        setError('Failed to upload manifest');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError('Error uploading manifest');
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="command-center">
      <Header title="Sentry Command Center" />
      <PageTitleBar selectedLens={selectedLens} uploadMessage={uploadMessage} />
      <TabBar selectedLens={selectedLens} onLensChange={setSelectedLens} onUploadClick={handleUploadClick} />
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xls"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        aria-label="Upload Excel manifest file"
      />
      <CommandCenterContent
        selectedLens={selectedLens}
        shipments={shipments}
        corridors={corridors}
        vessels={vessels}
        loading={loading}
        error={error}
      />
    </div>
  );
}
