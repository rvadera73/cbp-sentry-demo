import React from 'react';
import { Package } from 'lucide-react';
import { Section3_2_LineItems } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_2Props {
  data: Section3_2_LineItems;
  defaultExpanded?: boolean;
}

export function ReferralSection3_2({
  data,
  defaultExpanded = false,
}: ReferralSection3_2Props) {
  const flaggedItems = data.items.filter((item) => item.flag !== 'LOW');
  const anomalyCount = flaggedItems.length;

  return (
    <SectionWrapper
      sectionId="section-3-2"
      sectionNumber="3-2"
      title="Line Items & Commodity Detail"
      icon={<Package size={16} />}
      dataQuality="COMPLETE"
      anomalyCount={anomalyCount}
      defaultExpanded={defaultExpanded}
    >
      <div className="referral-section__stats">
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">Total Items</span>
          <span className="referral-section__stat-value">{data.items.length}</span>
        </div>
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">Total Value</span>
          <span className="referral-section__stat-value">
            ${(data.totalValue / 1000).toFixed(0)}K
          </span>
        </div>
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">Total Quantity</span>
          <span className="referral-section__stat-value">
            {data.totalQuantity.toLocaleString()}
          </span>
        </div>
        {data.commodityCategory && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Category</span>
            <span
              className="referral-section__stat-value"
              style={{ fontSize: '14px' }}
            >
              {data.commodityCategory}
            </span>
          </div>
        )}
      </div>

      <table className="referral-section__table">
        <thead>
          <tr>
            <th>Line #</th>
            <th>HTS Code</th>
            <th>Commodity</th>
            <th style={{ textAlign: 'right' }}>Qty</th>
            <th style={{ textAlign: 'right' }}>Unit Price</th>
            <th style={{ textAlign: 'center' }}>Risk</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((item) => (
            <tr
              key={item.line_number}
              style={{
                backgroundColor:
                  item.flag === 'HIGH'
                    ? '#ffe6e6'
                    : item.flag === 'MEDIUM'
                      ? '#fff7e6'
                      : 'inherit',
              }}
            >
              <td>{item.line_number}</td>
              <td>
                <code>{item.hts_code}</code>
              </td>
              <td title={item.commodity_description}>
                {item.commodity_description.length > 40
                  ? item.commodity_description.substring(0, 40) + '…'
                  : item.commodity_description}
              </td>
              <td style={{ textAlign: 'right' }}>
                {item.quantity.toLocaleString()} {item.unit}
              </td>
              <td style={{ textAlign: 'right' }}>
                ${item.unit_price.toFixed(2)}
              </td>
              <td style={{ textAlign: 'center' }}>
                {item.flag === 'HIGH' && <span style={{ color: '#d9381e', fontWeight: 600 }}>⚠️</span>}
                {item.flag === 'MEDIUM' && <span style={{ color: '#e6a100', fontWeight: 600 }}>!</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {flaggedItems.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600 }}>
            Flagged Commodities
          </h4>
          {flaggedItems.map((item) => (
            <div key={item.line_number} className="referral-section__evidence">
              <span className="referral-section__evidence-label">
                Line {item.line_number}: {item.hts_code}
              </span>
              {item.flagReason || 'Anomaly detected'}
            </div>
          ))}
        </div>
      )}
    </SectionWrapper>
  );
}
