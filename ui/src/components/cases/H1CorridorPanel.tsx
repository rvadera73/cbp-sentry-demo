
export default function H1CorridorPanel({ case: c }: any) {
  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-bold">H1: Corridor Risk Analysis (40 pts max)</h2>
      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 border border-gray-200 rounded-lg">
          <p className="text-sm font-semibold text-gray-700">Trade Corridor</p>
          <p className="text-lg font-bold">{c.shipper_country} → {c.consignee_country}</p>
        </div>
        <div className="p-4 border border-gray-200 rounded-lg">
          <p className="text-sm font-semibold text-gray-700">HTS Code</p>
          <p className="text-lg font-bold">{c.commodity_code}</p>
        </div>
        <div className="p-4 border border-gray-200 rounded-lg">
          <p className="text-sm font-semibold text-gray-700">Declared Value</p>
          <p className="text-lg font-bold">${(c.declared_value || 0).toLocaleString()}</p>
        </div>
        <div className="p-4 border border-gray-200 rounded-lg">
          <p className="text-sm font-semibold text-gray-700">Risk Level</p>
          <p className="text-lg font-bold">{c.h1_risk_level}</p>
        </div>
      </div>
    </div>
  );
}
