import React from 'react';
import { useCommandCenter } from '../../context/CommandCenterContext';
import '../../styles/command-center/CorridorLens.css';

export default function CorridorLens() {
  const { state, setFilters, setVessel } = useCommandCenter();

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'CRITICAL':
      case 'HIGH':
        return '#D9381E';
      case 'MEDIUM':
        return '#E6A100';
      case 'LOW':
        return '#2E8540';
      default:
        return '#6B7280';
    }
  };

  const getRiskBadge = (riskLevel: string) => {
    switch (riskLevel) {
      case 'HIGH':
      case 'CRITICAL':
        return '🔴';
      case 'MEDIUM':
        return '🟡';
      case 'LOW':
        return '🟢';
      default:
        return '⚪';
    }
  };

  return (
    <div className="corridor-lens">
      <div className="corridor-lens__header">
        <h2>Corridor Lens</h2>
        <div className="corridor-lens__controls">
          <select
            value={state.filters.port || 'USLA'}
            onChange={e => setFilters({ port: e.target.value })}
            className="corridor-lens__filter"
            aria-label="Select Port of Entry"
          >
            <option value="USLA">Port of Los Angeles</option>
            <option value="USNJ">Port of New York/New Jersey</option>
            <option value="USSF">Port of San Francisco</option>
            <option value="USHOU">Port of Houston</option>
            <option value="USMI">Port of Miami</option>
          </select>
        </div>
      </div>

      <div className="corridor-lens__content">
        <div className="corridor-lens__left">
          <h3>Vessels of Interest</h3>
          <div className="vessels-list">
            {state.vessels.length === 0 ? (
              <p className="vessels-list__empty">No vessels of interest at this port</p>
            ) : (
              state.vessels.map(vessel => (
                <div
                  key={vessel.vessel_id}
                  className={`vessels-list__item ${state.selectedVessel?.vessel_id === vessel.vessel_id ? 'active' : ''}`}
                  onClick={() => setVessel(vessel)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      setVessel(vessel);
                    }
                  }}
                >
                  <div className="vessels-list__item-header">
                    <span className="vessels-list__risk-badge">{getRiskBadge(vessel.cargo_risk_level)}</span>
                    <span className="vessels-list__name">{vessel.vessel_name}</span>
                  </div>
                  <div className="vessels-list__item-details">
                    <span style={{ color: getRiskColor(vessel.cargo_risk_level) }}>
                      {vessel.cargo_risk_level} RISK
                    </span>
                    <span className="vessels-list__eta">ETA: {vessel.eta || 'Unknown'}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="corridor-lens__right">
          {state.selectedVessel ? (
            <div className="vessel-detail">
              <h3>{state.selectedVessel.vessel_name}</h3>

              <div className="vessel-detail__section">
                <h4>Vessel Information</h4>
                <div className="vessel-detail__grid">
                  <div>
                    <span className="label">Flag State:</span>
                    <span>{state.selectedVessel.flag_state}</span>
                  </div>
                  <div>
                    <span className="label">IMO:</span>
                    <span>{state.selectedVessel.vessel_id}</span>
                  </div>
                  <div>
                    <span className="label">Current Port:</span>
                    <span>{state.selectedVessel.current_port}</span>
                  </div>
                  <div>
                    <span className="label">Status:</span>
                    <span>{state.selectedVessel.status}</span>
                  </div>
                </div>
              </div>

              <div className="vessel-detail__section">
                <h4>Port Call History</h4>
                <div className="port-calls-table">
                  <div className="port-calls-table__header">
                    <div>Port</div>
                    <div>Arrival</div>
                    <div>Dwell</div>
                    <div>Status</div>
                  </div>
                  <div className="port-calls-table__body">
                    {/* Placeholder - would be populated from API */}
                    <div className="port-calls-table__row">
                      <div>Port of Guangzhou</div>
                      <div>2026-05-05</div>
                      <div>7 days</div>
                      <div style={{ color: '#D9381E' }}>⚠️ ANOMALY</div>
                    </div>
                    <div className="port-calls-table__row">
                      <div>Port of Hong Kong</div>
                      <div>2026-05-13</div>
                      <div>2 days</div>
                      <div style={{ color: '#2E8540' }}>✓ Normal</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="vessel-detail__section">
                <h4>FTZ Dwell Events</h4>
                <div className="ftz-events">
                  <div className="ftz-event ftz-event--warning">
                    <span className="ftz-event__label">FTZ-80 Los Angeles</span>
                    <span className="ftz-event__dwell">7 days (HIGH RISK)</span>
                  </div>
                </div>
              </div>

              <div className="vessel-detail__section">
                <h4>Route Anomalies</h4>
                <ul className="anomalies-list">
                  <li>Port of Guangzhou dwell: 7 days (3.3× baseline)</li>
                  <li>Transshipment routing via Hong Kong detected</li>
                  <li>AIS signal gap: 18 hours near Sulu Strait</li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="vessel-detail__empty">
              <p>Select a vessel to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
