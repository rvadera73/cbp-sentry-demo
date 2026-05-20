
export default function H3IntelPanel({ case: c }: any) {
  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-bold">H3: Intelligence & Risk Indicators (25 pts max)</h2>
      <div className="space-y-2">
        <div className="p-3 border border-gray-200 rounded-lg">
          <p className="text-sm font-semibold">OFAC/SDN Screening</p>
          <p className="text-xs text-gray-600">No hits detected</p>
        </div>
        <div className="p-3 border border-gray-200 rounded-lg">
          <p className="text-sm font-semibold">Watch List Entities</p>
          <p className="text-xs text-gray-600">Prior EAPA filings analysis</p>
        </div>
        <div className="p-3 border border-gray-200 rounded-lg">
          <p className="text-sm font-semibold">New Importer Signals</p>
          <p className="text-xs text-gray-600">Company age and import history</p>
        </div>
        <div className="p-3 border border-gray-200 rounded-lg">
          <p className="text-sm font-semibold">Volume Surge Detection</p>
          <p className="text-xs text-gray-600">Baseline vs declared patterns</p>
        </div>
      </div>
    </div>
  );
}
