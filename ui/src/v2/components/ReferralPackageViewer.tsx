import React, { useState, useRef, useMemo } from 'react';
import { Download, Send, ChevronRight, FileText, AlertTriangle } from 'lucide-react';
import { computeRiskBreakdown } from '../utils/riskBreakdown';

interface ReferralPackageViewerProps {
  selectedReferral: any;
  selectedCase: any;
  findings: any[];
  referralNarrative: string;
  setReferralNarrative: (narrative: string) => void;
  onCompile: () => void;
  compileLoading: boolean;
  selectedCaseShipments?: any[];
  onSubmit?: () => void;
}

export function ReferralPackageViewer({
  selectedReferral,
  selectedCase,
  findings,
  referralNarrative,
  setReferralNarrative,
  onCompile,
  compileLoading,
  selectedCaseShipments = [],
  onSubmit,
}: ReferralPackageViewerProps) {
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const shipment = selectedCaseShipments?.[0];

  const enrichedShipment = useMemo(() => {
    if (!shipment) return null;

    let risk_breakdown = shipment.risk_breakdown || computeRiskBreakdown(shipment);

    if (selectedReferral?.sections?.section_3_12_score_breakdown?.calculation_table) {
      risk_breakdown = {
        ...risk_breakdown,
        calculation_table: selectedReferral.sections.section_3_12_score_breakdown.calculation_table,
        confidence_interval: selectedReferral.sections.section_3_12_score_breakdown.confidence_interval || risk_breakdown?.confidence_interval,
      };
    }

    return {
      ...shipment,
      risk_breakdown,
      audit_trail: selectedReferral?.audit_trail || shipment.audit_trail,
    };
  }, [shipment, selectedReferral]);

  // Get all sections from referral package
  const sections = useMemo(() => {
    if (!selectedReferral?.sections) return [];

    const sectionOrder = [
      'section_3_1_shipment_identification',
      'section_3_2_line_items',
      'section_3_3_routing_history',
      'section_3_4_parties_and_roles',
      'section_3_5_entity_ownership_chain',
      'section_3_6_historical_import_pattern',
      'section_3_7_trade_flow_intelligence',
      'section_3_8_document_review',
      'section_3_9_document_consistency',
      'section_3_10_supplier_verification',
      'section_3_11_risk_indicators',
      'section_3_12_score_breakdown',
      'section_3_13_what_if_scenarios',
      'section_3_14_data_sources',
    ];

    return sectionOrder.map(id => ({
      id,
      title: selectedReferral.sections[id]?.title || 'Unknown Section',
      data: selectedReferral.sections[id],
    })).filter(s => s.data);
  }, [selectedReferral]);

  // Set default section on load
  React.useEffect(() => {
    if (!selectedSectionId && sections.length > 0) {
      setSelectedSectionId(sections[0].id);
    }
  }, [sections, selectedSectionId]);

  const selectedSection = sections.find(s => s.id === selectedSectionId);

  const handleExportPDF = async () => {
    setExportLoading(true);
    try {
      const recommendation = selectedCase?.risk_score >= 80
        ? 'HOLD FOR EXAMINATION'
        : selectedCase?.risk_score >= 50
        ? 'EXAMINE'
        : 'CLEAR';

      const exportRequest = {
        case_id: selectedCase?.case_id || 'unknown',
        shipment_id: shipment?.shipment_id || 'unknown',
        risk_score: Math.round(selectedCase?.risk_score || 0),
        recommendation: recommendation,
        shipper_name: shipment?.shipper_name || 'Unknown',
        commodity_name: shipment?.commodity_name || 'Unknown',
        origin_country: shipment?.origin_country || 'Unknown',
        destination_country: shipment?.destination_country || 'Unknown',
        shipment_narrative: referralNarrative,
      };

      const response = await fetch('/api/referral/export-pdf-v2', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(exportRequest),
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`PDF export failed: ${response.statusText} - ${errText}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `CBP-EAPA-Referral-${selectedCase?.case_id || 'unknown'}-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('PDF export failed:', error);
      alert(`Failed to export PDF: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setExportLoading(false);
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 85) return 'text-[#D83933] bg-[#FFECEB]';
    if (score >= 70) return 'text-[#D83933] bg-[#FFECEB]';
    if (score >= 50) return 'text-[#FFBE2E] bg-[#FFFBEA]';
    return 'text-[#07A41E] bg-[#EAFCE4]';
  };

  const getRiskLevel = (score: number) => {
    if (score >= 85) return '🔴🔴 EXTREME';
    if (score >= 70) return '🔴 CRITICAL';
    if (score >= 50) return '🟡 MEDIUM-ELEVATED';
    return '🟢 LOW';
  };

  // Show loading state if no data yet
  if (!selectedReferral || sections.length === 0) {
    return (
      <div className="flex flex-col h-full bg-[#F7F9FC]">
        {/* Header */}
        <div className="bg-white border-b border-[#D0D7DE] px-6 py-4 shadow-sm">
          <div>
            <h2 className="text-lg font-bold text-[#0B1F33]">CBP REFERRAL PACKAGE</h2>
            <p className="text-xs text-slate-500 font-mono">
              {selectedCase?.case_id} • {shipment?.shipment_id}
            </p>
          </div>
        </div>

        {/* Empty State */}
        <div className="flex-1 flex items-center justify-center bg-white">
          <div className="flex flex-col items-center space-y-4 max-w-md">
            <AlertTriangle className="w-12 h-12 text-slate-400" />
            <div className="text-center">
              <h3 className="text-sm font-bold text-[#0B1F33] mb-2">No Referral Package Generated</h3>
              <p className="text-xs text-slate-600 mb-4">
                A referral package with detailed analysis sections must be compiled first. Click "COMPILE AI NARRATIVE" to generate the complete referral package with all sections.
              </p>
            </div>
            <button
              onClick={onCompile}
              disabled={compileLoading}
              className="px-4 py-2 bg-[#005EA2] hover:bg-[#0076D6] disabled:opacity-50 text-white text-[9px] font-bold rounded-sm"
            >
              {compileLoading ? 'COMPILING...' : 'COMPILE AI NARRATIVE'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#F7F9FC]">
      {/* Header */}
      <div className="bg-white border-b border-[#D0D7DE] px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-[#0B1F33]">CBP REFERRAL PACKAGE</h2>
            <p className="text-xs text-slate-500 font-mono">
              {selectedCase?.case_id} • {shipment?.shipment_id} • {shipment?.origin_country}→{shipment?.destination_country}
            </p>
          </div>
          <div className={`px-4 py-2 rounded-sm text-sm font-bold ${getRiskColor(selectedCase?.risk_score || 0)}`}>
            {selectedCase?.risk_score || 0}/100 • {getRiskLevel(selectedCase?.risk_score || 0)}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden gap-4 p-4">
        {/* LEFT SIDEBAR - Section Navigation */}
        <div className="w-56 bg-white rounded-sm border border-[#D0D7DE] overflow-y-auto shadow-sm">
          <div className="p-3 border-b border-[#D0D7DE] bg-slate-50">
            <h3 className="text-[10px] font-bold uppercase text-slate-600">Contents</h3>
            <p className="text-[8px] text-slate-500 mt-1">{sections.length} Sections</p>
          </div>

          <div className="divide-y divide-[#D0D7DE]">
            {sections.map((section, idx) => (
              <button
                key={section.id}
                onClick={() => setSelectedSectionId(section.id)}
                className={`w-full text-left px-4 py-3 text-xs transition-colors ${
                  selectedSectionId === section.id
                    ? 'bg-[#005EA2] text-white font-bold'
                    : 'bg-white text-[#0B1F33] hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <FileText className="w-3 h-3" />
                  <div className="flex-1">
                    <div className="font-bold text-[9px]">Table 3-{idx + 1}</div>
                    <div className="text-[8px] text-slate-600 leading-tight line-clamp-2">
                      {section.title.replace('Table 3-', '').replace(': ', '')}
                    </div>
                  </div>
                  {selectedSectionId === section.id && <ChevronRight className="w-3 h-3" />}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* RIGHT PANE - Section Content */}
        <div ref={contentRef} className="flex-1 bg-white rounded-sm border border-[#D0D7DE] overflow-y-auto shadow-sm">
          {selectedSection ? (
            <div className="p-6 space-y-4">
              {/* Section Title */}
              <div className="border-b-2 border-[#005EA2] pb-4">
                <h2 className="text-lg font-bold text-[#0B1F33]">{selectedSection.title}</h2>
              </div>

              {/* Section Content - Render based on type */}
              <SectionRenderer section={selectedSection.data} />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500">
              <p className="text-sm">Select a section to view</p>
            </div>
          )}
        </div>
      </div>

      {/* Footer with Actions */}
      <div className="bg-white border-t border-[#D0D7DE] px-6 py-4 flex items-center justify-between">
        <div className="text-[8px] text-slate-500 font-mono">
          CBP Referral Package • {selectedReferral?.created_at ? new Date(selectedReferral.created_at).toLocaleString() : 'Draft'}
        </div>
        <div className="flex gap-3">
          <button
            onClick={onCompile}
            disabled={compileLoading}
            className="px-4 py-2 bg-slate-600 hover:bg-slate-700 disabled:opacity-50 text-white text-[9px] font-bold rounded-sm"
          >
            {compileLoading ? 'COMPILING AI...' : 'COMPILE AI NARRATIVE'}
          </button>
          <button
            onClick={handleExportPDF}
            disabled={exportLoading}
            className="px-4 py-2 bg-[#0076D6] hover:bg-[#005EA2] disabled:opacity-50 text-white text-[9px] font-bold rounded-sm flex items-center space-x-2"
          >
            <Download className="w-3 h-3" />
            <span>{exportLoading ? 'EXPORTING...' : 'EXPORT PDF'}</span>
          </button>
          <button
            onClick={() => {
              if (onSubmit) onSubmit();
            }}
            className="px-4 py-2 bg-[#07A41E] hover:bg-[#06843E] text-white text-[9px] font-bold rounded-sm flex items-center space-x-2"
          >
            <Send className="w-3 h-3" />
            <span>SUBMIT REFERRAL</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// Helper component to render different section types
function SectionRenderer({ section }: { section: any }) {
  if (!section) return null;

  const type = section.title?.toLowerCase();

  // Table 3-1: Shipment Identification
  if (type?.includes('shipment identification')) {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-[8px] font-bold text-slate-500 uppercase mb-1">Shipper</p>
            <p className="text-sm text-[#0B1F33]">{section.shipper || 'N/A'}</p>
          </div>
          <div>
            <p className="text-[8px] font-bold text-slate-500 uppercase mb-1">Consignee</p>
            <p className="text-sm text-[#0B1F33]">{section.consignee || 'N/A'}</p>
          </div>
          <div>
            <p className="text-[8px] font-bold text-slate-500 uppercase mb-1">Commodity</p>
            <p className="text-sm text-[#0B1F33]">{section.commodity || 'N/A'}</p>
          </div>
          <div>
            <p className="text-[8px] font-bold text-slate-500 uppercase mb-1">Route</p>
            <p className="text-sm text-[#0B1F33]">{section.route || 'N/A'}</p>
          </div>
          <div>
            <p className="text-[8px] font-bold text-slate-500 uppercase mb-1">HS Code</p>
            <p className="text-sm font-mono text-[#0B1F33]">{section.hs_code || 'N/A'}</p>
          </div>
          <div>
            <p className="text-[8px] font-bold text-slate-500 uppercase mb-1">Value (USD)</p>
            <p className="text-sm text-[#0B1F33]">${section.value_usd?.toLocaleString() || '0'}</p>
          </div>
        </div>
        <div className="p-3 bg-slate-50 rounded border border-[#D0D7DE]">
          <p className="text-[8px] font-bold text-slate-600 uppercase mb-2">Summary</p>
          <p className="text-xs text-slate-700">{section.summary || 'N/A'}</p>
        </div>
      </div>
    );
  }

  // Table 3-2: Line Items
  if (type?.includes('line items')) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100 border-b-2 border-[#D0D7DE]">
              <th className="text-left p-2 font-bold">HS Code</th>
              <th className="text-left p-2 font-bold">Description</th>
              <th className="text-center p-2 font-bold">Qty</th>
              <th className="text-center p-2 font-bold">Unit</th>
              <th className="text-right p-2 font-bold">Value (USD)</th>
            </tr>
          </thead>
          <tbody>
            {section.items?.map((item: any, idx: number) => (
              <tr key={idx} className="border-b border-[#D0D7DE]">
                <td className="p-2 font-mono">{item.hs_code}</td>
                <td className="p-2">{item.description}</td>
                <td className="p-2 text-center">{item.quantity}</td>
                <td className="p-2 text-center">{item.unit}</td>
                <td className="p-2 text-right font-bold">${item.declared_value?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Table 3-3: AIS Routing History
  if (type?.includes('routing history')) {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-[8px] font-bold text-slate-500 uppercase mb-1">Vessel</p>
            <p className="text-sm text-[#0B1F33]">{section.vessel || 'N/A'}</p>
          </div>
          <div>
            <p className="text-[8px] font-bold text-slate-500 uppercase mb-1">IMO</p>
            <p className="text-sm font-mono text-[#0B1F33]">{section.vessel_imo || 'N/A'}</p>
          </div>
          <div>
            <p className="text-[8px] font-bold text-slate-500 uppercase mb-1">Dwell Days</p>
            <p className="text-sm text-[#0B1F33]">{section.dwell_days?.toFixed(1) || 'N/A'} days</p>
          </div>
          <div>
            <p className="text-[8px] font-bold text-slate-500 uppercase mb-1">Dwell Anomaly</p>
            <p className={`text-sm font-bold ${section.dwell_anomaly === 'HIGH' ? 'text-[#D83933]' : section.dwell_anomaly === 'MEDIUM' ? 'text-[#FFBE2E]' : 'text-[#07A41E]'}`}>
              {section.dwell_anomaly || 'N/A'}
            </p>
          </div>
        </div>
        <div>
          <p className="text-[8px] font-bold text-slate-500 uppercase mb-2">Port Calls</p>
          <div className="flex flex-wrap gap-2">
            {section.route?.map((port: string, idx: number) => (
              <div key={idx} className="px-2 py-1 bg-slate-100 rounded text-[9px] font-mono">
                {port}
              </div>
            ))}
          </div>
        </div>
        <div className="p-3 bg-slate-50 rounded border border-[#D0D7DE]">
          <p className="text-[8px] font-bold text-slate-600 uppercase mb-2">Summary</p>
          <p className="text-xs text-slate-700">{section.summary || 'N/A'}</p>
        </div>
      </div>
    );
  }

  // Table 3-12: Risk Score Breakdown (with calculation tables)
  if (type?.includes('score breakdown')) {
    const calc = section.calculation_table;
    return (
      <div className="space-y-6">
        {/* Risk Score Summary */}
        <div className="bg-blue-50 border border-[#005EA2] rounded p-4">
          <div className="text-center">
            <p className="text-[8px] font-bold text-slate-600 uppercase mb-2">Final Risk Score</p>
            <p className="text-4xl font-black text-[#D83933]">{section.total_score?.toFixed(1) || 'N/A'}</p>
            <p className="text-xs text-slate-700 mt-2">/100 • {section.total_score >= 70 ? 'CRITICAL' : section.total_score >= 50 ? 'ELEVATED' : 'LOW'} RISK</p>
          </div>
        </div>

        {/* Component Details Table */}
        {calc?.component_details && calc.component_details.length > 0 && (
          <div>
            <h4 className="text-sm font-bold text-[#0B1F33] mb-2">Component Scoring Details (All Factors)</h4>
            <div className="overflow-x-auto text-xs">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-slate-100 border-b-2 border-[#D0D7DE]">
                    <th className="text-left p-2 font-bold">Factor</th>
                    <th className="text-left p-2 font-bold">Component</th>
                    <th className="text-center p-2 font-bold">Score</th>
                    <th className="text-center p-2 font-bold">Weight %</th>
                    <th className="text-center p-2 font-bold">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {calc.component_details.map((factor: any, fidx: number) => (
                    <React.Fragment key={fidx}>
                      {factor.components?.map((comp: any, cidx: number) => (
                        <tr key={`${fidx}-${cidx}`} className="border-b border-[#D0D7DE]">
                          {cidx === 0 && (
                            <td rowSpan={factor.components.length} className="p-2 font-bold text-[#0B1F33] align-top bg-slate-50">
                              {factor.factor}
                            </td>
                          )}
                          <td className="p-2">{comp.name}</td>
                          <td className="p-2 text-center font-bold text-[#D83933]">{comp.score?.toFixed(1)}</td>
                          <td className="p-2 text-center">{comp.weight?.toFixed(1)}</td>
                          <td className="p-2 text-center font-bold">{comp.weighted_result?.toFixed(2)}</td>
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Factor Summary Table */}
        {calc?.factor_summary && calc.factor_summary.length > 0 && (
          <div>
            <h4 className="text-sm font-bold text-[#0B1F33] mb-2">Factor Aggregation Summary</h4>
            <div className="overflow-x-auto text-xs">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-slate-100 border-b-2 border-[#D0D7DE]">
                    <th className="text-left p-2 font-bold">Factor</th>
                    <th className="text-center p-2 font-bold">Subtotal</th>
                    <th className="text-center p-2 font-bold">% of Score</th>
                  </tr>
                </thead>
                <tbody>
                  {calc.factor_summary.map((f: any, idx: number) => (
                    <tr key={idx} className="border-b border-[#D0D7DE]">
                      <td className="p-2 font-bold text-[#0B1F33]">{f.factor}</td>
                      <td className="p-2 text-center font-bold text-[#D83933]">{f.subtotal?.toFixed(2)}</td>
                      <td className="p-2 text-center">{f.percentage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Adjustments */}
        {calc?.adjustments && calc.adjustments.length > 0 && (
          <div>
            <h4 className="text-sm font-bold text-[#0B1F33] mb-2">Adjustments Applied</h4>
            <div className="overflow-x-auto text-xs">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-slate-100 border-b-2 border-[#D0D7DE]">
                    <th className="text-left p-2 font-bold">Type</th>
                    <th className="text-center p-2 font-bold">Points</th>
                    <th className="text-left p-2 font-bold">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {calc.adjustments.map((a: any, idx: number) => (
                    <tr key={idx} className="border-b border-[#D0D7DE]">
                      <td className="p-2 font-bold">{a.type}</td>
                      <td className={`p-2 text-center font-bold ${a.points > 0 ? 'text-[#D83933]' : a.points < 0 ? 'text-[#0076D6]' : ''}`}>
                        {a.points > 0 ? '+' : ''}{a.points?.toFixed(2)}
                      </td>
                      <td className="p-2">{a.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Calculation Ledger */}
        {calc?.calculation_steps && (
          <div className="p-3 bg-slate-50 rounded border border-[#D0D7DE]">
            <h4 className="text-[9px] font-bold text-slate-600 uppercase mb-3">Calculation Ledger</h4>
            <div className="space-y-2 text-xs">
              {calc.calculation_steps.map((step: any, idx: number) => (
                <div key={idx} className="flex justify-between">
                  <span className="text-slate-700">{step.step}. {step.description}</span>
                  <span className="font-bold text-[#0B1F33]">{step.value?.toFixed(2)}</span>
                </div>
              ))}
              <div className="border-t border-slate-300 pt-2 mt-2 flex justify-between font-bold">
                <span>Final Score (capped at 100)</span>
                <span className="text-[#D83933] text-sm">{calc.final_score?.toFixed(2)}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Risk Indicators Table
  if (type?.includes('risk indicator')) {
    return (
      <div className="space-y-3">
        {section.indicators?.map((ind: any, idx: number) => (
          <div key={idx} className="p-3 border border-[#D0D7DE] rounded">
            <div className="flex items-start justify-between mb-2">
              <p className="text-sm font-bold text-[#0B1F33]">{ind.indicator}</p>
              {ind.present && <span className="text-[#D83933] font-bold text-xs">🚩 PRESENT</span>}
            </div>
            <p className="text-xs text-slate-700 mb-2">{ind.evidence}</p>
            <p className="text-[8px] text-slate-500 font-mono">Authority: {ind.authority}</p>
          </div>
        ))}
      </div>
    );
  }

  // Default: Display as JSON
  return (
    <div className="text-xs">
      <pre className="bg-slate-50 p-3 rounded border border-[#D0D7DE] overflow-x-auto max-h-96">
        {JSON.stringify(section, null, 2)}
      </pre>
    </div>
  );
}
