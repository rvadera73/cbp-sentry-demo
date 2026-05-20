
export default function H2VesselPanel({ case: c }: any) {
  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-bold">H2: Vessel & Document Intelligence (35 pts max)</h2>
      <div className="p-4 border border-gray-200 rounded-lg">
        <p className="text-sm font-semibold text-gray-700 mb-2">AIS Routing History</p>
        <p className="text-sm text-gray-600">Vessel tracking and dwell time analysis (coming soon)</p>
      </div>
      <div className="p-4 border border-gray-200 rounded-lg">
        <p className="text-sm font-semibold text-gray-700 mb-2">ISF Element 9 Analysis</p>
        <p className="text-sm text-gray-600">Pre-arrival country of origin verification</p>
      </div>
      <div className="p-4 border border-gray-200 rounded-lg">
        <p className="text-sm font-semibold text-gray-700 mb-2">Document Checklist</p>
        <ul className="space-y-1 text-sm">
          <li>✓ Commercial Invoice</li>
          <li>✓ Bill of Lading</li>
          <li>✗ Factory Records</li>
        </ul>
      </div>
    </div>
  );
}
