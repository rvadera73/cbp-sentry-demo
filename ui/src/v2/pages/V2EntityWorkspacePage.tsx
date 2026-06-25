import React, { useState } from 'react';
import { ArrowLeft, AlertTriangle, Network, Scale, Briefcase, TrendingUp, MoreVertical } from 'lucide-react';
import V2EntityResolutionPanel from '../components/V2EntityResolutionPanel';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';

interface RelatedEntity {
  entity_id: string;
  entity_name: string;
  risk_score: number;
  relationship: string;
}

interface V2EntityWorkspacePageProps {
  selectedEntityId?: string | null;
  setSelectedEntityId?: (id: string | null) => void;
  setActiveTab?: (tab: string) => void;
}

const FIXTURE_RELATED_ENTITIES: RelatedEntity[] = [
  { entity_id: 'ENT-GF-HK-001', entity_name: 'Greenfield Global Metals Holdings Ltd.', risk_score: 58, relationship: 'Owner' },
  { entity_id: 'ENT-GF-CN-001', entity_name: 'Guangdong Greenfield Aluminum Mfg.', risk_score: 52, relationship: 'Parent' },
  { entity_id: 'ENT-PAN-PAC-001', entity_name: 'Pan-Pacific Logistics, Inc.', risk_score: 38, relationship: 'Freight Fwd' },
  { entity_id: 'ENT-CTS-001', entity_name: 'China Trade Services', risk_score: 28, relationship: 'Registered Agent' },
  { entity_id: 'ENT-SP-US-001', entity_name: 'SunPath Energy Distributors LLC', risk_score: 52, relationship: 'Consignee' },
];

export default function V2EntityWorkspacePage({
  selectedEntityId,
  setSelectedEntityId,
  setActiveTab,
}: V2EntityWorkspacePageProps) {
  const [showActionsMenu, setShowActionsMenu] = useState(false);

  const handleBack = () => {
    setSelectedEntityId?.(null);
    setActiveTab?.('entities');
  };

  const handleViewRelated = (entityId: string) => {
    setSelectedEntityId?.(entityId);
    // Stay on entity-workspace, just reload with new entity
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#F7F9FC]">
      {/* Header with Back Button */}
      <div className={`${DESIGN.bgWhite} border-b ${DESIGN.borderColor} px-6 py-4 shadow-sm`}>
        <div className="flex items-center justify-between">
          <button
            onClick={handleBack}
            className="flex items-center space-x-2 px-3 py-1.5 hover:bg-slate-100 rounded text-xs font-bold text-[#0076D6] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Watchlist</span>
          </button>

          <button
            onClick={() => setShowActionsMenu(!showActionsMenu)}
            className="relative p-2 hover:bg-slate-100 rounded transition-colors"
            title="More actions"
          >
            <MoreVertical className="w-4 h-4 text-slate-600" />

            {showActionsMenu && (
              <div className="absolute right-0 top-full mt-2 bg-white border border-[#D0D7DE] rounded-sm shadow-lg z-50 w-48">
                <button className="w-full text-left px-4 py-2 hover:bg-slate-50 text-xs font-bold text-[#0B1F33]">
                  Export Profile
                </button>
                <button className="w-full text-left px-4 py-2 hover:bg-slate-50 text-xs font-bold text-[#0B1F33]">
                  Add to Manual Review
                </button>
                <button className="w-full text-left px-4 py-2 hover:bg-slate-50 text-xs font-bold text-[#0B1F33]">
                  Flag as False Positive
                </button>
              </div>
            )}
          </button>
        </div>
      </div>

      {/* Main Content with Sidebar */}
      <div className="flex-1 flex overflow-hidden gap-4 p-6">
        {/* Main Panel (75%) - Entity Intelligence */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white rounded-sm border border-[#D0D7DE] shadow-sm">
          <V2EntityResolutionPanel />
        </div>

        {/* Right Sidebar (25%) - Related Entities */}
        <div className="w-80 flex flex-col overflow-hidden bg-white rounded-sm border border-[#D0D7DE] shadow-sm">
          <div className="bg-[#F0F4F8] p-3 border-b border-[#D0D7DE]">
            <h3 className={`${TYPOGRAPHY.tableHeader}`}>RELATED ENTITIES</h3>
          </div>

          <div className="flex-1 overflow-y-auto">
            <div className="p-3 space-y-2">
              {FIXTURE_RELATED_ENTITIES.length > 0 ? (
                <>
                  {FIXTURE_RELATED_ENTITIES.map((entity, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleViewRelated(entity.entity_id)}
                      className="w-full text-left p-3 bg-slate-50 hover:bg-[#E3F2FD] rounded transition-colors border border-slate-200 hover:border-[#0076D6]"
                    >
                      <div className="flex items-start justify-between mb-1">
                        <span className="font-bold text-[#0B1F33] text-xs line-clamp-2">
                          {entity.entity_name}
                        </span>
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded text-white shrink-0 ${
                          entity.risk_score >= 50
                            ? 'bg-orange-600'
                            : entity.risk_score >= 30
                            ? 'bg-amber-600'
                            : 'bg-green-600'
                        }`}>
                          {entity.risk_score}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[8px] text-slate-600">
                          {entity.relationship}
                        </span>
                        <span className="text-[8px] text-[#0076D6] font-bold">→ Open</span>
                      </div>
                    </button>
                  ))}

                  {FIXTURE_RELATED_ENTITIES.length > 0 && (
                    <button className="w-full mt-3 px-3 py-2 bg-[#0076D6] hover:bg-[#005EA2] text-white rounded text-xs font-bold transition-colors">
                      View All Connected ({FIXTURE_RELATED_ENTITIES.length})
                    </button>
                  )}
                </>
              ) : (
                <div className={`text-center py-8 ${DESIGN.textGray}`}>
                  <p className="text-xs">No related entities</p>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar Footer - Quick Info */}
          <div className="border-t border-[#D0D7DE] p-3 bg-[#F7F9FC] space-y-2">
            <div>
              <span className="text-[9px] font-bold text-[#5C5C5C] uppercase">Confidence</span>
              <div className="w-full bg-slate-200 rounded-full h-2 mt-1">
                <div className="bg-[#0076D6] h-2 rounded-full" style={{ width: '92%' }}></div>
              </div>
              <span className="text-[8px] text-slate-600 mt-1 block">92% match confidence</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
