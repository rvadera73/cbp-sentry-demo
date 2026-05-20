import React, { useEffect, useRef } from 'react'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import type { ShipmentRoute } from '../../types/sentry'

interface ShipmentsMapProps {
  routes: ShipmentRoute[]
}

const ShipmentsMap: React.FC<ShipmentsMapProps> = ({ routes }) => {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstance = useRef<L.Map | null>(null)

  useEffect(() => {
    if (!mapRef.current || !routes.length) return

    if (!mapInstance.current) {
      mapInstance.current = L.map(mapRef.current).setView([20, 0], 3)

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(mapInstance.current)
    }

    const getRiskColor = (score: number): string => {
      if (score >= 80) return '#ef4444'
      if (score >= 50) return '#eab308'
      return '#22c55e'
    }

    let minLat = 90,
      maxLat = -90,
      minLon = 180,
      maxLon = -180

    routes.forEach((route) => {
      const riskColor = getRiskColor(route.riskScore)

      minLat = Math.min(minLat, route.from.lat, route.to.lat)
      maxLat = Math.max(maxLat, route.from.lat, route.to.lat)
      minLon = Math.min(minLon, route.from.lon, route.to.lon)
      maxLon = Math.max(maxLon, route.from.lon, route.to.lon)

      L.polyline([[route.from.lat, route.from.lon], [route.to.lat, route.to.lon]], {
        color: riskColor,
        weight: 3,
        opacity: 0.7,
        dashArray: route.riskScore >= 80 ? '5, 5' : undefined,
      }).addTo(mapInstance.current!)

      L.circleMarker([route.from.lat, route.from.lon], {
        radius: route.riskScore >= 80 ? 10 : 8,
        fillColor: riskColor,
        color: route.riskScore >= 80 ? '#991b1b' : riskColor,
        weight: route.riskScore >= 80 ? 3 : 2,
        opacity: 1,
        fillOpacity: 0.8,
      })
        .bindPopup(
          `<div class="text-sm"><p class="font-bold mb-2">${route.shipperName}</p><p class="text-xs mb-2">Manifest: ${route.manifestId}</p><p class="font-bold">Risk: ${route.riskScore}/100</p></div>`
        )
        .bindTooltip(route.shipperName)
        .addTo(mapInstance.current!)

      L.circleMarker([route.to.lat, route.to.lon], {
        radius: route.riskScore >= 80 ? 10 : 8,
        fillColor: riskColor,
        color: route.riskScore >= 80 ? '#991b1b' : riskColor,
        weight: route.riskScore >= 80 ? 3 : 2,
        opacity: 1,
        fillOpacity: 0.8,
      })
        .bindPopup(`<div class="text-sm"><p class="font-bold">${route.consigneeName}</p><p class="font-bold">Risk: ${route.riskScore}/100</p></div>`)
        .bindTooltip(route.consigneeName)
        .addTo(mapInstance.current!)
    })

    const bounds = L.latLngBounds([
      [minLat - 10, minLon - 10],
      [maxLat + 10, maxLon + 10],
    ])
    mapInstance.current.fitBounds(bounds)
  }, [routes])

  return <div ref={mapRef} style={{ height: '600px', width: '100%', borderRadius: '0.5rem' }} className="border border-gray-300" />
}

export default ShipmentsMap
