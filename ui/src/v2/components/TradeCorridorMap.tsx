import React, { useEffect, useRef } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { Map as MapIcon } from 'lucide-react';
import { Panel, SectionHeader, StatStrip } from '../../components/ui';

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

const COUNTRY_COORDINATES: Record<string, [number, number]> = {
  'Vietnam': [14.0583, 108.2772], 'Hong Kong': [22.3193, 114.1694], 'Singapore': [1.3521, 103.8198],
  'USA': [37.0902, -95.7129], 'China': [35.8617, 104.1954], 'Japan': [36.2048, 138.2529],
  'Malaysia': [4.2105, 101.6964], 'Thailand': [15.8700, 100.9925], 'Indonesia': [-0.7893, 113.9213],
  'Philippines': [12.8797, 121.7740], 'South Korea': [35.9078, 127.7669], 'Taiwan': [23.6978, 120.9605],
  'India': [20.5937, 78.9629], 'Mexico': [23.6345, -102.5528], 'Canada': [56.1304, -106.3468], 'Cambodia': [12.5657, 104.9910],
};

// Map common name variants to our coordinate keys so routes always resolve.
const ALIASES: Record<string, string> = {
  'united states': 'USA', 'united states of america': 'USA', 'us': 'USA', 'u.s.': 'USA', 'u.s.a.': 'USA', 'america': 'USA',
  'viet nam': 'Vietnam', 'vn': 'Vietnam', 'hk': 'Hong Kong', 'prc': 'China', "people's republic of china": 'China', 'cn': 'China',
  'korea': 'South Korea', 'republic of korea': 'South Korea', 'kr': 'South Korea', 'my': 'Malaysia', 'th': 'Thailand',
  'id': 'Indonesia', 'sg': 'Singapore', 'jp': 'Japan', 'tw': 'Taiwan', 'in': 'India', 'kh': 'Cambodia',
};

function resolveCountry(name: string): [string, [number, number]] | null {
  const raw = (name || '').trim();
  if (!raw) return null;
  if (COUNTRY_COORDINATES[raw]) return [raw, COUNTRY_COORDINATES[raw]];
  const key = raw.toLowerCase();
  const aliased = ALIASES[key];
  if (aliased && COUNTRY_COORDINATES[aliased]) return [aliased, COUNTRY_COORDINATES[aliased]];
  const ci = Object.keys(COUNTRY_COORDINATES).find(n => n.toLowerCase() === key);
  return ci ? [ci, COUNTRY_COORDINATES[ci]] : null;
}

// Kit-aligned risk palette.
function riskColor(score: number): string {
  if (score >= 80) return '#D83933';
  if (score >= 60) return '#C7791B';
  if (score >= 40) return '#B8860B';
  return '#15803D';
}

const FIXTURE_ROUTES: TradeRoute[] = [
  { origin_country: 'Vietnam', destination_country: 'USA', shipment_count: 12, avg_risk_score: 68, avg_dwell_days: 8, anomaly_count: 3 },
  { origin_country: 'Hong Kong', destination_country: 'USA', shipment_count: 8, avg_risk_score: 72, avg_dwell_days: 6, anomaly_count: 2 },
  { origin_country: 'China', destination_country: 'USA', shipment_count: 24, avg_risk_score: 62, avg_dwell_days: 7, anomaly_count: 4 },
];

export default function TradeCorridorMap({ routes, height = 360 }: TradeCorridorMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  // Resolve usable routes (both endpoints geocodable); fall back to fixtures.
  const incoming = routes && routes.length ? routes : FIXTURE_ROUTES;
  const usable = incoming
    .map(r => ({ r, o: resolveCountry(r.origin_country), d: resolveCountry(r.destination_country) }))
    .filter(x => x.o && x.d) as { r: TradeRoute; o: [string, [number, number]]; d: [string, [number, number]] }[];
  const drawRoutes = usable.length ? usable : FIXTURE_ROUTES
    .map(r => ({ r, o: resolveCountry(r.origin_country)!, d: resolveCountry(r.destination_country)! }));

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const map = L.map(mapContainer.current, { zoomControl: true, attributionControl: false }).setView([20, 110], 3);
    mapRef.current = map;

    // Light basemap to match the app theme.
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd', maxZoom: 18, minZoom: 2,
    }).addTo(map);

    const bounds: L.LatLngExpression[] = [];
    const seen = new Set<string>();

    drawRoutes.forEach(({ r, o, d }) => {
      const color = riskColor(r.avg_risk_score);
      // Route line
      L.polyline([o[1], d[1]], {
        color, weight: Math.max(2, Math.min(6, r.shipment_count / 4)),
        opacity: 0.85, dashArray: r.avg_risk_score >= 60 ? '6,6' : undefined,
      }).addTo(map).bindPopup(
        `<b>${o[0]} → ${d[0]}</b><br/>Shipments: ${r.shipment_count}<br/>Avg risk: ${Math.round(r.avg_risk_score)}%<br/>Avg dwell: ${r.avg_dwell_days}d<br/>Anomalies: ${r.anomaly_count}`
      );
      // Endpoint markers + permanent labels
      ([[o, 'Origin'], [d, 'Destination']] as const).forEach(([pt, role]) => {
        bounds.push(pt[1]);
        if (seen.has(pt[0])) return;
        seen.add(pt[0]);
        L.circleMarker(pt[1], { radius: 7, fillColor: role === 'Origin' ? color : '#005EA2', color: '#fff', weight: 2, fillOpacity: 0.9 })
          .addTo(map)
          .bindTooltip(`${pt[0]}`, { permanent: true, direction: 'top', className: 'corridor-label', offset: [0, -6] });
      });
    });

    if (bounds.length) map.fitBounds(L.latLngBounds(bounds).pad(0.35), { maxZoom: 5 });

    return () => { map.remove(); mapRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(routes)]);

  const totalShipments = drawRoutes.reduce((s, x) => s + x.r.shipment_count, 0);
  const avgRisk = drawRoutes.length ? Math.round(drawRoutes.reduce((s, x) => s + x.r.avg_risk_score, 0) / drawRoutes.length) : 0;
  const totalAnomalies = drawRoutes.reduce((s, x) => s + x.r.anomaly_count, 0);

  return (
    <Panel>
      <SectionHeader title="Trade Corridor Map" subtitle="Origin → destination routing, weighted by risk & volume" icon={<MapIcon className="w-4 h-4" />} />
      <style>{`.corridor-label{background:#0B1F33;color:#fff;border:none;font-size:10px;font-weight:700;padding:1px 5px;border-radius:3px;box-shadow:none}.corridor-label:before{display:none}`}</style>
      <div ref={mapContainer} style={{ height, borderRadius: 4 }} className="border border-[#D0D7DE] overflow-hidden" />

      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-[10px]">
        {[['Critical ≥80', '#D83933'], ['High 60–79', '#C7791B'], ['Medium 40–59', '#B8860B'], ['Low <40', '#15803D']].map(([label, c]) => (
          <div key={label} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: c as string }} />
            <span className="font-semibold text-[#5C5C5C]">{label}</span>
          </div>
        ))}
      </div>

      <div className="mt-3">
        <StatStrip items={[
          { label: 'Corridors', value: drawRoutes.length },
          { label: 'Total Shipments', value: totalShipments },
          { label: 'Avg Risk', value: `${avgRisk}%`, color: riskColor(avgRisk) },
          { label: 'Total Anomalies', value: totalAnomalies, color: '#D83933' },
        ]} />
      </div>
    </Panel>
  );
}
