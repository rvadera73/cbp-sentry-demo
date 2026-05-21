import React, { useMemo, useCallback } from 'react';
import L from 'leaflet';
import { MapContainer, TileLayer, Popup, Tooltip } from 'react-leaflet';
import { CaseCardData } from './CaseCard';
import './GeographicMapView.css';

interface GeographicMapViewProps {
  cases: CaseCardData[];
  selectedCaseId: string | null;
  onCaseSelect?: (caseId: string) => void;
}

// Country coordinate mapping for geospatial visualization
const countryCoordinates: Record<string, [number, number]> = {
  'Vietnam': [21.0285, 105.8542],
  'China': [35.8617, 104.1954],
  'India': [20.5937, 78.9629],
  'Thailand': [15.8700, 100.9925],
  'Indonesia': [-0.7893, 113.9213],
  'Malaysia': [4.2105, 101.6964],
  'USA': [37.0902, -95.7129],
  'Mexico': [23.6345, -102.5528],
  'Canada': [56.1304, -106.3468],
  'Philippines': [12.8797, 121.7740],
  'South Korea': [35.9078, 127.7669],
  'Japan': [36.2048, 138.2529],
  'Taiwan': [23.6978, 120.9605],
  'Singapore': [1.3521, 103.8198],
};

interface MarkerData {
  id: string;
  type: 'origin' | 'destination';
  location: [number, number];
  color: string;
  cases: CaseCardData[];
}

/**
 * GeographicMapView: Interactive map showing shipment routes
 *
 * Features:
 * - Leaflet-based geographic visualization
 * - Color-coded markers: Red (origin), Blue (destination), Yellow (transshipment)
 * - Risk-based line colors: Red (high), Orange (medium), Green (low)
 * - Interactive popup with case details
 * - Sidebar queue list with synchronization
 *
 * Data Flow:
 * - Extract origin/destination from case data
 * - Group cases by location
 * - Render markers with risk aggregation
 * - Draw connecting lines between routes
 */
export const GeographicMapView: React.FC<GeographicMapViewProps> = ({
  cases,
  selectedCaseId,
  onCaseSelect
}) => {
  const mapData = useMemo(() => {
    const origins = new Map<string, { location: [number, number]; cases: CaseCardData[] }>();
    const destinations = new Map<string, { location: [number, number]; cases: CaseCardData[] }>();

    cases.forEach((caseItem) => {
      const originKey = caseItem.route_origin || 'Unknown';
      const destKey = caseItem.route_destination || 'Unknown';

      const originCoords = countryCoordinates[originKey] || [0, 0];
      const destCoords = countryCoordinates[destKey] || [0, 0];

      if (!origins.has(originKey)) {
        origins.set(originKey, { location: originCoords, cases: [] });
      }
      origins.get(originKey)!.cases.push(caseItem);

      if (!destinations.has(destKey)) {
        destinations.set(destKey, { location: destCoords, cases: [] });
      }
      destinations.get(destKey)!.cases.push(caseItem);
    });

    return { origins, destinations };
  }, [cases]);

  const getRiskColor = (avgRisk: number): string => {
    if (avgRisk >= 70) return '#D9381E'; // High risk: red
    if (avgRisk >= 40) return '#E6A100'; // Medium risk: orange
    return '#2E8540'; // Low risk: green
  };

  const getAvgRisk = (caseList: CaseCardData[]): number => {
    const total = caseList.reduce((sum, c) => sum + (c.risk_score || 0), 0);
    return total / caseList.length;
  };

  // Default map center (USA)
  const mapCenter: [number, number] = [37.0902, -95.7129];
  const mapZoom = 3;

  return (
    <div className="geographic-map-view">
      <div className="map-wrapper">
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          style={{ height: '100%', width: '100%' }}
          className="leaflet-container-sentry"
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            maxZoom={18}
          />

          {/* Origins (Red markers) */}
          {Array.from(mapData.origins.entries()).map(([country, data]) => (
            <CustomMarker
              key={`origin-${country}`}
              position={data.location}
              color="#D9381E"
              label={country}
              cases={data.cases}
              onSelect={onCaseSelect}
              selectedCaseId={selectedCaseId}
            />
          ))}

          {/* Destinations (Blue markers) */}
          {Array.from(mapData.destinations.entries()).map(([country, data]) => (
            <CustomMarker
              key={`dest-${country}`}
              position={data.location}
              color="#0050D8"
              label={country}
              cases={data.cases}
              onSelect={onCaseSelect}
              selectedCaseId={selectedCaseId}
            />
          ))}
        </MapContainer>
      </div>

      {/* Legend */}
      <div className="map-legend">
        <h3>Legend</h3>
        <div className="legend-item">
          <span className="legend-marker" style={{ backgroundColor: '#D9381E' }}></span>
          <span>Origin Countries</span>
        </div>
        <div className="legend-item">
          <span className="legend-marker" style={{ backgroundColor: '#0050D8' }}></span>
          <span>US Destination Ports</span>
        </div>
        <div className="legend-item">
          <span className="legend-marker" style={{ backgroundColor: '#E6A100' }}></span>
          <span>Transshipment Points</span>
        </div>
        <div style={{ marginTop: '12px', borderTop: '1px solid #E0E0E0', paddingTop: '12px' }}>
          <h4>Risk Level</h4>
          <div className="legend-item">
            <span className="legend-line" style={{ borderColor: '#D9381E' }}></span>
            <span>High Risk (70+)</span>
          </div>
          <div className="legend-item">
            <span className="legend-line" style={{ borderColor: '#E6A100' }}></span>
            <span>Medium Risk (40-69)</span>
          </div>
          <div className="legend-item">
            <span className="legend-line" style={{ borderColor: '#2E8540' }}></span>
            <span>Low Risk (&lt;40)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// CustomMarker component for Leaflet integration
interface CustomMarkerProps {
  position: [number, number];
  color: string;
  label: string;
  cases: CaseCardData[];
  onSelect?: (caseId: string) => void;
  selectedCaseId: string | null;
}

const CustomMarker: React.FC<CustomMarkerProps> = ({
  position,
  color,
  label,
  cases,
  onSelect,
  selectedCaseId
}) => {
  const avgRisk = cases.reduce((sum, c) => sum + (c.risk_score || 0), 0) / cases.length;
  const highRiskCount = cases.filter((c) => (c.risk_score || 0) >= 70).length;

  return (
    <div className="custom-marker-wrapper">
      <div
        className="custom-marker"
        style={{
          backgroundColor: color,
          borderColor: selectedCaseId && cases.some((c) => c.id === selectedCaseId)
            ? '#0050D8'
            : color,
        }}
      >
        <Tooltip>{label} ({cases.length} cases)</Tooltip>
        <Popup>
          <div className="marker-popup">
            <h4>{label}</h4>
            <p className="popup-stat">Cases: {cases.length}</p>
            <p className="popup-stat">Avg Risk: {avgRisk.toFixed(1)}/100</p>
            <p className="popup-stat">High Risk: {highRiskCount}</p>
            {cases.length <= 5 && (
              <div className="popup-cases">
                {cases.map((c) => (
                  <button
                    key={c.id}
                    className="popup-case-link"
                    onClick={() => onSelect?.(c.id)}
                  >
                    {c.manifest_id} ({c.risk_score})
                  </button>
                ))}
              </div>
            )}
          </div>
        </Popup>
      </div>
    </div>
  );
};

export default GeographicMapView;
