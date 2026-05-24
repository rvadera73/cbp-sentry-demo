import React, { useState } from 'react';
import { MapPin, Ship, FileText, DollarSign, AlertTriangle, TrendingDown, Calendar, CheckCircle } from 'lucide-react';
import { useV2Cases } from '../hooks/useV2Cases';
import { useShippingIntelligence, computeShippingIntelligence, CBP_CORRIDORS, US_PORTS_OF_ENTRY } from '../hooks/useShippingIntelligence';

export default function V2ShippingIntelligencePage() {
  const { shipments } = useV2Cases();
  const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(null);
  const [corridorFilter, setCorridorFilter] = useState<string>('ALL');

  const selectedShipment = shipments.find(s => s.shipment_id === selectedShipmentId) || shipments[0];
  const intelligence = useShippingIntelligence(selectedShipment);

  // Filter shipments by corridor
  const filteredShipments = corridorFilter === 'ALL'
    ? shipments
    : shipments.filter(s => `${s.origin_country?.slice(0,2).toUpperCase() || 'XX'}→${s.destination_country?.slice(0,2).toUpperCase() || 'XX'}` === corridorFilter);

  return (
    <div className="flex-1 flex flex-col h-full bg-[#F7F9FC] overflow-hidden">
      {/* Header */}
      <div className="h-16 bg-white border-b border-[#D0D7DE] px-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-[#112E51]">Shipping Intelligence</h1>
          <p className="text-xs text-slate-500 font-mono">Trade Analyst View • Corridors • ISF • Vessel Tracking • Pricing Analysis</p>
        </div>
        <div className="flex items-center space-x-3 text-xs font-mono text-slate-600">
          <span>{filteredShipments.length} shipments</span>
          <span className="px-2 py-1 bg-slate-100 rounded">CBP Tracked Corridors</span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: Corridor & Shipment List */}
        <div className="w-80 border-r border-[#D0D7DE] flex flex-col bg-white overflow-hidden">
          {/* Corridor Selector */}
          <div className="p-3 border-b border-[#D0D7DE] bg-[#F7F9FC]">
            <label className="text-xs font-bold text-slate-600 uppercase block mb-2">CBP Corridors</label>
            <select
              value={corridorFilter}
              onChange={(e) => {
                setCorridorFilter(e.target.value);
                setSelectedShipmentId(null);
              }}
              className="w-full bg-white border border-[#D0D7DE] rounded px-2 py-1.5 text-xs font-mono focus:outline-none focus:border-[#005EA2]"
            >
              <option value="ALL">All Corridors</option>
              {Object.entries(CBP_CORRIDORS).map(([key, corridor]) => (
                <option key={key} value={key}>
                  {key} - {corridor.risk_profile}
                </option>
              ))}
            </select>
          </div>

          {/* Shipment List */}
          <div className="flex-1 overflow-y-auto">
            {filteredShipments.map((shipment) => {
              const intel = computeShippingIntelligence(shipment);
              const originCountry = shipment.origin_country?.slice(0, 2).toUpperCase() || 'XX';
              const destCountry = shipment.destination_country?.slice(0, 2).toUpperCase() || 'XX';
              return (
                <button
                  key={shipment.shipment_id}
                  onClick={() => setSelectedShipmentId(shipment.shipment_id)}
                  className={`w-full text-left p-3 border-b border-[#E5E7EB] hover:bg-blue-50 transition-colors ${
                    selectedShipmentId === shipment.shipment_id ? 'bg-[#E8F4FD] border-l-4 border-l-[#005EA2]' : ''
                  }`}
                >
                  <div className="text-xs font-bold text-[#112E51]">{shipment.shipper_name}</div>
                  <div className="text-[11px] text-slate-600 font-mono mt-0.5">
                    {originCountry}→{destCountry} | {shipment.commodity_name}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1 flex items-center space-x-2">
                    <span className={`px-1.5 py-0.5 rounded text-white ${
                      shipment.risk_score! >= 80 ? 'bg-[#D83933]' :
                      shipment.risk_score! >= 60 ? 'bg-[#FFBE2E] text-slate-950' : 'bg-slate-400'
                    }`}>
                      Risk: {Math.round(shipment.risk_score || 0)}
                    </span>
                    {intel?.pricing_flag !== 'NORMAL' && (
                      <span className="px-1.5 py-0.5 bg-orange-100 text-orange-800 rounded">
                        Pricing: {intel?.pricing_flag}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Panel: Detailed Intelligence */}
        {selectedShipment && intelligence && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* 1. CORRIDOR ANALYSIS */}
            <section className="bg-white rounded-sm border border-[#D0D7DE] p-4">
              <h2 className="text-sm font-bold text-[#112E51] mb-3 flex items-center space-x-2">
                <MapPin className="w-4 h-4" />
                <span>CBP Trade Corridor</span>
              </h2>
              {intelligence.corridor ? (
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-600">Route:</span>
                    <span className="font-mono font-bold">{intelligence.corridor.route}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600">Risk Profile:</span>
                    <span className={`font-bold ${
                      intelligence.corridor.risk_profile === 'TARIFF_EVASION' ? 'text-orange-600' :
                      intelligence.corridor.risk_profile === 'ORIGIN_CONCEALMENT' ? 'text-red-600' :
                      'text-amber-600'
                    }`}>{intelligence.corridor.risk_profile}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600">Baseline Risk:</span>
                    <span className="font-mono">{intelligence.corridor.baseline_risk}/100</span>
                  </div>
                  <div className="pt-2 border-t border-[#E5E7EB]">
                    <div className="text-slate-600 mb-1">Applicable Duties:</div>
                    <div className="space-y-1">
                      {intelligence.corridor.applicable_duties.map((duty, i) => (
                        <div key={i} className="text-[10px] bg-slate-50 p-1.5 rounded">
                          <div className="font-bold">{duty.duty_type}</div>
                          <div className="text-slate-600">{duty.rate > 0 ? `${duty.rate}%` : 'Variable'} - {duty.description}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-slate-500 italic">Corridor not in primary tracking database</div>
              )}
            </section>

            {/* 2. ISF FILING STATUS */}
            <section className="bg-white rounded-sm border border-[#D0D7DE] p-4">
              <h2 className="text-sm font-bold text-[#112E51] mb-3 flex items-center space-x-2">
                <FileText className="w-4 h-4" />
                <span>ISF Filing Data</span>
              </h2>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-600">Filing Status:</span>
                  <span className={`font-bold px-2 py-0.5 rounded ${
                    intelligence.isf_discrepancies > 0
                      ? 'bg-red-100 text-red-700'
                      : 'bg-emerald-100 text-emerald-700'
                  }`}>
                    {intelligence.isf_discrepancies > 0 ? 'DISCREPANCIES FOUND' : 'COMPLIANT'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Element 9 Status:</span>
                  <span className={selectedShipment.element9_is_mismatch ? 'text-red-600 font-bold' : 'text-emerald-600'}>
                    {selectedShipment.element9_is_mismatch ? 'MISMATCH' : 'Declared: ' + selectedShipment.element9_declared_country}
                  </span>
                </div>
                {intelligence.isf_discrepancies > 0 && (
                  <div className="bg-red-50 p-2 rounded border border-red-200 mt-2">
                    <div className="font-bold text-red-700 mb-1">Discrepancies Detected:</div>
                    <ul className="text-[10px] text-red-600 space-y-1">
                      {selectedShipment.element9_is_mismatch && (
                        <li>• Element 9: Declared {selectedShipment.element9_declared_country} vs Actual {selectedShipment.element9_actual_country}</li>
                      )}
                      {(selectedShipment.h2_signals || []).includes('ISF_MISMATCH') && (
                        <li>• ISF Mismatch detected in pre-filing review</li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
            </section>

            {/* 3. VESSEL TRACKING */}
            <section className="bg-white rounded-sm border border-[#D0D7DE] p-4">
              <h2 className="text-sm font-bold text-[#112E51] mb-3 flex items-center space-x-2">
                <Ship className="w-4 h-4" />
                <span>Vessel Tracking & ETA</span>
              </h2>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-600">Vessel:</span>
                  <span className="font-mono">{selectedShipment.vessel_name || 'Unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">IMO:</span>
                  <span className="font-mono">{selectedShipment.vessel_imo || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Route:</span>
                  <span className="font-mono">{(selectedShipment.port_calls || []).join(' → ')}</span>
                </div>
                {(selectedShipment.h2_signals || []).includes('DWELL_ANOMALY') && (
                  <div className="bg-yellow-50 p-2 rounded border border-yellow-200 mt-2 text-yellow-700 font-bold text-[10px]">
                    ⚠️ AIS Dwell Anomaly Detected - Vessel position inconsistent with schedule
                  </div>
                )}
              </div>
            </section>

            {/* 4. PORT OF ENTRY */}
            <section className="bg-white rounded-sm border border-[#D0D7DE] p-4">
              <h2 className="text-sm font-bold text-[#112E51] mb-3 flex items-center space-x-2">
                <Calendar className="w-4 h-4" />
                <span>Port of Entry</span>
              </h2>
              {intelligence.port_of_entry ? (
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-600">Port:</span>
                    <span className="font-bold">{intelligence.port_of_entry.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600">Code:</span>
                    <span className="font-mono">US{intelligence.port_of_entry.name.split(' ').pop()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600">Expected Dwell:</span>
                    <span className="font-mono">{intelligence.port_of_entry.typical_dwell} days</span>
                  </div>
                </div>
              ) : (
                <div className="text-slate-500 italic">Port information unavailable</div>
              )}
            </section>

            {/* 5. PRICING ANALYSIS */}
            <section className="bg-white rounded-sm border border-[#D0D7DE] p-4">
              <h2 className="text-sm font-bold text-[#112E51] mb-3 flex items-center space-x-2">
                <DollarSign className="w-4 h-4" />
                <span>Pricing Analysis vs Benchmark</span>
              </h2>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-600">Declared Value:</span>
                  <span className="font-mono">${intelligence.unit_price_per_kg.toFixed(2)}/kg</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Benchmark Price:</span>
                  <span className="font-mono">${intelligence.benchmark_price_per_kg.toFixed(2)}/kg</span>
                </div>
                <div className={`flex justify-between font-bold p-2 rounded mt-2 ${
                  intelligence.pricing_flag === 'SEVERE' ? 'bg-red-50 text-red-700' :
                  intelligence.pricing_flag === 'HIGH' ? 'bg-orange-50 text-orange-700' :
                  intelligence.pricing_flag === 'PREMIUM' ? 'bg-blue-50 text-blue-700' :
                  'bg-emerald-50 text-emerald-700'
                }`}>
                  <span>Variance:</span>
                  <span>{intelligence.price_variance_percent > 0 ? '+' : ''}{intelligence.price_variance_percent.toFixed(1)}%</span>
                </div>
                {intelligence.pricing_flag !== 'NORMAL' && (
                  <div className={`text-[10px] p-2 rounded mt-2 ${
                    intelligence.pricing_flag === 'SEVERE' ? 'bg-red-100 text-red-700' :
                    intelligence.pricing_flag === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {intelligence.pricing_flag === 'SEVERE' && '🚨 Severe underpricing detected - Potential tariff evasion indicator'}
                    {intelligence.pricing_flag === 'HIGH' && '⚠️ High underpricing - Verify declared value legitimacy'}
                    {intelligence.pricing_flag === 'PREMIUM' && 'ℹ️ Premium pricing - Unusually high value per unit'}
                  </div>
                )}
              </div>
            </section>

            {/* 6. TRADE FLOW TIMELINE */}
            <section className="bg-white rounded-sm border border-[#D0D7DE] p-4">
              <h2 className="text-sm font-bold text-[#112E51] mb-3 flex items-center space-x-2">
                <TrendingDown className="w-4 h-4" />
                <span>Trade Flow Timeline</span>
              </h2>
              <div className="space-y-2 text-xs">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  <span>Manifest Filed: {selectedShipment.date}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Ship className="w-4 h-4 text-slate-400" />
                  <span>In Transit to {intelligence.port_of_entry?.name || 'Unknown Port'}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  <span>{intelligence.isf_discrepancies > 0 ? 'ISF Discrepancies Require Review' : 'ISF Compliant'}</span>
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
