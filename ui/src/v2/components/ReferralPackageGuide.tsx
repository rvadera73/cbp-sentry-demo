import React, { useState } from 'react';
import { ChevronDown, BookOpen } from 'lucide-react';

export function ReferralPackageGuide() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-blue-50 border border-blue-300 rounded-sm p-4 text-[9px]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center space-x-2 font-bold text-blue-900 w-full hover:bg-blue-100 p-2 rounded transition-colors"
      >
        <BookOpen className="w-4 h-4" />
        <span>REFERRAL PACKAGE STRUCTURE GUIDE</span>
        <ChevronDown
          className={`w-4 h-4 ml-auto transition-transform ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      {expanded && (
        <div className="mt-3 space-y-4 text-blue-900">
          {/* Purpose Section */}
          <div className="bg-white rounded p-3 border-l-4 border-blue-500">
            <h4 className="font-bold mb-1">PURPOSE: THE NARRATIVE</h4>
            <p className="leading-tight">
              The <strong>narrative is an executive summary</strong> that synthesizes all investigative data
              into a coherent story for CBP/DHS officers. It answers three questions:
            </p>
            <ul className="mt-2 space-y-1 ml-3">
              <li>✓ <strong>WHY</strong> is this shipment high-risk?</li>
              <li>✓ <strong>WHAT</strong> fraud pattern is suspected?</li>
              <li>✓ <strong>WHAT ACTION</strong> should CBP take? (EXAMINE, REFER, etc.)</li>
            </ul>
          </div>

          {/* Three-Horizon Model */}
          <div className="bg-white rounded p-3 border-l-4 border-amber-500">
            <h4 className="font-bold mb-2">THREE-HORIZON RISK MODEL (H1+H2+H3=Total)</h4>
            <div className="space-y-2">
              <div>
                <p className="font-bold text-amber-700">H1: CORRIDOR RISK (0-40 pts) — MACRO</p>
                <p className="text-slate-700">
                  Trade route analysis. Which lane? Are AD/CVD duties in play? Example: CN→VN→US is
                  high-risk for tariff evasion.
                </p>
                <p className="text-[8px] text-slate-600 mt-1">
                  <strong>Authority:</strong> 19 USC § 1516a (tariff duty evasion)
                </p>
              </div>
              <div>
                <p className="font-bold text-amber-700">H2: PRE-MANIFEST INTELLIGENCE (0-35 pts) — MESO</p>
                <p className="text-slate-700">
                  Document analysis. ISF Element 9 mismatch? Vessel dwell anomalies? Invoice inconsistencies?
                </p>
                <p className="text-[8px] text-slate-600 mt-1">
                  <strong>Authority:</strong> 19 CFR Part 149 (ISF filing requirements)
                </p>
              </div>
              <div>
                <p className="font-bold text-amber-700">H3: NETWORK INTELLIGENCE (0-25 pts) — MICRO</p>
                <p className="text-slate-700">
                  Entity resolution. Shared directors? Shell companies? Supply chain opacity?
                </p>
                <p className="text-[8px] text-slate-600 mt-1">
                  <strong>Authority:</strong> 19 USC § 1581 (entry denial)
                </p>
              </div>
            </div>
          </div>

          {/* 14 Sections */}
          <div className="bg-white rounded p-3 border-l-4 border-green-500">
            <h4 className="font-bold mb-2">14 STATUTORY SECTIONS (EAPA Structure)</h4>
            <table className="w-full text-[8px] border-collapse">
              <tbody>
                <tr className="border-b border-slate-200">
                  <td className="font-bold py-1">Section 3-1</td>
                  <td className="py-1">Shipment Identification</td>
                  <td className="text-slate-600">What is being shipped?</td>
                </tr>
                <tr className="border-b border-slate-200">
                  <td className="font-bold py-1">Section 3-2</td>
                  <td className="py-1">Line Items</td>
                  <td className="text-slate-600">Invoice details</td>
                </tr>
                <tr className="border-b border-slate-200">
                  <td className="font-bold py-1">Section 3-3</td>
                  <td className="py-1">AIS Routing History</td>
                  <td className="text-slate-600">How did it travel?</td>
                </tr>
                <tr className="border-b border-slate-200">
                  <td className="font-bold py-1">Section 3-4</td>
                  <td className="py-1">Parties & Roles</td>
                  <td className="text-slate-600">Who is involved?</td>
                </tr>
                <tr className="border-b border-slate-200">
                  <td className="font-bold py-1">Section 3-5</td>
                  <td className="py-1">Entity Ownership Chain</td>
                  <td className="text-slate-600">Corporate structure (shell detection)</td>
                </tr>
                <tr className="border-b border-slate-200">
                  <td className="font-bold py-1">3-6 to 3-11</td>
                  <td className="py-1">Investigation Findings</td>
                  <td className="text-slate-600">Detailed evidence & analysis</td>
                </tr>
                <tr className="border-b border-slate-200">
                  <td className="font-bold py-1">Section 3-12</td>
                  <td className="py-1">Risk Score Breakdown</td>
                  <td className="text-slate-600">H1/H2/H3 components</td>
                </tr>
                <tr>
                  <td className="font-bold py-1">Section 3-13</td>
                  <td className="py-1">What-If Scenarios</td>
                  <td className="text-slate-600">Counterfactuals ("if evidence clears...")</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Example Narrative */}
          <div className="bg-white rounded p-3 border-l-4 border-purple-500">
            <h4 className="font-bold mb-2">EXAMPLE NARRATIVE STRUCTURE</h4>
            <div className="bg-slate-50 p-2 rounded font-mono text-[7px] leading-relaxed space-y-1">
              <p>
                <strong>CASE:</strong> EAPA-SHP-0002 | <strong>RISK:</strong> 95/100 (HIGH)
              </p>
              <p>
                <strong>SUBJECT:</strong> Da Nang Industrial (VN) → Atlantic Trading Partners (US)
              </p>
              <p className="border-t border-slate-300 pt-1">
                <strong>EXECUTIVE SUMMARY:</strong> Investigation reveals systematic transshipment evasion.
                Shipper falsely declares Vietnamese origin for steel coil that originates in restricted
                Chinese manufacturing base. Vessel routing anomalies (2.1d dwell vs 2.5d baseline) at Singapore
                transshipment hub. Supply chain exhibits shell company layering (HK holding company, no
                independent operations).
              </p>
              <p className="border-t border-slate-300 pt-1">
                <strong>H1 CORRIDOR (38/40):</strong> VN→US lane exhibits high AD/CVD duty incentive (374%
                anti-dumping on CN-origin steel). Prior EAPA determinations on similar corridor patterns.
              </p>
              <p className="border-t border-slate-300 pt-1">
                <strong>H2 MANIFEST (17/35):</strong> ISF Element 9 mismatch. Container labeled "Vietnam
                supplier" but AIS tracking places vessel at restricted Chinese port 14 days before U.S. arrival.
              </p>
              <p className="border-t border-slate-300 pt-1">
                <strong>H3 NETWORK (40/25):</strong> Senzing detects shared director between shipper and HK
                holding company (no independent operations). Pattern consistent with integrated transshipment
                scheme.
              </p>
              <p className="border-t border-slate-300 pt-1">
                <strong>RECOMMENDATION:</strong> EXAMINE ON ARRIVAL per 19 USC § 1516a. Recommend NTC referral
                for EAPA investigation.
              </p>
            </div>
          </div>

          {/* Key Takeaways */}
          <div className="bg-white rounded p-3 border-l-4 border-red-500">
            <h4 className="font-bold mb-2">KEY TAKEAWAYS</h4>
            <ul className="space-y-1">
              <li>
                ✓ <strong>Narrative ≠ sections.</strong> Narrative is a <strong>synthesis</strong> — it pulls the
                most compelling evidence from all 14 sections.
              </li>
              <li>
                ✓ <strong>H1+H2+H3 logic.</strong> Each horizon targets different fraud indicators. A case weak in
                H1 but strong in H3 might still trigger a referral.
              </li>
              <li>
                ✓ <strong>What-If scenarios matter.</strong> They show what would need to happen (factory
                certification, ISF amendment, director verification) to reduce risk.
              </li>
              <li>
                ✓ <strong>Entity graph is critical.</strong> Supply chain opacity (layers without independent
                operations, shared directors) is often the strongest H3 signal.
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
