import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

interface EntityLocation {
  entity_id: string;
  entity_name: string;
  country: string;
  risk_score: number;
  entity_type: string;
}

interface EntityGeoMapProps {
  entities: EntityLocation[];
  height?: number;
  showRoutes?: boolean;
}

const COUNTRY_COORDINATES: Record<string, [number, number]> = {
  Vietnam: [16.8661, 107.5833],
  China: [35.8617, 104.1954],
  India: [20.5937, 78.9629],
  Thailand: [15.8700, 100.9925],
  Indonesia: [-0.7893, 113.9213],
  Malaysia: [4.2105, 101.6964],
  USA: [37.0902, -95.7129],
  Mexico: [23.6345, -102.5528],
  Canada: [56.1304, -106.3468],
  Philippines: [12.8797, 121.7740],
  'South Korea': [35.9078, 127.7669],
  Japan: [36.2048, 138.2529],
  Taiwan: [23.6978, 120.9605],
  Singapore: [1.3521, 103.8198],
  'Hong Kong': [22.3193, 114.1694],
};

function getRiskColor(riskScore: number): string {
  if (riskScore >= 70) return '#D83933';
  if (riskScore >= 50) return '#FF9500';
  return '#22c55e';
}

export default function EntityGeoMap({
  entities,
  height = 200,
  showRoutes = false,
}: EntityGeoMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.Layer>>(new Map());
  const polylineRef = useRef<L.Polyline | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    if (!mapRef.current) {
      mapRef.current = L.map(containerRef.current, {
        center: [30, 10],
        zoom: 2,
        scrollWheelZoom: true,
        zoomControl: false,
      });

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; CartoDB',
        maxZoom: 19,
      }).addTo(mapRef.current);
    }

    markersRef.current.forEach((marker) => mapRef.current?.removeLayer(marker));
    markersRef.current.clear();

    if (polylineRef.current && mapRef.current) {
      mapRef.current.removeLayer(polylineRef.current);
      polylineRef.current = null;
    }

    const coordinates: [number, number][] = [];
    entities.forEach((entity) => {
      const coord = COUNTRY_COORDINATES[entity.country as keyof typeof COUNTRY_COORDINATES];
      if (coord && mapRef.current) {
        coordinates.push(coord);
        const marker = L.circleMarker(coord, {
          radius: 7,
          fillColor: getRiskColor(entity.risk_score),
          color: '#fff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.8,
        })
          .bindTooltip(`${entity.entity_name} (${entity.entity_type})\nRisk: ${entity.risk_score}%`, {
            permanent: false,
            direction: 'top',
          })
          .addTo(mapRef.current);

        markersRef.current.set(entity.entity_id, marker);
      }
    });

    if (showRoutes && coordinates.length > 1 && mapRef.current) {
      polylineRef.current = L.polyline(coordinates, {
        color: '#888',
        weight: 1,
        opacity: 0.5,
        dashArray: '4, 4',
      }).addTo(mapRef.current);
    }

    return () => {
      markersRef.current.forEach((marker) => mapRef.current?.removeLayer(marker));
      if (polylineRef.current && mapRef.current) {
        mapRef.current.removeLayer(polylineRef.current);
      }
    };
  }, [entities, showRoutes]);

  return <div ref={containerRef} style={{ width: '100%', height: `${height}px` }} />;
}
