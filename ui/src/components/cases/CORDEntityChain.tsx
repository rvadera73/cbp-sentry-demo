/**
 * CORD Entity Chain Display — Shows 3-level ownership chain from CORD API
 *
 * Displays:
 * - Level 1: Direct shipper (from manifest)
 * - Level 2: Holding/parent company (OWNED_BY relationship)
 * - Level 3: Ultimate beneficial owner/manufacturer (OWNED_BY relationship)
 * - OFAC status for each level
 * - Risk scoring derived from entity locations
 */

import { useState, useEffect } from 'react';
import { ArrowRight, AlertCircle, CheckCircle, Building2 } from 'lucide-react';
import { api } from '../../services/api';

interface CORDEntityChainProps {
  shipper_name: string;
  shipper_country?: string;
  consignee_name?: string;
  consignee_country?: string;
}

interface EntityLevel {
  entity_id: string;
  name: string;
  country: string;
  data_source: string;
  confidence: number;
  entity_type: string;
}

interface ChainResolution {
  level_1?: EntityLevel;
  level_2?: EntityLevel;
  level_3?: EntityLevel;
  level_2_relationship?: { relationship_type: string; confidence: number };
  level_3_relationship?: { relationship_type: string; confidence: number };
}

export default function CORDEntityChain({
  shipper_name,
  shipper_country,
  consignee_name,
  consignee_country,
}: CORDEntityChainProps) {
  const [chain, setChain] = useState<ChainResolution | null>(null);
  const [ofac_detected, setOfacDetected] = useState(false);
  const [risk_score, setRiskScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchChain = async () => {
      try {
        setLoading(true);
        const result = await api.cordResolveChain(
          shipper_name,
          shipper_country,
          consignee_name,
          consignee_country
        );

        if (result.status === 'success' && result.resolution) {
          setChain(result.resolution.chain);
          setOfacDetected(result.resolution.ofac?.detected || false);
          setRiskScore(result.resolution.scoring?.risk_score || null);
          setError(null);
        } else {
          setError('Entity chain not found in CORD database');
          setChain(null);
        }
      } catch (err) {
        setError(`Failed to resolve entity chain: ${err}`);
        setChain(null);
      } finally {
        setLoading(false);
      }
    };

    if (shipper_name) {
      fetchChain();
    }
  }, [shipper_name, shipper_country, consignee_name, consignee_country]);

  const renderEntity = (level: number, entity: EntityLevel | undefined, relationship: any) => {
    if (!entity) {
      return (
        <div style={{ opacity: 0.4 }}>
          <div style={{
            padding: '12px 16px',
            background: '#f3f4f6',
            border: '2px dashed #d1d5db',
            borderRadius: '6px',
            textAlign: 'center',
            color: '#6b7280',
            fontSize: '13px'
          }}>
            Level {level}: Not found in CORD
          </div>
        </div>
      );
    }

    const countryColors: { [key: string]: string } = {
      'CN': '#dc2626',  // Red for China
      'VN': '#ea580c',  // Orange for Vietnam
      'MY': '#f59e0b',  // Amber for Malaysia
      'HK': '#3b82f6',  // Blue for Hong Kong
      'US': '#10b981',  // Green for US
      'gb': '#6366f1',  // Indigo for UK
      'TH': '#d946ef',  // Pink for Thailand
      'SG': '#0891b2',  // Cyan for Singapore
    };

    const bgColor = countryColors[entity.country?.toUpperCase()] || '#6b7280';

    return (
      <div style={{
        padding: '12px 16px',
        background: 'white',
        border: `2px solid ${bgColor}`,
        borderRadius: '6px',
        marginBottom: '12px'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '6px'
        }}>
          <div style={{ flex: 1 }}>
            <div style={{
              fontSize: '14px',
              fontWeight: '600',
              color: '#1f2937',
              marginBottom: '4px'
            }}>
              Level {level}: {entity.name}
            </div>
            <div style={{
              fontSize: '12px',
              color: '#6b7280',
              display: 'flex',
              gap: '12px',
              flexWrap: 'wrap'
            }}>
              <span>🌍 {entity.country || 'N/A'}</span>
              <span>📊 {Math.round(entity.confidence * 100)}% confidence</span>
              <span style={{ background: bgColor, color: 'white', padding: '2px 6px', borderRadius: '3px', fontSize: '11px' }}>
                {entity.data_source}
              </span>
            </div>
          </div>
          {ofac_detected && level <= 2 && (
            <div style={{
              background: '#dc2626',
              color: 'white',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: '600',
              marginLeft: '12px',
              whiteSpace: 'nowrap'
            }}>
              🚨 OFAC MATCH
            </div>
          )}
        </div>
        {relationship && (
          <div style={{
            fontSize: '11px',
            color: '#7c3aed',
            fontWeight: '500',
            marginTop: '6px',
            paddingTop: '6px',
            borderTop: '1px solid #e5e7eb'
          }}>
            ← {relationship.relationship_type} (confidence: {Math.round(relationship.confidence * 100)}%)
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div style={{
        padding: '16px',
        textAlign: 'center',
        color: '#6b7280'
      }}>
        <div style={{ marginBottom: '8px' }}>🔍 Searching CORD database...</div>
        <div style={{ fontSize: '12px', color: '#9ca3af' }}>
          Querying 244K+ entities for ownership relationships...
        </div>
      </div>
    );
  }

  if (error || !chain) {
    return (
      <div style={{
        padding: '16px',
        background: '#fef3c7',
        border: '1px solid #f59e0b',
        borderRadius: '6px',
        color: '#92400e'
      }}>
        <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '4px' }}>
          ⚠️ {error || 'Entity chain not available'}
        </div>
        <div style={{ fontSize: '12px', color: '#b45309' }}>
          The shipper "{shipper_name}" could not be found in the CORD dataset.
          This may indicate a new or unregistered entity.
        </div>
      </div>
    );
  }

  return (
    <div style={{
      padding: '16px',
      background: '#f9fafb',
      borderRadius: '8px',
      border: '1px solid #e5e7eb'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px',
        paddingBottom: '12px',
        borderBottom: '1px solid #d1d5db'
      }}>
        <div>
          <h3 style={{
            margin: 0,
            fontSize: '15px',
            fontWeight: '600',
            color: '#111827'
          }}>
            Entity Ownership Chain (CORD)
          </h3>
          <p style={{
            margin: '4px 0 0 0',
            fontSize: '12px',
            color: '#6b7280'
          }}>
            Real international company relationships
          </p>
        </div>
        {risk_score !== null && (
          <div style={{
            textAlign: 'center',
            padding: '8px 12px',
            background: '#fef3c7',
            borderRadius: '6px',
            borderLeft: `4px solid ${risk_score >= 70 ? '#dc2626' : risk_score >= 40 ? '#f59e0b' : '#10b981'}`
          }}>
            <div style={{
              fontSize: '13px',
              fontWeight: '600',
              color: '#111827'
            }}>
              {Math.round(risk_score)}/100
            </div>
            <div style={{
              fontSize: '11px',
              color: '#6b7280'
            }}>
              Risk Score
            </div>
          </div>
        )}
      </div>

      {/* Chain Flow */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr auto 1fr auto 1fr',
        gap: '12px',
        alignItems: 'center',
        fontSize: '12px'
      }}>
        {/* Level 1 */}
        <div>{renderEntity(1, chain.level_1, null)}</div>

        <div style={{
          display: 'flex',
          justifyContent: 'center',
          color: '#d1d5db',
          fontSize: '20px'
        }}>
          →
        </div>

        {/* Level 2 */}
        <div>{renderEntity(2, chain.level_2, chain.level_2_relationship)}</div>

        <div style={{
          display: 'flex',
          justifyContent: 'center',
          color: '#d1d5db',
          fontSize: '20px'
        }}>
          →
        </div>

        {/* Level 3 */}
        <div>{renderEntity(3, chain.level_3, chain.level_3_relationship)}</div>
      </div>

      {/* Risk Summary */}
      {ofac_detected && (
        <div style={{
          marginTop: '16px',
          padding: '12px',
          background: '#fee2e2',
          border: '1px solid #fecaca',
          borderRadius: '6px',
          color: '#991b1b',
          fontSize: '12px'
        }}>
          <strong>⚠️ OFAC Alert:</strong> One or more entities in this chain match OFAC SDN records.
        </div>
      )}
    </div>
  );
}
