import { useMemo } from 'react';
import { Shipment } from '../types/v2.types';

// CBP Corridor Definitions - Trade analyst perspective
const CBP_CORRIDORS = {
  'CN→US': {
    route: 'China to United States',
    risk_profile: 'ORIGIN_CONCEALMENT',
    baseline_risk: 45,
    key_commodities: ['Electronics', 'Semiconductors', 'Machinery', 'Chemicals'],
    applicable_duties: [
      { duty_type: 'Section 301 Tariffs', rate: 25, description: 'Additional tariffs on Chinese goods' },
      { duty_type: 'Export Control (EAR)', rate: 0, description: 'Semiconductor manufacturing equipment' },
      { duty_type: 'UFLPA Enforcement', rate: 0, description: 'Xinjiang forced labor concerns' },
    ],
    red_flags: ['Element 9 mismatch', 'New intermediary shipper', 'Unusual routing', 'AIS spoofing'],
  },
  'VN→US': {
    route: 'Vietnam to United States',
    risk_profile: 'TARIFF_EVASION',
    baseline_risk: 35,
    key_commodities: ['Aluminum Extrusions', 'Steel Products', 'Textiles', 'Furniture'],
    applicable_duties: [
      { duty_type: 'Section 301 Tariffs', rate: 20, description: 'Vietnam origin verification' },
      { duty_type: 'AD/CVD on Aluminum', rate: 150, description: 'Antidumping/countervailing duties' },
    ],
    red_flags: ['Origin concealment', 'Rapid business growth', 'Low pricing vs benchmark'],
  },
  'MY→US': {
    route: 'Malaysia to United States',
    risk_profile: 'FORCED_LABOR',
    baseline_risk: 32,
    key_commodities: ['Solar Equipment', 'Semiconductors', 'Palm Oil Products'],
    applicable_duties: [
      { duty_type: 'UFLPA', rate: 0, description: 'Forced labor enforcement' },
      { duty_type: 'Anti-Dumping', rate: 40, description: 'Solar panel duties' },
    ],
    red_flags: ['UFLPA supply chain concerns', 'Unverified end-use', 'Labor complaints'],
  },
  'CA→US': {
    route: 'Canada to United States',
    risk_profile: 'EXPORT_CONTROL',
    baseline_risk: 20,
    key_commodities: ['Semiconductors', 'Machinery', 'Minerals'],
    applicable_duties: [
      { duty_type: 'USMCA Rules', rate: 0, description: 'Preferential trade agreement' },
    ],
    red_flags: ['Semiconductor export controls', 'Transshipment via Canada', 'Hidden Chinese ownership'],
  },
};

// US Port of Entry Database
const US_PORTS_OF_ENTRY = {
  'USNYC': { name: 'Port of New York/New Jersey', state: 'NY/NJ', typical_dwell: 3 },
  'USLA': { name: 'Port of Los Angeles', state: 'CA', typical_dwell: 4 },
  'USLB': { name: 'Port of Long Beach', state: 'CA', typical_dwell: 4 },
  'USHOU': { name: 'Port of Houston', state: 'TX', typical_dwell: 2 },
  'USCHI': { name: 'Port of Chicago', state: 'IL', typical_dwell: 2 },
  'USMIA': { name: 'Port of Miami', state: 'FL', typical_dwell: 2 },
  'USSAN': { name: 'Port of San Diego', state: 'CA', typical_dwell: 3 },
  'USSEA': { name: 'Port of Seattle', state: 'WA', typical_dwell: 3 },
};

interface ShippingIntelligenceEnrichment {
  corridor: typeof CBP_CORRIDORS[keyof typeof CBP_CORRIDORS] | null;
  port_of_entry: typeof US_PORTS_OF_ENTRY[keyof typeof US_PORTS_OF_ENTRY] | null;
  isf_discrepancies: number;
  unit_price_per_kg: number;
  benchmark_price_per_kg: number;
  price_variance_percent: number;
  pricing_flag: 'SEVERE' | 'HIGH' | 'NORMAL' | 'PREMIUM';
}

