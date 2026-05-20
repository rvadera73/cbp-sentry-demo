
export default function CaseOverview({ case: c }: any) {
  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Case Overview</h2>
      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 border border-gray-200 rounded-lg">
          <p className="text-sm text-gray-600 mb-1">Shipper</p>
          <p className="font-semibold">{c.shipper_name}</p>
        </div>
        <div className="p-4 border border-gray-200 rounded-lg">
          <p className="text-sm text-gray-600 mb-1">Consignee</p>
          <p className="font-semibold">{c.consignee_name}</p>
        </div>
        <div className="p-4 border border-gray-200 rounded-lg">
          <p className="text-sm text-gray-600 mb-1">Commodity</p>
          <p className="font-semibold">{c.commodity_code}</p>
        </div>
        <div className="p-4 border border-gray-200 rounded-lg">
          <p className="text-sm text-gray-600 mb-1">Value</p>
          <p className="font-semibold">${c.declared_value.toLocaleString()}</p>
        </div>
      </div>
    </div>
  );
}
