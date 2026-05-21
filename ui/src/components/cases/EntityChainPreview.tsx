/**
 * Entity Chain Preview Card
 *
 * Displays Senzing entity resolution (ownership chain) for a case.
 * Shows shipper → parent company → manufacturer hierarchy with confidence scores.
 */

import React from 'react';

interface Entity {
  entity_id: number;
  name: string;
  country: string;
  entity_type: string;
  role: string;
  confidence: number;
  prior_cbp_filings?: number;
  relationships?: Array<{
    type: string;
    target: string;
    confidence: number;
  }>;
}

interface Props {
  entities: Entity[];
  isLoading?: boolean;
  isDemo?: boolean;
}

export default function EntityChainPreview({ entities, isLoading = false, isDemo = false }: Props) {
  if (isLoading) {
    return (
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-700 animate-pulse">Loading entity chain...</p>
      </div>
    );
  }

  if (!entities || entities.length === 0) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-sm text-yellow-700">⚠ Entity resolution unavailable</p>
      </div>
    );
  }

  // Group entities by role
  const shipper = entities.find(e => e.entity_type === 'SHIPPER');
  const manufacturer = entities.find(e => e.entity_type === 'MANUFACTURER');
  const holding = entities.find(e => e.entity_type === 'HOLDING_COMPANY');
  const consignee = entities.find(e => e.entity_type === 'CONSIGNEE');
  const forwarder = entities.find(e => e.entity_type === 'FREIGHT_FORWARDER');

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.95) return 'bg-green-100 text-green-700';
    if (confidence >= 0.85) return 'bg-blue-100 text-blue-700';
    return 'bg-gray-100 text-gray-700';
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'SHIPPER':
        return '📦';
      case 'MANUFACTURER':
        return '🏭';
      case 'HOLDING_COMPANY':
        return '🏢';
      case 'CONSIGNEE':
        return '🏠';
      case 'FREIGHT_FORWARDER':
        return '✈️';
      default:
        return '🔗';
    }
  };

  return (
    <div className="p-4 bg-gradient-to-br from-gray-50 to-gray-100 border border-gray-200 rounded-lg space-y-3">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-bold text-gray-900">Entity Ownership Chain</h4>
        {isDemo && (
          <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded font-semibold">
            DEMO
          </span>
        )}
      </div>

      {/* Entity Chain Flow */}
      <div className="space-y-2">
        {/* Manufacturer → Holding */}
        {manufacturer && holding && (
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <EntityBadge
                icon={getEntityIcon(manufacturer.entity_type)}
                name={manufacturer.name}
                country={manufacturer.country}
                confidence={manufacturer.confidence}
              />
            </div>
            <div className="text-xs text-gray-500 font-semibold">OWNS</div>
            <div className="flex-1">
              <EntityBadge
                icon={getEntityIcon(holding.entity_type)}
                name={holding.name}
                country={holding.country}
                confidence={holding.confidence}
              />
            </div>
          </div>
        )}

        {/* Holding → Shipper */}
        {holding && shipper && (
          <div className="flex items-center gap-2">
            <div className="text-xs text-gray-500 font-semibold">↓ OWNS</div>
          </div>
        )}

        {/* Shipper → Consignee */}
        {shipper && (
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <EntityBadge
                icon={getEntityIcon(shipper.entity_type)}
                name={shipper.name}
                country={shipper.country}
                confidence={shipper.confidence}
                isBold
              />
            </div>
            <div className="text-xs text-gray-500 font-semibold">EXPORTS TO</div>
            <div className="flex-1">
              <EntityBadge
                icon={getEntityIcon(consignee?.entity_type || 'CONSIGNEE')}
                name={consignee?.name || 'Unknown'}
                country={consignee?.country || 'US'}
                confidence={consignee?.confidence || 0}
              />
            </div>
          </div>
        )}

        {/* Freight Forwarder */}
        {forwarder && (
          <div className="mt-2 pt-2 border-t border-gray-300">
            <p className="text-xs text-gray-600 mb-1">Via Freight Forwarder:</p>
            <EntityBadge
              icon={getEntityIcon(forwarder.entity_type)}
              name={forwarder.name}
              country={forwarder.country}
              confidence={forwarder.confidence}
            />
          </div>
        )}
      </div>

      {/* Risk Indicators from Chain */}
      <div className="pt-2 border-t border-gray-300 space-y-1">
        {manufacturer && shipper && manufacturer.country !== shipper.country && (
          <div className="flex items-start gap-2 p-2 bg-red-50 rounded text-xs">
            <span>⚠</span>
            <div>
              <p className="font-semibold text-red-700">Transshipment Ring Detected</p>
              <p className="text-red-600">
                Manufacturer ({manufacturer.country}) → Shipper ({shipper.country})
              </p>
            </div>
          </div>
        )}

        {consignee && consignee.prior_cbp_filings && consignee.prior_cbp_filings > 5 && (
          <div className="flex items-start gap-2 p-2 bg-amber-50 rounded text-xs">
            <span>⚠</span>
            <div>
              <p className="font-semibold text-amber-700">High-Risk Consignee</p>
              <p className="text-amber-600">{consignee.prior_cbp_filings} prior CBP filings</p>
            </div>
          </div>
        )}
      </div>

      {/* Call to Action */}
      <div className="pt-2 border-t border-gray-300">
        <p className="text-xs text-gray-600">
          👉 <span className="font-semibold">Click case to see full entity chain in referral package</span>
        </p>
      </div>
    </div>
  );
}

/**
 * Entity Badge - displays entity name, country, and confidence score
 */
function EntityBadge({
  icon,
  name,
  country,
  confidence,
  isBold = false
}: {
  icon: string;
  name: string;
  country: string;
  confidence: number;
  isBold?: boolean;
}) {
  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.95) return 'bg-green-100 text-green-700';
    if (conf >= 0.85) return 'bg-blue-100 text-blue-700';
    return 'bg-gray-100 text-gray-700';
  };

  return (
    <div className={`p-2 bg-white rounded border border-gray-300 ${isBold ? 'ring-2 ring-orange-300' : ''}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex-1">
          <p className={`text-xs flex items-center gap-1 ${isBold ? 'font-bold' : 'font-semibold'} text-gray-900`}>
            {icon} {name.length > 25 ? name.substring(0, 22) + '...' : name}
          </p>
          <p className="text-xs text-gray-600 font-mono">{country}</p>
        </div>
        <div className={`text-xs font-bold px-2 py-1 rounded ${getConfidenceColor(confidence)}`}>
          {(confidence * 100).toFixed(0)}%
        </div>
      </div>
    </div>
  );
}