/**
 * Pure function: compute shipping intelligence from shipment data
 * This is called both from the hook and directly in list rendering
 */
function computeShippingIntelligence(shipment: Shipment | null): ShippingIntelligenceEnrichment | null {
  if (!shipment) return null;

  // 1. Identify CBP Corridor
  const originCountry = shipment.origin_country?.slice(0, 2).toUpperCase() || 'XX';
  const destCountry = shipment.destination_country?.slice(0, 2).toUpperCase() || 'XX';
  const corridorKey = `${originCountry}→${destCountry}`;
  const corridor = CBP_CORRIDORS[corridorKey as keyof typeof CBP_CORRIDORS] || null;

  // 2. Assign Port of Entry (default to Newark for East Coast, LA for West Coast, Houston for Gulf)
  const portMap: Record<string, keyof typeof US_PORTS_OF_ENTRY> = {
    'NY': 'USNYC', 'NJ': 'USNYC',
    'CA': 'USLA', 'WA': 'USSEA',
    'TX': 'USHOU', 'FL': 'USMIA',
  };
  const consigneeState = 'NJ'; // Default - in real system would come from consignee address
  const portCode = portMap[consigneeState] || 'USNYC';
  const port_of_entry = US_PORTS_OF_ENTRY[portCode];

  // 3. ISF Discrepancies (based on element9 mismatch, signal presence)
  const isf_discrepancies = [
    shipment.element9_is_mismatch ? 1 : 0,
    (shipment.h2_signals || []).includes('ISF_MISMATCH') ? 1 : 0,
  ].reduce((a, b) => a + b, 0);

  // 4. Pricing Analysis
  const declared_value = shipment.manifest_data?.declared_value_usd ||
                        (shipment as any).declared_value || 0;
  const declared_weight = shipment.manifest_data?.weight_kg ||
                         (shipment as any).declared_weight_kg || 1;
  const unit_price_per_kg = declared_weight > 0 ? declared_value / declared_weight : 0;

  // Benchmark prices per kg (industry standard)
  const benchmarks: Record<string, number> = {
    '8541': 45.00, // Semiconductors - $45/kg
    '7604': 8.50,  // Aluminum extrusions - $8.50/kg
    '7210': 1.20,  // Steel - $1.20/kg
    '7308': 2.00,  // Steel structures - $2.00/kg
    '2933': 85.00, // Pharma - $85/kg
  };

  const hs_prefix = (shipment.product_code || shipment.hs_code || '9999').slice(0, 4);
  const benchmark_price_per_kg = benchmarks[hs_prefix] || 25.00;
  const price_variance_percent = ((unit_price_per_kg - benchmark_price_per_kg) / benchmark_price_per_kg) * 100;

  // Flag pricing anomalies
  let pricing_flag: 'SEVERE' | 'HIGH' | 'NORMAL' | 'PREMIUM' = 'NORMAL';
  if (price_variance_percent < -50) pricing_flag = 'SEVERE'; // >50% underpriced
  else if (price_variance_percent < -20) pricing_flag = 'HIGH'; // 20-50% underpriced
  else if (price_variance_percent > 50) pricing_flag = 'PREMIUM'; // >50% overpriced (unusual)

  return {
    corridor,
    port_of_entry,
    isf_discrepancies,
    unit_price_per_kg,
    benchmark_price_per_kg,
    price_variance_percent,
    pricing_flag,
  };
}

/**
 * Enriches shipment data with trade analyst intelligence via memoized hook
 * Adds corridor risk profiles, ISF discrepancies, pricing analysis
 */
export function useShippingIntelligence(shipment: Shipment | null): ShippingIntelligenceEnrichment | null {
  return useMemo(() => computeShippingIntelligence(shipment), [shipment]);
}

// Export corridor database for corridor overview
export { CBP_CORRIDORS, US_PORTS_OF_ENTRY, computeShippingIntelligence };
export type ShippingIntelligence = ShippingIntelligenceEnrichment;
