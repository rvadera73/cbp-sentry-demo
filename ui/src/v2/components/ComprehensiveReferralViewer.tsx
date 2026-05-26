import React, { useState, useCallback } from 'react';
import { Download, MessageSquare, X, ChevronDown, ChevronUp, AlertCircle, CheckCircle } from 'lucide-react';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

interface Annotation {
  sectionId: string;
  text: string;
  timestamp: string;
  author: string;
}

interface ReferralPackage {
  referral_id: string;
  shipment_id: string;
  created_at: string;
  risk_score: number;
  risk_level: string;
  sections: Record<string, any>;
  risk_breakdown?: {
    final_score: number;
    components: Array<{
      component: string;
      score: number;
      weight: number;
      weighted_result: number;
    }>;
  };
}

function formatCellValue(val: any): string | React.ReactNode {
  if (val === null || val === undefined) {
    return '';
  }
  if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') {
    return String(val);
  }
  if (Array.isArray(val)) {
    return val.map(v => typeof v === 'string' ? v : String(v)).join(', ');
  }
  if (typeof val === 'object') {
    const entries = Object.entries(val);
    if (entries.length <= 3) {
      return entries.map(([k, v]) => `${k}: ${formatCellValue(v)}`).join(' | ');
    }
    return JSON.stringify(val, null, 2);
  }
  return String(val);
}

interface Props {
  referral: ReferralPackage;
  onAnnotationSave?: (annotations: Annotation[]) => void;
}

