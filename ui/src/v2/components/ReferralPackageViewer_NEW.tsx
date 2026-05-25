import React, { useState, useEffect } from 'react';
import { Download, AlertCircle, Loader } from 'lucide-react';

interface ReferralPackageViewerProps {
  shipmentId: string;
  caseId?: string;
  selectedCase?: any;
}

export function ReferralPackageViewerNew({
  shipmentId,
  caseId,
  selectedCase,
}: ReferralPackageViewerProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [referralData, setReferralData] = useState<any>(null);

  // Fetch referral package on component mount
  useEffect(() => {
    const fetchReferralPackage = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/referral/${shipmentId}`);

        if (!response.ok) {
          throw new Error(`Failed to generate referral package: ${response.statusText}`);
        }

        const data = await response.json();

        if (data && data.sections) {
          setReferralData(data);
          setLoading(false);
        } else if (data.error) {
          throw new Error(data.error);
        } else {
          throw new Error('Invalid referral package data');
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMsg);
        console.error('Error fetching referral package:', err);
        setLoading(false);
      }
    };

    if (shipmentId) {
      fetchReferralPackage();
    }
  }, [shipmentId]);

  const handleExportPDF = async () => {
    if (!referralData) return;

    setExporting(true);
    try {
      // Generate HTML content for export
      const htmlContent = `
        <html>
          <head>
            <title>CBP-EAPA-Referral-${caseId || shipmentId}</title>
            <style>
              body { font-family: Arial, sans-serif; margin: 20px; }
              h1 { color: #0B1F33; border-bottom: 2px solid #005EA2; padding-bottom: 10px; }
              .section { margin: 20px 0; page-break-inside: avoid; }
              .high-risk { color: #D83933; font-weight: bold; }
              .medium-risk { color: #FFBE2E; font-weight: bold; }
              table { width: 100%; border-collapse: collapse; margin: 10px 0; }
              th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
              th { background-color: #F0F4F8; }
            </style>
          </head>
          <body>
            <h1>CBP EAPA Referral Package</h1>
            <div class="section">
              <h2>Case Information</h2>
              <p><strong>Risk Score:</strong> <span class="high-risk">${referralData.risk_score}/100</span></p>
              <p><strong>Recommendation:</strong> ${referralData.recommendation}</p>
            </div>
            <p style="text-align: center; margin-top: 40px; font-size: 10px; color: #999;">
              Generated: ${new Date().toLocaleString()} | Authority: 19 USC § 1516a
            </p>
          </body>
        </html>
      `;

      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `CBP-EAPA-Referral-${caseId || shipmentId}-${new Date().toISOString().split('T')[0]}.html`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error exporting:', error);
      setError('Failed to export PDF');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#F7F9FC]">
      {/* Header */}
      <div className="bg-white border-b border-[#D0D7DE] px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-[#0B1F33]">CBP REFERRAL PACKAGE</h2>
            <p className="text-xs text-slate-500 font-mono">
              {referralData?.shipment?.origin_country}→{referralData?.shipment?.destination_country}
            </p>
          </div>
          <div className="flex items-center space-x-4">
            {referralData && (
              <div className="text-right">
                <div className="text-xs text-slate-500 font-mono mb-1">RISK SCORE</div>
                <div className="text-2xl font-bold text-[#D83933]">
                  {referralData.risk_score}/100
                </div>
              </div>
            )}
            <button
              onClick={handleExportPDF}
              disabled={!pdfUrl || exporting || loading}
              className="px-4 py-2 bg-[#0076D6] hover:bg-[#005EA2] disabled:opacity-50 text-white text-[9px] font-bold rounded-sm flex items-center space-x-2 transition-colors"
            >
              <Download className="w-3 h-3" />
              <span>{exporting ? 'EXPORTING...' : 'EXPORT PDF'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex-1 flex items-center justify-center bg-white">
          <div className="flex flex-col items-center space-y-3">
            <Loader className="w-8 h-8 text-[#005EA2] animate-spin" />
            <p className="text-sm text-slate-600 font-medium">Generating referral package...</p>
            <p className="text-xs text-slate-500">This may take a moment on first load</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="flex-1 flex items-center justify-center bg-white">
          <div className="flex flex-col items-center space-y-3 max-w-md">
            <AlertCircle className="w-8 h-8 text-[#D83933]" />
            <p className="text-sm text-[#D83933] font-medium">Failed to generate referral package</p>
            <p className="text-xs text-slate-600 text-center">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-xs font-bold rounded-sm transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Referral Package Content */}
      {!loading && !error && referralData && (
        <div className="flex-1 overflow-y-auto bg-white">
          <div className="max-w-4xl mx-auto p-8">
            {/* Case Information */}
            <div className="mb-8 pb-6 border-b border-slate-200">
              <h3 className="text-sm font-bold text-[#0B1F33] mb-4">CASE INFORMATION</h3>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <p className="text-slate-500">Entity</p>
                  <p className="font-mono font-bold text-[#0B1F33]">{referralData.sections?.entity_parties?.exporter || 'Unknown'}</p>
                </div>
                <div>
                  <p className="text-slate-500">Commodity</p>
                  <p className="font-mono font-bold text-[#0B1F33]">{referralData.sections?.commodity_analysis?.commodity || 'Unknown'}</p>
                </div>
                <div>
                  <p className="text-slate-500">Corridor</p>
                  <p className="font-mono font-bold text-[#0B1F33]">{referralData.sections?.corridor_risk?.trade_lane || 'Unknown'}</p>
                </div>
                <div>
                  <p className="text-slate-500">Risk Assessment</p>
                  <p className={`font-mono font-bold ${referralData.risk_score >= 80 ? 'text-red-600' : referralData.risk_score >= 50 ? 'text-amber-600' : 'text-green-600'}`}>
                    {referralData.risk_score >= 80 ? 'HIGH' : referralData.risk_score >= 50 ? 'MEDIUM' : 'LOW'}
                  </p>
                </div>
              </div>
            </div>

            {/* Score Components */}
            <div className="mb-8 pb-6 border-b border-slate-200">
              <h3 className="text-sm font-bold text-[#0B1F33] mb-4">RISK SCORE BREAKDOWN</h3>
              <div className="space-y-2 text-xs">
                {referralData.sections?.section_3_12_score_breakdown?.components?.map((comp: any, idx: number) => (
                  <div key={idx} className="flex justify-between items-center p-2 bg-slate-50 rounded">
                    <span className="text-slate-600">{comp.name}</span>
                    <span className="font-bold text-[#0B1F33]">{comp.score?.toFixed(1) || 0}/100</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Key Findings */}
            {referralData.sections?.section_3_11_risk_indicators?.indicators && (
              <div className="mb-8 pb-6 border-b border-slate-200">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">RISK INDICATORS</h3>
                <div className="space-y-2 text-xs">
                  {referralData.sections.section_3_11_risk_indicators.indicators.map((indicator: any, idx: number) => (
                    indicator.present && (
                      <div key={idx} className="p-3 bg-red-50 border border-red-200 rounded">
                        <p className="font-bold text-red-900">{indicator.indicator}</p>
                        <p className="text-red-700 text-[11px] mt-1">{indicator.evidence}</p>
                      </div>
                    )
                  ))}
                </div>
              </div>
            )}

            {/* Recommendation */}
            <div className={`p-4 rounded-sm ${referralData.recommendation === 'EXAMINE' ? 'bg-red-50 border border-red-300' : 'bg-amber-50 border border-amber-300'}`}>
              <p className={`text-xs font-bold ${referralData.recommendation === 'EXAMINE' ? 'text-red-900' : 'text-amber-900'}`}>
                RECOMMENDED ACTION: {referralData.recommendation}
              </p>
              <p className={`text-[11px] mt-2 ${referralData.recommendation === 'EXAMINE' ? 'text-red-800' : 'text-amber-800'}`}>
                {referralData.recommendation === 'EXAMINE' && 'Schedule examination on arrival. Initiate EAPA investigation per 19 USC § 1516a.'}
                {referralData.recommendation === 'REVIEW' && 'Flag for officer review. Monitor for additional indicators before examination.'}
                {referralData.recommendation === 'CLEAR' && 'No examination required at this time. May be subject to periodic review.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      {!loading && !error && referralData && (
        <div className="bg-white border-t border-[#D0D7DE] px-6 py-3 text-[8px] text-slate-500 font-mono flex justify-between">
          <span>CBP EAPA Referral Package</span>
          <span>{new Date().toLocaleDateString()}</span>
        </div>
      )}
    </div>
  );
}
