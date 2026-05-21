import React from 'react';
import { Factory } from 'lucide-react';
import { Section3_10_SupplierVerification } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_10Props {
  data: Section3_10_SupplierVerification;
  defaultExpanded?: boolean;
}

export function ReferralSection3_10({
  data,
  defaultExpanded = false,
}: ReferralSection3_10Props) {
  const flaggedSuppliers = data.suppliers.filter((s) => s.capacity_flag);
  const anomalyCount = flaggedSuppliers.length;

  return (
    <SectionWrapper
      sectionId="section-3-10"
      sectionNumber="3-10"
      title="Supplier Capacity Verification"
      icon={<Factory size={16} />}
      dataQuality="COMPLETE"
      anomalyCount={anomalyCount}
      defaultExpanded={defaultExpanded}
    >
      <div className="referral-section__stats">
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">Total Suppliers</span>
          <span className="referral-section__stat-value">{data.suppliers.length}</span>
        </div>
        {anomalyCount > 0 && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Capacity Gaps</span>
            <span className="referral-section__stat-value" style={{ color: '#d9381e' }}>
              {anomalyCount}
            </span>
          </div>
        )}
        {data.total_capacity_gap !== undefined && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Total Gap</span>
            <span className="referral-section__stat-value" style={{ color: '#d9381e' }}>
              {data.total_capacity_gap.toLocaleString()}
            </span>
          </div>
        )}
      </div>

      <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {data.suppliers.map((supplier, idx) => {
          const utilizationPct = supplier.capacity_utilization_pct ?? (supplier.actual_volume / supplier.max_annual_capacity) * 100;
          const isOverCapacity = supplier.actual_volume > supplier.max_annual_capacity;
          const hasGap = supplier.capacity_flag || isOverCapacity;

          return (
            <div
              key={idx}
              style={{
                padding: '12px',
                border: '1px solid #e5e8eb',
                borderLeft: `3px solid ${hasGap ? '#d9381e' : '#2e8540'}`,
                backgroundColor: hasGap ? '#ffe6e6' : '#e7f4e4',
                borderRadius: '6px',
              }}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: '12px',
                  marginBottom: '12px',
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: hasGap ? '#8b0000' : '#1b4d22',
                      marginBottom: '4px',
                      textTransform: 'uppercase',
                    }}
                  >
                    Supplier
                  </div>
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: hasGap ? '#8b0000' : '#1b4d22',
                    }}
                  >
                    {supplier.supplier_name}
                  </div>
                </div>
                <div>
                  <div
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: hasGap ? '#8b0000' : '#1b4d22',
                      marginBottom: '4px',
                      textTransform: 'uppercase',
                    }}
                  >
                    Declared Volume
                  </div>
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: hasGap ? '#8b0000' : '#1b4d22',
                    }}
                  >
                    {supplier.declared_volume.toLocaleString()} units
                  </div>
                </div>
                <div>
                  <div
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: hasGap ? '#8b0000' : '#1b4d22',
                      marginBottom: '4px',
                      textTransform: 'uppercase',
                    }}
                  >
                    Capacity Utilization
                  </div>
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: utilizationPct > 100 ? '#d9381e' : hasGap ? '#8b0000' : '#1b4d22',
                    }}
                  >
                    {Math.round(utilizationPct)}%
                    {utilizationPct > 100 && ' ⚠️ Over'}
                  </div>
                </div>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 200px',
                  gap: '12px',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: '11px',
                      color: hasGap ? '#8b0000' : '#1b4d22',
                      marginBottom: '6px',
                      display: 'flex',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span>
                      Max Capacity: {supplier.max_annual_capacity.toLocaleString()} units
                    </span>
                  </div>
                  <div style={{ width: '100%', height: '8px', backgroundColor: 'rgba(255,255,255,0.5)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.min(utilizationPct, 100)}%`,
                        backgroundColor: utilizationPct > 100 ? '#d9381e' : hasGap ? '#d9381e' : '#2e8540',
                      }}
                    />
                  </div>
                  <div
                    style={{
                      fontSize: '10px',
                      color: hasGap ? '#8b0000' : '#1b4d22',
                      marginTop: '4px',
                    }}
                  >
                    Actual Volume: {supplier.actual_volume.toLocaleString()} units
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  {isOverCapacity ? (
                    <div style={{ color: '#d9381e', fontWeight: 600, fontSize: '12px' }}>
                      +{(supplier.actual_volume - supplier.max_annual_capacity).toLocaleString()} over capacity
                    </div>
                  ) : (
                    <div
                      style={{
                        color: hasGap ? '#8b0000' : '#1b4d22',
                        fontWeight: 600,
                        fontSize: '12px',
                      }}
                    >
                      {(supplier.max_annual_capacity - supplier.actual_volume).toLocaleString()} remaining capacity
                    </div>
                  )}
                </div>
              </div>

              {supplier.evidence && (
                <div
                  className="referral-section__evidence"
                  style={{
                    marginTop: '12px',
                    borderLeftColor: '#d9381e',
                    backgroundColor: 'rgba(255,255,255,0.6)',
                  }}
                >
                  <span className="referral-section__evidence-label">Evidence</span>
                  {supplier.evidence}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {data.critical_suppliers && data.critical_suppliers.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4
            style={{
              margin: '0 0 12px 0',
              fontSize: '13px',
              fontWeight: 600,
              color: '#d9381e',
            }}
          >
            Critical Suppliers (Requires Investigation)
          </h4>
          {data.critical_suppliers.map((supplier, idx) => (
            <div key={idx} className="referral-section__evidence" style={{ borderLeftColor: '#d9381e' }}>
              <span style={{ fontSize: '12px', color: '#2d3748' }}>⚠️ {supplier}</span>
            </div>
          ))}
        </div>
      )}
    </SectionWrapper>
  );
}
