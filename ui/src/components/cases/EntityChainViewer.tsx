/**
 * Entity Chain Viewer — Display Senzing entity relationships and ownership chains
 *
 * Shows:
 * - Entity nodes (companies, people, holding companies)
 * - Relationships (OWNED_BY, DIRECTOR_SHARED, SHIPS_VIA, etc.)
 * - Confidence scores
 * - Why-explanations
 * - Risk flags per entity
 */

import { useState } from 'react';
import { ChevronRight, AlertCircle, CheckCircle, HelpCircle } from 'lucide-react';
import type { EntityChain, EntityNode, RiskFlag } from '../../services/cordApi';
import '../styles/EntityChainViewer.css';

interface EntityChainViewerProps {
  entityChains: EntityChain[];
  riskFlags: RiskFlag[];
  confidence: number;
  loading?: boolean;
  errorReason?: string;
  debugInfo?: {
    search_queries_attempted?: string[];
    no_matches_found_for?: string[];
    low_confidence_matches?: Array<{ entity: string; confidence: number }>;
  };
}

export default function EntityChainViewer({
  entityChains,
  riskFlags,
  confidence,
  loading,
  errorReason,
  debugInfo,
}: EntityChainViewerProps) {
  const [expandedChain, setExpandedChain] = useState<number>(0);
  const [selectedEntity, setSelectedEntity] = useState<EntityNode | null>(null);

  if (loading) {
    return (
      <div className="entity-chain-loading">
        <div className="spinner"></div>
        <p>Resolving entity chains via Senzing...</p>
      </div>
    );
  }

  if (!entityChains || entityChains.length === 0) {
    return (
      <div style={{ padding: '2rem' }}>
        <div style={{
          padding: '16px',
          background: '#fef3c7',
          border: '1px solid #f59e0b',
          borderRadius: '8px',
          marginBottom: '24px'
        }}>
          <h3 style={{ margin: '0 0 8px 0', color: '#92400e', fontSize: '15px', fontWeight: '600' }}>
            ⚠️ Entity Chains Not Found
          </h3>
          <p style={{ margin: '8px 0 0 0', color: '#b45309', fontSize: '14px', lineHeight: '1.5' }}>
            Senzing could not establish ownership relationships for this shipment.
            {errorReason && <> Reason: <strong>{errorReason}</strong></>}
          </p>
        </div>

        {/* Debug Info if available */}
        {debugInfo && (
          <div style={{
            padding: '12px',
            background: '#f0fdf4',
            border: '1px solid #86efac',
            borderRadius: '6px',
            marginBottom: '24px',
            fontSize: '12px',
            color: '#16a34a'
          }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '12px', fontWeight: '600' }}>Debug Information</h4>
            {debugInfo.search_queries_attempted && debugInfo.search_queries_attempted.length > 0 && (
              <div style={{ marginBottom: '8px' }}>
                <strong>Search Attempts:</strong> {debugInfo.search_queries_attempted.join(', ')}
              </div>
            )}
            {debugInfo.no_matches_found_for && debugInfo.no_matches_found_for.length > 0 && (
              <div style={{ marginBottom: '8px' }}>
                <strong>No Matches:</strong> {debugInfo.no_matches_found_for.join(', ')}
              </div>
            )}
            {debugInfo.low_confidence_matches && debugInfo.low_confidence_matches.length > 0 && (
              <div>
                <strong>Low Confidence Matches:</strong> {debugInfo.low_confidence_matches.map(m => `${m.entity} (${(m.confidence * 100).toFixed(0)}%)`).join(', ')}
              </div>
            )}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          <div style={{ padding: '16px', background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '6px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#374151', fontSize: '13px', fontWeight: '600', textTransform: 'uppercase' }}>
              ❌ Possible Reasons
            </h4>
            <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: '#6b7280', lineHeight: '1.6' }}>
              <li>Shipper name spelling variation (e.g., "Ltd" vs "Limited")</li>
              <li>Entity registered in non-English speaking country (transliteration)</li>
              <li>New entity (registered &lt; 30 days ago, not in registries yet)</li>
              <li>Entity name uses common terms ("Trading Co.", "International Ltd")</li>
              <li>CORD dataset doesn't cover this jurisdiction</li>
              <li>Entity uses multiple legal names (aliases not linked)</li>
            </ul>
          </div>

          <div style={{ padding: '16px', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: '6px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#166534', fontSize: '13px', fontWeight: '600', textTransform: 'uppercase' }}>
              🔍 Manual Research Sources
            </h4>
            <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: '#16a34a', lineHeight: '1.6' }}>
              <li><strong>OpenCorporates</strong> - 500M+ company database</li>
              <li><strong>GLEIF</strong> - Global legal entity identifiers</li>
              <li><strong>Bloomberg Terminal</strong> - Ownership & hierarchy data</li>
              <li><strong>Dun & Bradstreet</strong> - Business relationships</li>
              <li><strong>ICIJ Offshore Leaks</strong> - Beneficial ownership</li>
              <li><strong>National Registries</strong> - Country-specific databases</li>
            </ul>
          </div>

          <div style={{ padding: '16px', background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '6px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#991b1b', fontSize: '13px', fontWeight: '600', textTransform: 'uppercase' }}>
              💡 Recommended Actions
            </h4>
            <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: '#dc2626', lineHeight: '1.6' }}>
              <li>Try alternate shipper name spelling/variants</li>
              <li>Search by tax ID or registration number</li>
              <li>Check factory website for parent company</li>
              <li>Request beneficial ownership documentation</li>
              <li>Request factory visit or ISO certification</li>
              <li>Escalate to investigator for manual review</li>
            </ul>
          </div>
        </div>

        <div style={{
          padding: '16px',
          background: '#f3f4f6',
          border: '1px solid #d1d5db',
          borderRadius: '6px',
          marginBottom: '24px'
        }}>
          <h4 style={{ margin: '0 0 8px 0', color: '#374151', fontSize: '13px', fontWeight: '600' }}>
            📊 What We Searched
          </h4>
          <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: '#6b7280', fontFamily: 'monospace', lineHeight: '1.5' }}>
            CORD Datasets:<br/>
            • London: GLEIF (legal entities), ICIJ (beneficial ownership), OpenSanctions<br/>
            • Moscow: Russian tax registry, Central Asian business databases<br/>
            <br/>
            Query Scope:<br/>
            • Shipper name + Consignee name<br/>
            • Beneficial owners + Related entities<br/>
            • Directors + Shareholders<br/>
            <br/>
            Confidence Threshold: 85%+ for relationship confirmation
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => window.open('https://opencorporates.com', '_blank')}
            style={{
              flex: 1,
              padding: '12px 16px',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'background 0.2s ease'
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = '#2563eb')}
            onMouseOut={(e) => (e.currentTarget.style.background = '#3b82f6')}
          >
            🔗 OpenCorporates
          </button>
          <button
            onClick={() => window.open('https://www.gleif.org', '_blank')}
            style={{
              flex: 1,
              padding: '12px 16px',
              background: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'background 0.2s ease'
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = '#059669')}
            onMouseOut={(e) => (e.currentTarget.style.background = '#10b981')}
          >
            🏛️ GLEIF Database
          </button>
          <button
            onClick={() => window.open('https://www.icij.org/investigations/offshore-leaks/', '_blank')}
            style={{
              flex: 1,
              padding: '12px 16px',
              background: '#f59e0b',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'background 0.2s ease'
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = '#d97706')}
            onMouseOut={(e) => (e.currentTarget.style.background = '#f59e0b')}
          >
            📰 ICIJ Leaks
          </button>
        </div>
      </div>
    );
  }

  const getEntityIcon = (role?: string) => {
    switch (role) {
      case 'manufacturer':
        return '🏭';
      case 'holding_company':
        return '🏢';
      case 'shipper':
        return '📦';
      case 'consignee':
        return '🏠';
      case 'freight_forwarder':
        return '🚢';
      default:
        return '🏛️';
    }
  };

  const getRiskFlagsForEntity = (entityName: string): RiskFlag[] => {
    return riskFlags.filter(flag =>
      flag.entity?.toLowerCase().includes(entityName.toLowerCase())
    );
  };

  const renderChainFlow = (chain: EntityChain) => {
    if (!chain.entities || chain.entities.length === 0) {
      return null;
    }

    return (
      <div className="chain-flow">
        {chain.entities.map((entity, idx) => (
          <div key={idx} className="flow-item">
            <div
              className="entity-node"
              onClick={() => setSelectedEntity(entity)}
            >
              <div className="entity-icon">{getEntityIcon(entity.role)}</div>
              <div className="entity-details">
                <div className="entity-name">{entity.name}</div>
                <div className="entity-meta">
                  <span className="country-badge">{entity.country}</span>
                  {entity.confidence && (
                    <span className="confidence-badge">
                      {(entity.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>
              {getRiskFlagsForEntity(entity.name).length > 0 && (
                <div className="entity-risk-indicator">
                  <AlertCircle size={16} className="risk-icon" />
                </div>
              )}
            </div>

            {idx < chain.entities.length - 1 && (
              <div className="flow-connector">
                <ChevronRight size={20} />
                {chain.relationships && chain.relationships[idx] && (
                  <div className="relationship-label">
                    {chain.relationships[idx].type}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="entity-chain-viewer">
      {/* Header */}
      <div className="entity-chain-header">
        <div className="header-info">
          <h3>Entity Ownership Chain (Senzing Resolution)</h3>
          <p>Real international company relationships from CORD data</p>
        </div>
        <div className="header-stats">
          <div className="stat">
            <span className="label">Entities</span>
            <span className="value">
              {entityChains.reduce((sum, chain) => sum + (chain.entities?.length || 0), 0)}
            </span>
          </div>
          <div className="stat">
            <span className="label">Confidence</span>
            <span className="value">{(confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="stat">
            <span className="label">Risk Flags</span>
            <span className={`value ${riskFlags.length > 0 ? 'flag-alert' : 'flag-clear'}`}>
              {riskFlags.length}
            </span>
          </div>
        </div>
      </div>

      {/* Chains */}
      <div className="entity-chains">
        {entityChains.map((chain, chainIdx) => (
          <div
            key={chainIdx}
            className={`chain-container ${expandedChain === chainIdx ? 'expanded' : ''}`}
          >
            <div
              className="chain-header"
              onClick={() => setExpandedChain(expandedChain === chainIdx ? -1 : chainIdx)}
            >
              <div className="chain-title">
                <strong>Chain {chainIdx + 1}:</strong>
                {chain.entities?.[0] && (
                  <>
                    <span className="primary-entity">
                      {chain.entities[0].name}
                    </span>
                    {chain.entities.length > 1 && (
                      <span className="chain-length">
                        (+{chain.entities.length - 1} related)
                      </span>
                    )}
                  </>
                )}
              </div>
              <div className="chain-toggle">
                {expandedChain === chainIdx ? '▼' : '▶'}
              </div>
            </div>

            {expandedChain === chainIdx && (
              <div className="chain-content">
                {renderChainFlow(chain)}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Risk Summary */}
      {riskFlags.length > 0 && (
        <div className="risk-summary">
          <h4>🚨 Detected Risk Indicators</h4>
          <div className="risk-grid">
            {riskFlags.map((flag, idx) => (
              <div key={idx} className={`risk-card severity-${flag.severity.toLowerCase()}`}>
                <div className="risk-icon">
                  {flag.severity === 'CRITICAL' && '🔴'}
                  {flag.severity === 'HIGH' && '🟠'}
                  {flag.severity === 'MEDIUM' && '🟡'}
                  {flag.severity === 'LOW' && '🟢'}
                </div>
                <div className="risk-content">
                  <div className="risk-type">{flag.type}</div>
                  <div className="risk-detail">{flag.detail}</div>
                  {flag.entity && <div className="risk-entity">Entity: {flag.entity}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
