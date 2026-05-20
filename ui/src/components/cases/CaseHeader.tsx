import { AlertTriangle } from 'lucide-react';
import { Case } from '../../types/models';

interface Props {
  case: Case;
}

export default function CaseHeader({ case: c }: Props) {
  const riskScore = Math.round(c.risk_score || 0);
  const riskTier = riskScore >= 70 ? 'HIGH' : riskScore >= 50 ? 'MEDIUM' : 'LOW';
  const riskColor =
    riskTier === 'HIGH'
      ? 'text-red-600 bg-red-50 border-red-200'
      : riskTier === 'MEDIUM'
      ? 'text-amber-600 bg-amber-50 border-amber-200'
      : 'text-green-600 bg-green-50 border-green-200';

  const actionOptions = riskTier === 'HIGH' ? 'EXAMINE' : riskTier === 'MEDIUM' ? 'REVIEW' : 'CLEAR';

  return (
    <div className={`border-b border-gray-200 ${riskColor}`}>
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-4 gap-6 mb-6">
          {/* Case ID */}
          <div>
            <p className="text-xs uppercase tracking-wide font-semibold text-gray-600 mb-1">
              Case ID
            </p>
            <p className="text-lg font-mono text-gray-900">{c.id.substring(0, 12)}</p>
          </div>

          {/* Route */}
          <div>
            <p className="text-xs uppercase tracking-wide font-semibold text-gray-600 mb-1">
              Route
            </p>
            <p className="text-lg font-bold text-gray-900">
              {c.shipper_country} → {c.consignee_country}
            </p>
          </div>

          {/* HTS Code */}
          <div>
            <p className="text-xs uppercase tracking-wide font-semibold text-gray-600 mb-1">
              HTS Code
            </p>
            <p className="text-lg font-mono font-bold text-gray-900">{c.commodity_code}</p>
          </div>

          {/* Value */}
          <div>
            <p className="text-xs uppercase tracking-wide font-semibold text-gray-600 mb-1">
              Declared Value
            </p>
            <p className="text-lg font-bold text-gray-900">
              ${(c.declared_value || 0).toLocaleString()}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6">
          {/* Parties */}
          <div>
            <p className="text-xs uppercase tracking-wide font-semibold text-gray-600 mb-2">
              Shipper
            </p>
            <p className="font-semibold text-gray-900 mb-3">{c.shipper_name}</p>

            <p className="text-xs uppercase tracking-wide font-semibold text-gray-600 mb-2">
              Consignee
            </p>
            <p className="font-semibold text-gray-900">{c.consignee_name}</p>
          </div>

          {/* Risk Score Gauge */}
          <div className="flex flex-col items-center justify-center">
            <div className="relative w-32 h-32 rounded-full border-8 border-gray-300 flex items-center justify-center bg-white shadow-lg">
              <div className="text-center">
                <p className="text-4xl font-bold text-gray-900">{riskScore}</p>
                <p className="text-xs uppercase font-bold text-gray-600">/100</p>
              </div>
              {/* Risk indicator ring */}
              <div
                className={`absolute inset-0 rounded-full border-8 ${
                  riskTier === 'HIGH'
                    ? 'border-red-500'
                    : riskTier === 'MEDIUM'
                    ? 'border-amber-500'
                    : 'border-green-500'
                }`}
                style={{
                  clipPath: `inset(0 ${100 - Math.min((riskScore / 100) * 100, 100)}% 0 0)`,
                  borderRadius: '100%',
                }}
              ></div>
            </div>
            <p className="mt-3 font-bold text-gray-900">
              {riskTier} RISK
            </p>
          </div>

          {/* Recommended Action */}
          <div>
            <p className="text-xs uppercase tracking-wide font-semibold text-gray-600 mb-3">
              CBP Action Required
            </p>
            <div className="space-y-2">
              <button
                className={`w-full py-2 px-4 rounded-lg font-semibold text-sm transition-colors ${
                  actionOptions === 'EXAMINE'
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Examine on Arrival
              </button>
              <button className="w-full py-2 px-4 bg-gray-200 text-gray-700 rounded-lg font-semibold text-sm hover:bg-gray-300 transition-colors">
                {actionOptions === 'CLEAR' ? 'Clear' : 'Secondary Exam'}
              </button>
              <button className="w-full py-2 px-4 bg-gray-200 text-gray-700 rounded-lg font-semibold text-sm hover:bg-gray-300 transition-colors">
                TRLED Referral
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
