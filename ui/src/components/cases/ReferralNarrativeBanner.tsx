import React, { useMemo } from 'react';
import { AlertTriangle } from 'lucide-react';
import { ReferralNarrativeBannerProps } from './ReferralPackage.types';
import './ReferralNarrativeBanner.css';

/**
 * ReferralNarrativeBanner
 * Contextual investigation narrative banner with risk alert
 *
 * Displays:
 * - High-risk alert banner with semantic coloring
 * - Narrative text: "Potential Duty Evasion via Illogical Transshipment..."
 * - Risk badge: [HIGH RISK: {risk_score}/100]
 *
 * Accessibility:
 * - role="alert" announces important updates
 * - aria-live="polite" for dynamic content
 * - Sufficient contrast and icon + text labeling
 */
export default function ReferralNarrativeBanner({
  shipper_name,
  shipper_country,
  declared_origin,
  actual_origin,
  risk_score,
  vessel_path,
}: ReferralNarrativeBannerProps) {
  const narrative = useMemo(() => {
    const pathDescription = vessel_path.length > 2
      ? `via ${vessel_path.slice(1, -1).join(' → ')} `
      : '';

    return `Potential Duty Evasion via Illogical Transshipment. Shipment from ${shipper_name} (${shipper_country}) claims ${declared_origin} origin, but physical vessel tracking confirms cargo loading at ${actual_origin} hub ${pathDescription}and reroute to ${vessel_path[vessel_path.length - 1]}.`;
  }, [shipper_name, shipper_country, declared_origin, actual_origin, vessel_path]);

  const riskLevel = risk_score >= 70 ? 'HIGH RISK' : risk_score >= 40 ? 'MEDIUM RISK' : 'LOW RISK';

  return (
    <div
      className="referral-narrative-banner risk-token-l3"
      role="alert"
      aria-live="polite"
      aria-atomic="true"
    >
      {/* Alert Icon */}
      <div className="banner__icon">
        <AlertTriangle
          size={24}
          aria-hidden="true"
          className="banner__icon-symbol"
        />
      </div>

      {/* Narrative Content */}
      <div className="banner__content">
        <p className="banner__narrative">
          {narrative}
        </p>

        {/* Risk Badge */}
        <div className="banner__badge" aria-label={`Risk level: ${riskLevel}, Score: ${risk_score} out of 100`}>
          <span className="banner__badge-text">
            {riskLevel}: {Math.round(risk_score)}/100
          </span>
        </div>
      </div>
    </div>
  );
}
