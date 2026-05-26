import React, { useMemo } from 'react';
import { AlertCircle } from 'lucide-react';

interface Entity {
  entity_id: string | number;
  name: string;
  country: string;
  entity_type: string;
  role: string;
  confidence: number;
  relationships?: Array<{
    type: string;
    target: string;
    confidence: number;
  }>;
  data_source?: string;
}

interface EntityGraphProps {
  chain?: Entity[];
  parties?: Array<{ entity: string; role: string; country: string }>;
}

export function EntityRelationshipGraph({ chain, parties }: EntityGraphProps) {
  const nodes = useMemo(() => {
    if (!chain || !Array.isArray(chain) || chain.length === 0) return [];

    // Filter out entities without required fields
    const validChain = chain.filter(e => e && e.name && e.entity_type);
    if (validChain.length === 0) return [];

    // Calculate positions in a hierarchical layout (top-down, centered)
    const nodeWidth = 140;
    const nodeHeight = 75;
    const xGap = 200;
    const yGap = 140;

    // Group by entity type for better visualization
    const manufacturers = validChain.filter(e => e.entity_type?.toUpperCase().includes('MANUFACTURER'));
    const holdings = validChain.filter(e => e.entity_type?.toUpperCase().includes('HOLDING'));
    const shippers = validChain.filter(e => e.entity_type?.toUpperCase().includes('SHIPPER') && !e.role?.toUpperCase().includes('CONSIGNEE'));
    const consignees = validChain.filter(e => e.role?.toUpperCase().includes('CONSIGNEE') || e.entity_type?.toUpperCase().includes('IMPORTER'));

    const rows = [manufacturers, holdings, shippers, consignees];
    const nodes: any[] = [];
    const centerX = 400;

    rows.forEach((row, rowIdx) => {
      if (row.length === 0) return;

      row.forEach((entity, colIdx) => {
        const totalInRow = row.length;
        const startX = centerX - (totalInRow * xGap) / 2 + colIdx * xGap;

        nodes.push({
          id: String(entity.entity_id),
          ...entity,
          x: startX,
          y: rowIdx * yGap + 30,
          width: nodeWidth,
          height: nodeHeight,
        });
      });
    });

    return nodes;
  }, [chain]);

  const getEntityColor = (type: string) => {
    switch (type?.toUpperCase()) {
      case 'MANUFACTURER':
      case 'MANUFACTURER_SUPPLIER':
        return '#10B981'; // Green
      case 'HOLDING_COMPANY':
      case 'INTERMEDIARY':
        return '#F59E0B'; // Amber (risky)
      case 'SHIPPER':
        return '#3B82F6'; // Blue
      case 'CONSIGNEE':
      case 'IMPORTER':
        return '#8B5CF6'; // Purple
      default:
        return '#6B7280'; // Gray
    }
  };

  const getRiskLevel = (entity: Entity) => {
    // Shell company indicators: intermediary with no manufacturing capacity, director shared
    const isIntermediatary = entity.entity_type?.toUpperCase().includes('INTERMEDIARY');
    const isHolding = entity.entity_type?.toUpperCase().includes('HOLDING');
    const hasSharedDirector = entity.relationships?.some(r => r.type === 'DIRECTOR_SHARED');

    if ((isIntermediatary || isHolding) && hasSharedDirector) return 'CRITICAL';
    if (isIntermediatary || isHolding) return 'HIGH';
    return 'NORMAL';
  };

  if (nodes.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-50 rounded-sm border border-dashed border-slate-300">
        <p className="text-sm text-slate-500">No entity chain data available</p>
      </div>
    );
  }

  // Calculate SVG dimensions based on content
  const maxX = Math.max(...nodes.map(n => n.x + n.width), 800);
  const maxY = Math.max(...nodes.map(n => n.y + n.height), 400);
  const svgWidth = Math.min(1200, maxX + 40);
  const svgHeight = Math.min(600, maxY + 40);

  return (
    <div className="w-full bg-white border border-[#D0D7DE] rounded-sm p-4">
      <h3 className="text-sm font-bold text-[#0B1F33] mb-3 uppercase">ENTITY SUPPLY CHAIN TOPOLOGY</h3>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mb-4 text-[8px]">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: '#10B981' }}></div>
          <span>Manufacturer</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: '#F59E0B' }}></div>
          <span>Intermediary (Risk)</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: '#3B82F6' }}></div>
          <span>Shipper</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: '#8B5CF6' }}></div>
          <span>Consignee</span>
        </div>
        <div className="flex items-center space-x-2">
          <AlertCircle className="w-3 h-3 text-red-600" />
          <span>Shell Company Flag</span>
        </div>
      </div>

      {/* SVG Graph */}
      <div className="overflow-x-auto border border-slate-200 rounded-sm bg-slate-50">
        <svg width={svgWidth} height={svgHeight} className="min-w-full">
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 10 3, 0 6" fill="#6B7280" />
            </marker>
            <marker
              id="arrowhead-risk"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 10 3, 0 6" fill="#DC2626" />
            </marker>
          </defs>

          {/* Relationship arrows */}
          {nodes.map((node, idx) => {
            if (idx >= nodes.length - 1) return null;
            const nextNode = nodes[idx + 1];
            const relationships = node.relationships || [];
            const isRiskRelationship = relationships.some((r: any) =>
              r.type === 'DIRECTOR_SHARED' || r.type === 'OWNED_BY'
            );

            return (
              <g key={`arrow-${idx}`}>
                <line
                  x1={node.x + node.width}
                  y1={node.y + node.height / 2}
                  x2={nextNode.x}
                  y2={nextNode.y + nextNode.height / 2}
                  stroke={isRiskRelationship ? '#DC2626' : '#6B7280'}
                  strokeWidth="2"
                  markerEnd={isRiskRelationship ? 'url(#arrowhead-risk)' : 'url(#arrowhead)'}
                  strokeDasharray={isRiskRelationship ? '5,5' : 'none'}
                />
                {relationships.length > 0 && (
                  <text
                    x={(node.x + node.width + nextNode.x) / 2}
                    y={(node.y + node.height / 2 + nextNode.y + nextNode.height / 2) / 2 - 5}
                    fontSize="10"
                    fill="#666"
                    textAnchor="middle"
                    className="pointer-events-none"
                  >
                    {relationships[0].type.replace(/_/g, ' ')}
                  </text>
                )}
              </g>
            );
          })}

          {/* Entity nodes */}
          {nodes.map((node) => {
            const riskLevel = getRiskLevel(node);
            const borderColor =
              riskLevel === 'CRITICAL'
                ? '#DC2626'
                : riskLevel === 'HIGH'
                ? '#F59E0B'
                : '#D0D7DE';
            const borderWidth = riskLevel === 'CRITICAL' ? 3 : 2;

            return (
              <g key={`node-${node.id}`}>
                {/* Node background */}
                <rect
                  x={node.x}
                  y={node.y}
                  width={node.width}
                  height={node.height}
                  fill={getEntityColor(node.entity_type)}
                  fillOpacity="0.15"
                  stroke={borderColor}
                  strokeWidth={borderWidth}
                  rx="4"
                />

                {/* Risk flag */}
                {riskLevel === 'CRITICAL' && (
                  <circle
                    cx={node.x + node.width - 8}
                    cy={node.y + 8}
                    r="6"
                    fill="#DC2626"
                  />
                )}

                {/* Entity name */}
                <text
                  x={node.x + node.width / 2}
                  y={node.y + 20}
                  fontSize="11"
                  fontWeight="bold"
                  textAnchor="middle"
                  fill="#1F2937"
                  className="pointer-events-none"
                >
                  {(node.name?.length || 0) > 18
                    ? (node.name || '').substring(0, 15) + '...'
                    : (node.name || 'N/A')}
                </text>

                {/* Entity type & country */}
                <text
                  x={node.x + node.width / 2}
                  y={node.y + 38}
                  fontSize="9"
                  textAnchor="middle"
                  fill="#6B7280"
                  className="pointer-events-none"
                >
                  {(node.entity_type || '').replace(/_/g, ' ')}
                </text>

                <text
                  x={node.x + node.width / 2}
                  y={node.y + 52}
                  fontSize="9"
                  textAnchor="middle"
                  fill="#6B7280"
                  className="pointer-events-none"
                >
                  {node.country}
                </text>

                {/* Confidence */}
                <text
                  x={node.x + node.width / 2}
                  y={node.y + node.height - 5}
                  fontSize="8"
                  textAnchor="middle"
                  fill="#059669"
                  fontWeight="bold"
                  className="pointer-events-none"
                >
                  {Math.round(node.confidence * 100)}% conf
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Risk Analysis */}
      <div className="mt-4 space-y-2 text-[9px]">
        {nodes.map((node) => {
          const riskLevel = getRiskLevel(node);
          if (riskLevel === 'NORMAL') return null;

          const hasSharedDirector = node.relationships?.some(
            (r: any) => r.type === 'DIRECTOR_SHARED'
          );
          const isIntermediaryOrHolding =
            node.entity_type?.toUpperCase().includes('INTERMEDIARY') ||
            node.entity_type?.toUpperCase().includes('HOLDING');

          return (
            <div
              key={`risk-${node.id}`}
              className={`p-2 rounded border-l-2 ${
                riskLevel === 'CRITICAL'
                  ? 'bg-red-50 border-red-400 text-red-900'
                  : 'bg-amber-50 border-amber-400 text-amber-900'
              }`}
            >
              <p className="font-bold">
                {riskLevel === 'CRITICAL' ? '🚩 CRITICAL: ' : '⚠️ HIGH: '}
                {node.name}
              </p>
              <ul className="mt-1 ml-4 space-y-0.5">
                {isIntermediaryOrHolding && (
                  <li>• Intermediary/holding entity without manufacturing capacity</li>
                )}
                {hasSharedDirector && (
                  <li>• Shared director(s) across borders without independent operations</li>
                )}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
