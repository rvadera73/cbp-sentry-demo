import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import USWDSLayout from '../components/layout/USWDSLayout';
import '../styles/Dashboard.css';

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
  h1_score?: number;
  h2_score?: number;
  vessel_name?: string;
  status: string;
}

export default function DashboardPageUSWDS() {
  const navigate = useNavigate();
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchShipments();
  }, []);

  const fetchShipments = async () => {
    try {
      const response = await fetch('http://localhost:8005/shipments');
      const data = await response.json();
      setShipments(data.data || []);
    } catch (error) {
      console.error('Failed to fetch shipments:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 70) return 'risk-high';
    if (score >= 50) return 'risk-medium';
    return 'risk-low';
  };

  const getRiskLabel = (score: number) => {
    if (score >= 70) return 'HIGH';
    if (score >= 50) return 'MEDIUM';
    return 'LOW';
  };

  const filteredShipments = shipments.filter((s) => {
    if (filter === 'high') return s.risk_score >= 70;
    if (filter === 'medium') return s.risk_score >= 50 && s.risk_score < 70;
    if (filter === 'low') return s.risk_score < 50;
    return true;
  }).sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));

  const highRiskCount = shipments.filter(s => s.risk_score >= 70).length;
  const mediumRiskCount = shipments.filter(s => s.risk_score >= 50 && s.risk_score < 70).length;

  return (
    <USWDSLayout
      title="Shipment Intelligence Dashboard"
      subtitle="CBP Trade Enforcement & Customs Risk Assessment"
    >
      {/* KPI Section */}
      <div className="kpi-section">
        <div className="kpi-card">
          <div className="kpi-label">Total Shipments</div>
          <div className="kpi-value">{shipments.length}</div>
        </div>
        <div className="kpi-card alert-red">
          <div className="kpi-label">🚨 High Risk</div>
          <div className="kpi-value">{highRiskCount}</div>
        </div>
        <div className="kpi-card alert-yellow">
          <div className="kpi-label">⚠️ Medium Risk</div>
          <div className="kpi-value">{mediumRiskCount}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">📤 Upload New</div>
          <button
            className="usa-button usa-button--primary"
            onClick={() => navigate('/ingest')}
          >
            Upload Manifest
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="filter-section">
        <label htmlFor="risk-filter">Filter by Risk Level:</label>
        <select
          id="risk-filter"
          className="usa-select"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="all">All Shipments ({shipments.length})</option>
          <option value="high">High Risk ({highRiskCount})</option>
          <option value="medium">Medium Risk ({mediumRiskCount})</option>
          <option value="low">Low Risk</option>
        </select>
      </div>

      {/* Shipments Table */}
      <div className="data-table-wrapper">
        {loading ? (
          <div className="loading">Loading shipments...</div>
        ) : filteredShipments.length === 0 ? (
          <div className="empty-state">
            <p>No shipments found. <button onClick={() => navigate('/ingest')}>Upload a manifest</button> to get started.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Risk Score</th>
                <th>Shipper Name</th>
                <th>Origin → Destination</th>
                <th>Commodity (HTS)</th>
                <th>Vessel</th>
                <th>Declared Value</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredShipments.map((shipment) => (
                <tr key={shipment.id} className="shipment-row">
                  <td className="risk-col">
                    <div className={`risk-badge ${getRiskColor(shipment.risk_score || 0)}`}>
                      <strong>{Math.round(shipment.risk_score || 0)}</strong>
                      <br />
                      <small>{getRiskLabel(shipment.risk_score || 0)}</small>
                    </div>
                  </td>
                  <td>{shipment.shipper_name}</td>
                  <td>{shipment.origin_country} → {shipment.destination_country}</td>
                  <td><code>{shipment.hs_code}</code></td>
                  <td>{shipment.vessel_name || '—'}</td>
                  <td>${shipment.declared_value_usd?.toLocaleString() || '—'}</td>
                  <td>
                    <button
                      className="usa-button usa-button--secondary usa-button--small"
                      onClick={() => navigate(`/case-investigation/${shipment.id}`)}
                    >
                      Investigate
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </USWDSLayout>
  );
}
