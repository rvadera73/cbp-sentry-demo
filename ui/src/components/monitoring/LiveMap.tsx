import React, { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface Shipment {
  id: string
  shipper_name: string
  consignee_name: string
  shipper_lat: number
  shipper_lon: number
  consignee_lat: number
  consignee_lon: number
  risk_score: number
  h1_risk_level: string
  status: string
}

interface LiveMapProps {
  shipments: Shipment[]
  selectedShipment: Shipment | null
  onSelectShipment: (shipment: Shipment) => void
}

const LiveMap: React.FC<LiveMapProps> = ({ shipments, selectedShipment, onSelectShipment }) => {
  const mapRef = useRef<L.Map | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const markersRef = useRef<Map<string, L.Layer>>(new Map())

  // Custom icon styles based on risk level
  const getRiskColor = (riskScore: number): string => {
    if (riskScore >= 70) return '#ef4444' // red
    if (riskScore >= 50) return '#eab308' // yellow
    return '#22c55e' // green
  }

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    mapRef.current = L.map(containerRef.current, {
      center: [20, 0],
      zoom: 3,
      zoomControl: false,
    })

    // Dark tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(mapRef.current)

    // Add zoom control to bottom right
    L.control.zoom({ position: 'bottomright' }).addTo(mapRef.current)

    return () => {
      // Don't destroy map on unmount for smooth updates
    }
  }, [])

  // Update shipment markers
  useEffect(() => {
    if (!mapRef.current) return

    // Clear old markers
    markersRef.current.forEach((marker) => {
      mapRef.current?.removeLayer(marker)
    })
    markersRef.current.clear()

    // Add new markers for each shipment
    shipments.forEach((shipment) => {
      const color = getRiskColor(shipment.risk_score)
      const isSelected = selectedShipment?.id === shipment.id

      // Origin marker (shipper)
      const originMarker = L.circleMarker([shipment.shipper_lat, shipment.shipper_lon], {
        radius: isSelected ? 10 : 7,
        fillColor: color,
        color: isSelected ? '#fff' : color,
        weight: isSelected ? 3 : 1,
        opacity: isSelected ? 1 : 0.8,
        fillOpacity: isSelected ? 1 : 0.7,
        className: `shipment-marker origin ${isSelected ? 'selected' : ''} ${shipment.id}`,
      })

      originMarker.bindPopup(`
        <div class="text-sm font-semibold text-gray-900">
          <p class="font-black">${shipment.shipper_name}</p>
          <p class="text-xs text-gray-600">${shipment.shipper_lat.toFixed(2)}, ${shipment.shipper_lon.toFixed(2)}</p>
          <p class="text-xs mt-1">Risk: <span class="font-black text-red-600">${shipment.risk_score}/100</span></p>
        </div>
      `)

      originMarker.on('click', () => {
        onSelectShipment(shipment)
      })

      originMarker.addTo(mapRef.current!)
      markersRef.current.set(`${shipment.id}-origin`, originMarker)

      // Destination marker (consignee)
      const destMarker = L.circleMarker([shipment.consignee_lat, shipment.consignee_lon], {
        radius: isSelected ? 10 : 7,
        fillColor: color,
        color: isSelected ? '#fff' : color,
        weight: isSelected ? 3 : 1,
        opacity: isSelected ? 1 : 0.8,
        fillOpacity: isSelected ? 1 : 0.5,
        className: `shipment-marker destination ${isSelected ? 'selected' : ''} ${shipment.id}`,
      })

      destMarker.bindPopup(`
        <div class="text-sm font-semibold text-gray-900">
          <p class="font-black">${shipment.consignee_name}</p>
          <p class="text-xs text-gray-600">${shipment.consignee_lat.toFixed(2)}, ${shipment.consignee_lon.toFixed(2)}</p>
          <p class="text-xs mt-1">Status: ${shipment.status}</p>
        </div>
      `)

      destMarker.on('click', () => {
        onSelectShipment(shipment)
      })

      destMarker.addTo(mapRef.current!)
      markersRef.current.set(`${shipment.id}-dest`, destMarker)

      // Draw route line
      const routeLine = L.polyline(
        [
          [shipment.shipper_lat, shipment.shipper_lon],
          [shipment.consignee_lat, shipment.consignee_lon],
        ],
        {
          color: color,
          weight: isSelected ? 3 : 1,
          opacity: isSelected ? 0.8 : 0.4,
          dashArray: isSelected ? undefined : '5, 5',
          className: `route-line ${isSelected ? 'selected' : ''} ${shipment.id}`,
        }
      )

      routeLine.addTo(mapRef.current!)
      markersRef.current.set(`${shipment.id}-line`, routeLine)
    })
  }, [shipments, selectedShipment])

  return (
    <div ref={containerRef} className="w-full h-full relative">
      <style>{`
        .leaflet-popup-content {
          padding: 12px !important;
          margin: 0 !important;
        }
        .leaflet-popup-close-button {
          display: none;
        }
        .shipment-marker.origin {
          filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.3));
        }
        .shipment-marker.selected {
          filter: drop-shadow(0 0 12px rgba(255, 255, 255, 0.6));
          animation: pulse 2s infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
      `}</style>
    </div>
  )
}

export default LiveMap
