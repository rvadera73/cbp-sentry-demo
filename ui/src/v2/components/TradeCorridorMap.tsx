import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

interface TradeRoute {
  origin_country: string;
  destination_country: string;
  shipment_count: number;
  avg_risk_score: number;
  avg_dwell_days: number;
  anomaly_count: number;
}

interface TradeCorridorMapProps {
  routes?: TradeRoute[];
  height?: number;
  centerCountry?: string;
}

// Country coordinates (simplified for demonstration)
const COUNTRY_COORDINATES: Record<string, [number, number]> = {
  'Vietnam': [14.0583, 108.2772],
  'Hong Kong': [22.3193, 114.1694],
  'Singapore': [1.3521, 103.8198],
  'USA': [37.0902, -95.7129],
  'China': [35.8617, 104.1954],
  'Japan': [36.2048, 138.2529],
  'Malaysia': [4.2105, 101.6964],
  'Thailand': [15.8700, 100.9925],
  'Indonesia': [-0.7893, 113.9213],
  'Philippines': [12.8797, 121.7740],
  'South Korea': [35.9078, 127.7669],
  'Taiwan': [23.6978, 120.9605],
  'India': [20.5937, 78.9629],
  'Mexico': [23.6345, -102.5528],
  'Canada': [56.1304, -106.3468],
};

function getRiskColor(score: number): string {
  if (score >= 80) return '#D83933';
  if (score >= 60) return '#FF9500';
  if (score >= 40) return '#F59E0B';
  return '#22c55e';
}

const FIXTURE_ROUTES: TradeRoute[] = [
  {
    origin_country: 'Vietnam',
    destination_country: 'USA',
    shipment_count: 12,
    avg_risk_score: 68,
    avg_dwell_days: 8,
    anomaly_count: 3,
  },
  {
    origin_country: 'Hong Kong',
    destination_country: 'USA',
    shipment_count: 8,
    avg_risk_score: 72,
    avg_dwell_days: 6,
    anomaly_count: 2,
  },
  {
    origin_country: 'Singapore',
    destination_country: 'USA',
    shipment_count: 15,
    avg_risk_score: 45,
    avg_dwell_days: 5,
    anomaly_count: 1,
  },
  {
    origin_country: 'China',
    destination_country: 'USA',
    shipment_count: 24,
    avg_risk_score: 62,
    avg_dwell_days: 7,
    anomaly_count: 4,
  },
];

export default function TradeCorridorMap({
  routes = FIXTURE_ROUTES,
  height = 400,
  centerCountry = 'USA',
}: TradeCorridorMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    // Initialize map
    const centerCoords = COUNTRY_COORDINATES[centerCountry] || [20, -10];
    map.current = L.map(mapContainer.current).setView([centerCoords[0], centerCoords[1]], 3);

    // Add CartoDB dark tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; CartoDB',
      subdomains: 'abcd',
      maxZoom: 19,
      minZoom: 2,
    }).addTo(map.current);

    // Add country markers
    const markedCountries = new Set<string>();
    routes.forEach((route) => {
      [route.origin_country, route.destination_country].forEach((country) => {
        if (!markedCountries.has(country) && COUNTRY_COORDINATES[country]) {
          markedCountries.add(country);
          const coords = COUNTRY_COORDINATES[country];
          const color = getRiskColor(
            routes
              .filter((r) => r.origin_country === country || r.destination_country === country)
              .reduce((sum, r) => sum + r.avg_risk_score, 0) /
              routes.filter((r) => r.origin_country === country || r.destination_country === country).length
          );

          const marker = L.circleMarker([coords[0], coords[1]], {
            radius: 8,
            fillColor: color,
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8,
          }).addTo(map.current!);

          marker.bindPopup(
            `<div class="text-xs"><strong>${country}</strong><br/>Risk data available</div>`
          );
        }
      });
    });

    // Add routes as polylines
    routes.forEach((route) => {
      const origin = COUNTRY_COORDINATES[route.origin_country];
      const dest = COUNTRY_COORDINATES[route.destination_country];

      if (origin && dest) {
        const color = getRiskColor(route.avg_risk_score);
        const weight = Math.max(1, Math.min(5, route.shipment_count / 5));
        const dashArray = route.avg_risk_score >= 60 ? '5,5' : 'none';

        const polyline = L.polyline([origin, dest], {
          color: color,
          weight: weight,
          opacity: 0.7,
          dashArray: dashArray,
        }).addTo(map.current!);

        polyline.bindPopup(
          `<div class="text-xs">
            <strong>${route.origin_country} → ${route.destination_country}</strong><br/>
            Shipments: ${route.shipment_count}<br/>
            Avg Risk: ${route.avg_risk_score}%<br/>
            Avg Dwell: ${route.avg_dwell_days}d<br/>
            Anomalies: ${route.anomaly_count}
          </div>`
        );
      }
    });

    // Cleanup on unmount
    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [routes, centerCountry]);

  return (
    <div className="w-full bg-white rounded-sm border border-[#D0D7DE] p-4 shadow-sm">
      <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-3">Trade Corridor Map</div>

      <div
        ref={mapContainer}
        style={{ height: `${height}px`, borderRadius: '4px', overflow: 'hidden' }}
        className="border border-[#D0D7DE] mb-4"
      />

      {/* Legend */}
      <div className="grid grid-cols-4 gap-3 text-[8px]">
        <div className="flex items-center gap-2">
          <div style={{ width: '12px', height: '12px', background: '#D83933', borderRadius: '50%' }} />
          <span className="font-bold">Critical (≥80)</span>
        </div>
        <div className="flex items-center gap-2">
          <div style={{ width: '12px', height: '12px', background: '#FF9500', borderRadius: '50%' }} />
          <span className="font-bold">High (60-79)</span>
        </div>
        <div className="flex items-center gap-2">
          <div style={{ width: '12px', height: '12px', background: '#F59E0B', borderRadius: '50%' }} />
          <span className="font-bold">Medium (40-59)</span>
        </div>
        <div className="flex items-center gap-2">
          <div style={{ width: '12px', height: '12px', background: '#22c55e', borderRadius: '50%' }} />
          <span className="font-bold">Low (&lt;40)</span>
        </div>
      </div>

      {/* Route Stats */}
      <div className="mt-4 pt-3 border-t border-[#D0D7DE] grid grid-cols-4 gap-3 text-[8px]">
        <div>
          <div className="text-[#5C5C5C] font-bold">CORRIDORS</div>
          <div className="text-[10px] font-bold text-[#0B1F33]">{routes.length}</div>
        </div>
        <div>
          <div className="text-[#5C5C5C] font-bold">TOTAL SHIPMENTS</div>
          <div className="text-[10px] font-bold text-[#0B1F33]">
            {routes.reduce((sum, r) => sum + r.shipment_count, 0)}
          </div>
        </div>
        <div>
          <div className="text-[#5C5C5C] font-bold">AVG RISK</div>
          <div className="text-[10px] font-bold text-[#0B1F33]">
            {Math.round(
              routes.reduce((sum, r) => sum + r.avg_risk_score, 0) / routes.length
            )}%
          </div>
        </div>
        <div>
          <div className="text-[#5C5C5C] font-bold">TOTAL ANOMALIES</div>
          <div className="text-[10px] font-bold text-[#D83933]">
            {routes.reduce((sum, r) => sum + r.anomaly_count, 0)}
          </div>
        </div>
      </div>
    </div>
  );
}
