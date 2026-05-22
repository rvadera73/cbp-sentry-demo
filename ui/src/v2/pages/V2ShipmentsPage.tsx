import React, { useState } from 'react';
import { useV2Cases } from '../hooks/useV2Cases';

export default function V2ShipmentsPage() {
  const { shipments, loading } = useV2Cases();
  const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(null);

  if (loading) return <div className="p-6 text-center">Loading shipments...</div>;

  const selectedShipment = shipments.find(s => s.shipment_id === selectedShipmentId);

  return (
    <div className="flex-1 flex overflow-hidden bg-[#F7F9FC]">
      <div className="flex-1 p-5 overflow-y-auto">
        <h1 className="text-2xl font-bold text-[#0B1F33] mb-4">Shipment Intelligence</h1>
        <div className="space-y-3">
          {shipments.map(s => (
            <button
              key={s.shipment_id}
              onClick={() => setSelectedShipmentId(s.shipment_id)}
              className={`w-full p-4 rounded-sm border-2 text-left transition-all ${
                selectedShipmentId === s.shipment_id
                  ? 'bg-[#F0F4F8] border-[#005EA2]'
                  : 'bg-white border-[#D0D7DE] hover:border-[#005EA2]'
              }`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-bold text-[#0B1F33]">{s.container_id}</h3>
                  <p className="text-xs text-[#5C5C5C]">{s.declared_origin} → {s.destination_country}</p>
                  <p className="text-xs text-[#5C5C5C]">{s.product_description}</p>
                </div>
                <span className={`px-2 py-1 text-xs font-bold rounded ${
                  s.ai_anomaly_score >= 80 ? 'bg-[#D83933] text-white' : 'bg-amber-100'
                }`}>
                  {s.ai_anomaly_score}%
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {selectedShipment && (
        <div className="w-96 border-l border-[#D0D7DE] bg-white overflow-y-auto p-5">
          <h2 className="text-lg font-bold text-[#0B1F33] mb-4">Shipment Detail</h2>
          <div className="space-y-3 text-sm">
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Container ID</label>
              <p className="text-[#0B1F33] font-mono">{selectedShipment.container_id}</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Shipper</label>
              <p className="text-[#0B1F33]">{selectedShipment.manifest_data.shipper}</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Vessel</label>
              <p className="text-[#0B1F33]">{selectedShipment.manifest_data.vessel}</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Anomalies</label>
              <p className="text-[#5C5C5C]">{selectedShipment.manifest_anomalies.join(', ') || 'None'}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
