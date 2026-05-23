import React, { useState } from 'react';
import { getRiskLevel } from '../../utils/risk';
import '../../styles/command-center/CorridorLens.css';

interface Vessel {
  id: string;
  vessel_name: string;
  imo: number;
  flag_country: string;
  risk_score: number;
  eta: string;
}

interface CorridorLensProps {
  vessels?: Vessel[];
}

export default function CorridorLens({ vessels = [] }: CorridorLensProps) {
  const [selectedVessel, setSelectedVessel] = useState<Vessel | null>(null);
  const [port, setPort] = useState('LA');


  return (
    <div className="corridor-lens">
      <div className="corridor-lens__header">
        <h2>Corridor Lens</h2>
        <div className="corridor-lens__controls">
          <select
            value={port}
            onChange={e => setPort(e.target.value)}
            className="corridor-lens__filter"
            aria-label="Select Port of Entry"
          >
            <option value="LA">Port of Los Angeles</option>
            <option value="NJ">Port of New York/New Jersey</option>
            <option value="SF">Port of San Francisco</option>
            <option value="HOU">Port of Houston</option>
            <option value="MI">Port of Miami</option>
          </select>
        </div>
      </div>

      <div className="corridor-lens__content">
        <div className="corridor-lens__left">
          <h3>Vessels of Interest</h3>
          <div className="vessels-list">
            {vessels.length === 0 ? (
              <p className="vessels-list__empty">No vessels of interest at this port</p>
            ) : (
              vessels.map(vessel => (
                <div
                  key={vessel.id}
                  className={`vessels-list__item ${selectedVessel?.id === vessel.id ? 'active' : ''}`}
                  onClick={() => setSelectedVessel(vessel)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      setSelectedVessel(vessel);
                    }
                  }}
                >
                  <div className="vessels-list__item-header">
                    <span className="vessels-list__risk-badge">{getRiskLevel(vessel.risk_score).substring(0, 1)}</span>
                    <span className="vessels-list__name">{vessel.vessel_name}</span>
                  </div>
                  <div className="vessels-list__item-details">
                    <span>{getRiskLevel(vessel.risk_score)} RISK</span>
                    <span className="vessels-list__eta">ETA: {vessel.eta || 'Unknown'}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="corridor-lens__right">
          {selectedVessel ? (
            <div className="vessel-detail">
              <h3>{selectedVessel.vessel_name}</h3>

              <div className="vessel-detail__section">
                <h4>Vessel Information</h4>
                <div className="vessel-detail__grid">
                  <div>
                    <span className="label">Flag State:</span>
                    <span>{selectedVessel.flag_country}</span>
                  </div>
                  <div>
                    <span className="label">IMO:</span>
                    <span>{selectedVessel.imo}</span>
                  </div>
                  <div>
                    <span className="label">Risk Score:</span>
                    <span>{selectedVessel.risk_score.toFixed(0)}</span>
                  </div>
                  <div>
                    <span className="label">ETA:</span>
                    <span>{selectedVessel.eta}</span>
                  </div>
                </div>
              </div>

              <div className="vessel-detail__section">
                <p style={{ color: '#666', fontSize: '13px' }}>
                  Detailed port call history and route analysis would be populated from vessel tracking API when data is available.
                </p>
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