export function ComprehensiveReferralViewer({ referral, onAnnotationSave }: Props) {
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['section_3_1_shipment_identification']));
  const [activeAnnotationSection, setActiveAnnotationSection] = useState<string | null>(null);
  const [annotationText, setAnnotationText] = useState('');

  const toggleSection = useCallback((sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  }, [expandedSections]);

  const addAnnotation = useCallback((sectionId: string) => {
    if (!annotationText.trim()) return;

    const newAnnotation: Annotation = {
      sectionId,
      text: annotationText,
      timestamp: new Date().toISOString(),
      author: 'Current User',
    };

    const updated = [...annotations, newAnnotation];
    setAnnotations(updated);
    setAnnotationText('');
    setActiveAnnotationSection(null);

    if (onAnnotationSave) {
      onAnnotationSave(updated);
    }
  }, [annotationText, annotations, onAnnotationSave]);

  const removeAnnotation = useCallback((index: number) => {
    const updated = annotations.filter((_, i) => i !== index);
    setAnnotations(updated);
  }, [annotations]);

  const exportToPDF = async () => {
    const element = document.getElementById('referral-content');
    if (!element) return;

    try {
      // Save original state
      const originalExpanded = new Set(expandedSections);

      // Expand all sections for PDF
      const allSectionIds = new Set(sectionOrder.filter(id => referral.sections[id]));
      setExpandedSections(allSectionIds);

      // Wait for DOM to update
      await new Promise(resolve => setTimeout(resolve, 500));

      const canvas = await html2canvas(element, { scale: 2 });
      const pdf = new jsPDF('p', 'mm', 'a4');
      const imgData = canvas.toDataURL('image/png');
      const imgWidth = 210;
      const pageHeight = 295;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      while (heightLeft >= 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      pdf.save(`Referral-${referral.referral_id}.pdf`);

      // Restore original state
      setExpandedSections(originalExpanded);
    } catch (error) {
      console.error('PDF export failed:', error);
    }
  };

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
    'section_3_12_pattern_analysis',
    'section_3_13_enforcement_analysis',
    'section_3_14_conclusion_and_recommendation',
  ];

  const getSectionTitle = (sectionId: string): string => {
    const section = referral.sections[sectionId];
    return section?.title || sectionId.replace(/_/g, ' ').toUpperCase();
  };

  const getRiskColor = (score: number) => {
    if (score >= 85) return 'bg-red-100 text-red-800 border-red-300';
    if (score >= 70) return 'bg-orange-100 text-orange-800 border-orange-300';
    if (score >= 50) return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    return 'bg-green-100 text-green-800 border-green-300';
  };

  const getRiskLabel = (score: number) => {
    if (score >= 85) return 'CRITICAL';
    if (score >= 70) return 'HIGH';
    if (score >= 50) return 'MEDIUM';
    return 'LOW';
  };

  return (
    <div className="w-full h-full flex flex-col bg-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#0B1F33] to-[#003d7a] text-white p-6 sticky top-0 z-10">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold mb-2">COMPREHENSIVE CBP REFERRAL PACKAGE</h1>
            <p className="text-sm opacity-90">CSOP-BP-GS-26-0001 | Shipment: {referral.shipment_id}</p>
            <p className="text-sm opacity-90">Generated: {new Date(referral.created_at).toLocaleDateString()}</p>
          </div>

          <div className="flex items-center gap-4">
            {/* Risk Score Badge */}
            <div className={`rounded-lg p-4 border-2 ${getRiskColor(referral.risk_score)} text-center`}>
              <div className="text-3xl font-bold">{Math.round(referral.risk_score)}</div>
              <div className="text-xs font-bold mt-1">{getRiskLabel(referral.risk_score)}</div>
            </div>

            {/* Actions */}
            <button
              onClick={exportToPDF}
              className="px-4 py-2 bg-white text-[#0B1F33] font-bold rounded hover:bg-gray-100 flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              PDF Export
            </button>
          </div>
        </div>
      </div>

      {/* Main Content - Letter Size (8.5x11 inches) */}
      <div className="flex-1 overflow-y-auto bg-slate-100 p-4">
        <div id="referral-content" className="mx-auto p-8 bg-white" style={{ width: '8.5in', minHeight: '11in' }}>
          {/* Summary Card */}
          <div className="bg-[#F7F9FC] border-l-4 border-[#0B1F33] p-6 mb-6 rounded">
            <h2 className="text-lg font-bold text-[#0B1F33] mb-3">EXECUTIVE SUMMARY</h2>
            <p className="text-sm text-slate-700 mb-2">
              This comprehensive referral package analyzes 14 statutory sections of transshipment risk across documentation,
              commodity, routing, party, corridor, pattern, and temporal factors. The cumulative risk assessment of{' '}
              <span className="font-bold">{Math.round(referral.risk_score)}/100</span> indicates{' '}
              <span className="font-bold">{getRiskLabel(referral.risk_score)}</span> concern requiring appropriate CBP action.
            </p>
            <p className="text-xs text-slate-600 mt-2">
              ✓ Data-backed sections 3-1 through 3-10 | ✓ AI-synthesized sections 3-6, 3-7, 3-11, 3-14 | ✓ Full audit trail
            </p>
          </div>

          {/* Sections */}
          <div className="space-y-4">
            {sectionOrder.map((sectionId) => {
              const section = referral.sections[sectionId];
              if (!section) return null;

              const isExpanded = expandedSections.has(sectionId);
              const sectionAnnotations = annotations.filter((a) => a.sectionId === sectionId);

              return (
                <div key={sectionId} className="border border-[#D0D7DE] rounded-sm overflow-hidden bg-white">
                  {/* Section Header */}
                  <button
                    onClick={() => toggleSection(sectionId)}
                    className="w-full flex justify-between items-center bg-[#F7F9FC] hover:bg-[#E8EEF6] p-4 border-b border-[#D0D7DE] transition-colors"
                  >
                    <div className="flex items-center gap-3 text-left">
                      <div className="text-sm font-bold text-[#0B1F33]">{getSectionTitle(sectionId)}</div>
                      {sectionAnnotations.length > 0 && (
                        <span className="bg-blue-600 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
                          {sectionAnnotations.length}
                        </span>
                      )}
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-slate-600" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-slate-600" />
                    )}
                  </button>

                  {/* Section Content */}
                  {isExpanded && (
                    <div className="p-6 space-y-4">
                      {/* Data Content */}
                      <div className="prose prose-sm max-w-none">
                        {typeof section === 'string' ? (
                          <p className="text-sm text-slate-700 whitespace-pre-wrap">{section}</p>
                        ) : (
                          <div className="space-y-3">
                            {/* Render section data */}
                            {section.narrative && (
                              <div className="bg-slate-50 p-4 rounded border-l-4 border-blue-500">
                                <p className="text-sm text-slate-700 whitespace-pre-wrap">{section.narrative}</p>
                              </div>
                            )}

                            {section.pattern_narrative && (
                              <div className="bg-slate-50 p-4 rounded border-l-4 border-blue-500">
                                <p className="text-sm text-slate-700 whitespace-pre-wrap">{section.pattern_narrative}</p>
                              </div>
                            )}

                            {section.conclusion_narrative && (
                              <div className="bg-slate-50 p-4 rounded border-l-4 border-blue-500">
                                <p className="text-sm text-slate-700 whitespace-pre-wrap">{section.conclusion_narrative}</p>
                              </div>
                            )}

                            {section.trade_flow_narrative && (
                              <div className="bg-slate-50 p-4 rounded border-l-4 border-blue-500">
                                <p className="text-sm text-slate-700 whitespace-pre-wrap">{section.trade_flow_narrative}</p>
                              </div>
                            )}

                            {section.summary && (
                              <div className="bg-slate-50 p-4 rounded border-l-4 border-orange-500">
                                <p className="text-sm text-slate-700 whitespace-pre-wrap">{section.summary}</p>
                              </div>
                            )}

                            {/* Parties Table (Section 3-4) */}
                            {section.parties && Array.isArray(section.parties) && (
                              <table className="w-full text-xs border-collapse">
                                <thead>
                                  <tr className="bg-[#005EA2] text-white">
                                    <th className="border border-slate-300 px-2 py-2 text-left font-bold">PARTY NAME</th>
                                    <th className="border border-slate-300 px-2 py-2 text-left font-bold">ROLE</th>
                                    <th className="border border-slate-300 px-2 py-2 text-left font-bold">COUNTRY</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {section.parties.map((item: any, idx: number) => (
                                    <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                                      <td className="border border-slate-300 px-2 py-2 text-slate-700">{item.name}</td>
                                      <td className="border border-slate-300 px-2 py-2 text-slate-700">{item.role}</td>
                                      <td className="border border-slate-300 px-2 py-2 text-slate-700">{item.country}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            )}

                            {/* Routing History Table (Section 3-3) */}
                            {section.routing_events && Array.isArray(section.routing_events) && section.routing_events.length > 0 && (
                              <table className="w-full text-xs border-collapse">
                                <thead>
                                  <tr className="bg-[#005EA2] text-white">
                                    <th className="border border-slate-300 px-2 py-2 text-left font-bold">LOCATION</th>
                                    <th className="border border-slate-300 px-2 py-2 text-left font-bold">DATE</th>
                                    <th className="border border-slate-300 px-2 py-2 text-left font-bold">EVENT</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {section.routing_events.map((event: any, idx: number) => (
                                    <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                                      <td className="border border-slate-300 px-2 py-2">{event.location}</td>
                                      <td className="border border-slate-300 px-2 py-2">{event.date}</td>
                                      <td className="border border-slate-300 px-2 py-2">{event.event}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            )}

                            {/* Entity Ownership Chain Table (Section 3-5) */}
                            {section.chain && Array.isArray(section.chain) && (
                              <div className="space-y-3">
                                <table className="w-full text-xs border-collapse">
                                  <thead>
                                    <tr className="bg-[#005EA2] text-white">
                                      <th className="border border-slate-300 px-2 py-2 text-left font-bold">ENTITY NAME</th>
                                      <th className="border border-slate-300 px-2 py-2 text-left font-bold">TYPE</th>
                                      <th className="border border-slate-300 px-2 py-2 text-left font-bold">COUNTRY</th>
                                      <th className="border border-slate-300 px-2 py-2 text-left font-bold">CONFIDENCE</th>
                                      <th className="border border-slate-300 px-2 py-2 text-left font-bold">SOURCE</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {section.chain.map((entity: any, idx: number) => (
                                      <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                                        <td className="border border-slate-300 px-2 py-2 text-slate-700 font-semibold">{entity.name}</td>
                                        <td className="border border-slate-300 px-2 py-2 text-slate-700">{entity.type}</td>
                                        <td className="border border-slate-300 px-2 py-2 text-slate-700">{entity.country}</td>
                                        <td className="border border-slate-300 px-2 py-2 text-slate-700">{(entity.confidence * 100).toFixed(0)}%</td>
                                        <td className="border border-slate-300 px-2 py-2 text-slate-700 text-xs">{entity.data_source}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                                {section.chain.length > 0 && section.chain[0].relationships?.length > 0 && (
                                  <div className="bg-blue-50 p-3 rounded border border-blue-200 text-xs">
                                    <p className="font-bold text-blue-900 mb-2">RELATIONSHIPS:</p>
                                    {section.chain.map((entity: any, idx: number) =>
                                      entity.relationships?.map((rel: any, ridx: number) => (
                                        <div key={`${idx}-${ridx}`} className="text-blue-800">
                                          Level {idx + 1} → Level {idx + 2}: <span className="font-bold">{rel.type}</span> ({(rel.confidence * 100).toFixed(0)}%)
                                        </div>
                                      ))
                                    )}
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Risk Breakdown (Section 3-11) */}
                            {sectionId === 'section_3_11_risk_indicators' && referral.risk_breakdown && (
                              <div className="space-y-4">
                                {section.summary && (
                                  <div className="bg-slate-50 p-4 rounded border-l-4 border-orange-500">
                                    <h4 className="font-bold text-slate-800 mb-2 text-xs">RISK ANALYSIS SUMMARY:</h4>
                                    <p className="text-xs text-slate-700 whitespace-pre-wrap">{section.summary}</p>
                                  </div>
                                )}
                                <div className="space-y-3">
                                  <h4 className="font-bold text-slate-800 text-sm">FINAL RISK SCORE: {referral.risk_breakdown.final_score.toFixed(1)}/100</h4>
                                  <h5 className="font-bold text-slate-800 text-xs">COMPONENT BREAKDOWN (18 FACTORS):</h5>
                                  <table className="w-full text-xs border-collapse">
                                    <thead>
                                      <tr className="bg-orange-600 text-white">
                                        <th className="border border-slate-300 px-2 py-2 text-left">FACTOR</th>
                                        <th className="border border-slate-300 px-2 py-2 text-right">SCORE</th>
                                        <th className="border border-slate-300 px-2 py-2 text-right">WEIGHT</th>
                                        <th className="border border-slate-300 px-2 py-2 text-right">WEIGHTED</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {referral.risk_breakdown.components.map((comp: any, idx: number) => (
                                        <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                                          <td className="border border-slate-300 px-2 py-2">{comp.component}</td>
                                          <td className="border border-slate-300 px-2 py-2 text-right">{comp.score.toFixed(1)}</td>
                                          <td className="border border-slate-300 px-2 py-2 text-right">{(comp.weight * 100).toFixed(0)}%</td>
                                          <td className="border border-slate-300 px-2 py-2 text-right font-semibold">{comp.weighted_result.toFixed(1)}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                  <div className="mt-3 p-3 bg-orange-50 rounded border-l-4 border-orange-500">
                                    <p className="font-bold text-orange-900">FINAL RISK SCORE: {referral.risk_breakdown.final_score.toFixed(1)}/100</p>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Documents Table (Section 3-8) */}
                            {section.documents && Array.isArray(section.documents) && (
                              <table className="w-full text-xs border-collapse">
                                <thead>
                                  <tr className="bg-[#005EA2] text-white">
                                    <th className="border border-slate-300 px-2 py-2 text-left font-bold">TYPE</th>
                                    <th className="border border-slate-300 px-2 py-2 text-left font-bold">STATUS</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {section.documents.map((doc: any, idx: number) => (
                                    <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                                      <td className="border border-slate-300 px-2 py-2">{doc.type}</td>
                                      <td className="border border-slate-300 px-2 py-2">{doc.status}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            )}

                            {/* Suppliers Table (Section 3-10) */}
                            {section.suppliers && Array.isArray(section.suppliers) && section.suppliers.length > 0 && (
                              <table className="w-full text-xs border-collapse">
                                <thead>
                                  <tr className="bg-[#005EA2] text-white">
                                    <th className="border border-slate-300 px-2 py-2 text-left font-bold">SUPPLIER NAME</th>
                                    <th className="border border-slate-300 px-2 py-2 text-left font-bold">LOCATION</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {section.suppliers.map((supplier: any, idx: number) => (
                                    <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                                      <td className="border border-slate-300 px-2 py-2">{supplier.name}</td>
                                      <td className="border border-slate-300 px-2 py-2">{supplier.location}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            )}

                            {/* Element 9 / Document Consistency (Section 3-9) */}
                            {section.element9_mismatch !== undefined && (
                              <div className="bg-slate-50 p-3 rounded border-l-4 border-orange-500">
                                <p className="text-xs font-bold text-slate-800 mb-2">Element 9 Analysis:</p>
                                <p className="text-xs text-slate-700"><strong>Status:</strong> {section.element9_mismatch ? 'MISMATCH DETECTED' : 'CONSISTENT'}</p>
                                {section.declared_country && <p className="text-xs text-slate-700"><strong>Declared Origin:</strong> {section.declared_country}</p>}
                                {section.actual_country && <p className="text-xs text-slate-700"><strong>Actual Origin:</strong> {section.actual_country}</p>}
                                {section.confidence && <p className="text-xs text-slate-700"><strong>Confidence:</strong> {(section.confidence * 100).toFixed(0)}%</p>}
                              </div>
                            )}

                            {/* Enforcement References (Section 3-13) */}
                            {section.enforcement_references && (
                              <div className="bg-red-50 p-3 rounded border-l-4 border-red-500">
                                <p className="text-xs font-bold text-red-900 mb-1">LEGAL REFERENCES & PRIOR ENFORCEMENT:</p>
                                <p className="text-xs text-red-800">{section.enforcement_references}</p>
                              </div>
                            )}

                            {/* Pattern Analysis (Section 3-12) */}
                            {section.patterns && Array.isArray(section.patterns) && (
                              <div className="space-y-1">
                                <h4 className="font-bold text-slate-800 text-xs">BEHAVIORAL INDICATORS:</h4>
                                {section.patterns.map((pattern: string, idx: number) => (
                                  <p key={idx} className="text-xs text-slate-700 ml-3">• {pattern}</p>
                                ))}
                              </div>
                            )}

                            {/* Generic Tables/Lists */}
                            {section.items && Array.isArray(section.items) && (
                              <table className="w-full text-xs border-collapse">
                                <thead>
                                  <tr className="bg-[#005EA2] text-white">
                                    {Object.keys(section.items[0] || {}).map((key) => (
                                      <th key={key} className="border border-slate-300 px-2 py-2 text-left font-bold">
                                        {key.replace(/_/g, ' ').toUpperCase()}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {section.items.map((item: any, idx: number) => (
                                    <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                                      {Object.values(item).map((val: any, cidx: number) => (
                                        <td key={cidx} className="border border-slate-300 px-2 py-2 text-slate-700 text-sm">
                                          {formatCellValue(val)}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            )}

                            {/* Key-Value Pairs */}
                            {typeof section === 'object' && !section.items && !section.narrative && (
                              <div className="grid grid-cols-2 gap-3">
                                {Object.entries(section).map(([key, val]: [string, any]) => (
                                  <div key={key} className="text-sm">
                                    <label className="font-bold text-slate-700">{key.replace(/_/g, ' ')}:</label>
                                    <p className="text-slate-600 whitespace-pre-wrap">
                                      {formatCellValue(val)}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Annotations Section */}
                      <div className="border-t pt-4 mt-4">
                        {sectionAnnotations.length > 0 && (
                          <div className="space-y-2 mb-4">
                            {sectionAnnotations.map((ann, idx) => (
                              <div key={idx} className="bg-blue-50 border border-blue-200 rounded p-3 flex justify-between items-start gap-3">
                                <div>
                                  <p className="text-xs text-blue-700 font-bold mb-1">
                                    💬 Note • {new Date(ann.timestamp).toLocaleDateString()}
                                  </p>
                                  <p className="text-sm text-slate-700">{ann.text}</p>
                                </div>
                                <button
                                  onClick={() => removeAnnotation(idx)}
                                  className="text-slate-400 hover:text-red-600"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Add Annotation */}
                        {activeAnnotationSection === sectionId ? (
                          <div className="bg-slate-50 p-4 rounded border-2 border-blue-400">
                            <textarea
                              value={annotationText}
                              onChange={(e) => setAnnotationText(e.target.value)}
                              placeholder="Add annotation (notes won't affect risk score)..."
                              className="w-full p-2 border border-slate-300 rounded text-sm resize-none"
                              rows={3}
                            />
                            <div className="flex gap-2 mt-2">
                              <button
                                onClick={() => addAnnotation(sectionId)}
                                className="px-3 py-1 bg-blue-600 text-white text-xs font-bold rounded hover:bg-blue-700"
                              >
                                Save Note
                              </button>
                              <button
                                onClick={() => {
                                  setActiveAnnotationSection(null);
                                  setAnnotationText('');
                                }}
                                className="px-3 py-1 bg-slate-300 text-slate-700 text-xs font-bold rounded hover:bg-slate-400"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => setActiveAnnotationSection(sectionId)}
                            className="text-sm text-blue-600 hover:text-blue-700 font-bold flex items-center gap-1"
                          >
                            <MessageSquare className="w-4 h-4" />
                            Add Annotation
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Footer */}
          <div className="mt-8 pt-6 border-t border-[#D0D7DE] text-xs text-slate-600">
            <p className="font-bold text-slate-700 mb-2">DOCUMENT PROPERTIES</p>
            <p>Referral ID: {referral.referral_id}</p>
            <p>Generated: {new Date(referral.created_at).toLocaleString()}</p>
            <p>Annotations: {annotations.length}</p>
            <p className="mt-3 text-slate-500">
              This document contains analysis synthesized from CBP shipment data, import patterns, and risk modeling.
              Annotations are internal notes and do not affect the calculated risk score.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ComprehensiveReferralViewer;
