import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/layout/Header';
import { AlertTriangle, TrendingUp, Clock, Upload, ArrowRight } from 'lucide-react';
import '../styles/CBPOfficerDashboard.css';

interface Shipment {
  id: string;
  shipper_name: string;
  consignee_name: string;
  origin_country: string;
  destination_country: string;
  hs_code: string;
  declared_value_usd: number;
  risk_score: number;
  vessel_name?: string;
  status: string;
}

export default function CBPOfficerDashboard() {
  const navigate = useNavigate();
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterRisk, setFilterRisk] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  useEffect(() => {
    fetchShipments();
  }, []);

  const fetchShipments = async () => {
    try {
      // Detect API URL based on deployment environment
      const hostname = window.location.hostname;
      let apiUrl = '/api';

      // Cloud Run: extract hash from sentry-ui-{HASH}.run.app
      const cloudRunMatch = hostname.match(/^sentry-ui-(\d+)\.(.+?)\.run\.app$/);
      if (cloudRunMatch) {
        const [, hash, region] = cloudRunMatch;
        apiUrl = `https://sentry-api-${hash}.${region}.run.app/api`;
      } else if (hostname !== 'localhost' && !hostname.startsWith('localhost:')) {
        // For other environments, try to construct API URL
        apiUrl = `https://sentry-api-${hostname.split('-').slice(1).join('-')}`;
      }

      // Call sentry-api (NOT sentry-data directly)
      const response = await fetch(`${apiUrl}/shipments?limit=100`);
      if (!response.ok) throw new Error('Failed to fetch shipments');
      const data = await response.json();
      setShipments(data.shipments || []);
    } catch (error) {
      console.error('Fetch shipments error:', error);
    } finally {
      setLoading(false);
    }
  };

  let displayedShipments = shipments;
  if (filterRisk !== 'all') {
    displayedShipments = shipments.filter(s => {
      const score = s.risk_score || 0;
      if (filterRisk === 'high') return score >= 70;
      if (filterRisk === 'medium') return score >= 40 && score < 70;
      if (filterRisk === 'low') return score < 40;
      return true;
    });
  }

  displayedShipments = [...displayedShipments].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));

  const highRiskCount = shipments.filter(s => (s.risk_score || 0) >= 70).length;
  const mediumRiskCount = shipments.filter(s => (s.risk_score || 0) >= 40 && (s.risk_score || 0) < 70).length;
  const totalValue = shipments.reduce((sum, s) => sum + (s.declared_value_usd || 0), 0);

  const getRiskColor = (score: number) => {
    if (score >= 70) return '#dc2626';
    if (score >= 40) return '#f97316';
    return '#16a34a';
  };

  const getRiskLabel = (score: number) => {
    if (score >= 70) return 'HIGH';
    if (score >= 40) return 'MEDIUM';
    return 'LOW';
  };

  return (
    <div className="cbp-dashboard">
      <Header title="Case Queue" showNav={true} />

      <div className="dashboard-container">
        {/* Statistics Cards */}
        <div className="stats-grid">
          <div className="stat-card critical">
            <div className="stat-icon">
              <AlertTriangle size={24} />
            </div>
            <div className="stat-info">
              <div className="stat-value">{highRiskCount}</div>
              <div className="stat-label">High Risk Cases</div>
              <div className="stat-subtext">Require immediate attention</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <TrendingUp size={24} />
            </div>
            <div className="stat-info">
              <div className="stat-value">{mediumRiskCount}</div>
              <div className="stat-label">Medium Risk Cases</div>
              <div className="stat-subtext">Under investigation</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <Clock size={24} />
            </div>
            <div className="stat-info">
              <div className="stat-value">${(totalValue / 1000000).toFixed(1)}M</div>
              <div className="stat-label">Total Value at Risk</div>
              <div className="stat-subtext">Across all cases</div>
            </div>
          </div>
        </div>

        {/* Manifest Queue Section */}
        <div className="queue-section">
          <div className="queue-header">
            <h2>Manifest Risk Queue</h2>
            <div className="queue-controls">
              <select
                value={filterRisk}
                onChange={(e) => setFilterRisk(e.target.value as any)}
                className="filter-select"
              >
                <option value="all">All Cases ({shipments.length})</option>
                <option value="high">High Risk ({highRiskCount})</option>
                <option value="medium">Medium Risk ({mediumRiskCount})</option>
                <option value="low">Low Risk ({shipments.length - highRiskCount - mediumRiskCount})</option>
              </select>
              <button className="btn-refresh" onClick={fetchShipments}>
                Refresh
              </button>
            </div>
          </div>

          {loading ? (
            <div className="queue-loading">Loading cases...</div>
          ) : displayedShipments.length === 0 ? (
            <div className="queue-empty">
              <Upload size={32} />
              <p>No cases found. Upload a manifest to get started.</p>
              <a href="/upload" className="btn-upload">
                <Upload size={18} />
                Upload Manifest
              </a>
            </div>
          ) : (
            <div className="queue-list">
              {displayedShipments.map((shipment) => (
                <div
                  key={shipment.id}
                  className="queue-item"
                  onClick={() => navigate(`/cases/${shipment.id}`)}
                >
                  <div className="queue-item-header">
                    <div className="risk-badge" style={{ borderLeftColor: getRiskColor(shipment.risk_score) }}>
                      <span className="risk-score">{shipment.risk_score || 0}</span>
                      <span className="risk-label">{getRiskLabel(shipment.risk_score || 0)}</span>
                    </div>
                    <div className="queue-item-main">
                      <h3 className="queue-item-title">
                        {shipment.shipper_name}
                      </h3>
                      <div className="queue-item-meta">
                        <span className="meta-tag">
                          <strong>To:</strong> {shipment.consignee_name.split(' ')[0]}
                        </span>
                        <span className="meta-tag">
                          <strong>Route:</strong> {shipment.origin_country} → {shipment.destination_country}
                        </span>
                        <span className="meta-tag">
                          <strong>HTS:</strong> {shipment.hs_code}
                        </span>
                        <span className="meta-tag">
                          <strong>Value:</strong> ${(shipment.declared_value_usd || 0).toLocaleString()}
                        </span>
                        {shipment.vessel_name && (
                          <span className="meta-tag">
                            <strong>Vessel:</strong> {shipment.vessel_name}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <button className="queue-item-action">
                    <ArrowRight size={18} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
