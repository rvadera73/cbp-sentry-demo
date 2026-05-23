import { Entity } from '../../types/models';
import RiskBadge from './RiskBadge';
import { Package, Building2, Factory, Truck, Building, Anchor, Globe } from 'lucide-react';

interface EntityCardProps {
  entity: Entity;
  riskScore?: number;
  onClick?: () => void;
  selected?: boolean;
}

const entityTypeIcons: Record<string, React.ReactNode> = {
  SHIPPER: <Package size={20} />,
  CONSIGNEE: <Building2 size={20} />,
  MANUFACTURER: <Factory size={20} />,
  FREIGHT_FORWARDER: <Truck size={20} />,
  HOLDING_COMPANY: <Building size={20} />,
  VESSEL: <Anchor size={20} />
};

export default function EntityCard({
  entity,
  riskScore,
  onClick,
  selected = false
}: EntityCardProps) {
  const icon = entityTypeIcons[entity.entity_type] || <Building2 size={20} />;

  return (
    <div
      onClick={onClick}
      className={`p-3 rounded-lg border-2 transition-colors ${
        selected
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 hover:border-gray-300 cursor-pointer'
      } ${onClick ? 'hover:bg-gray-50' : ''}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-700 flex-shrink-0">{icon}</span>
          <div>
            <p className="font-semibold text-sm text-gray-900">{entity.label || entity.name}</p>
            <p className="text-xs text-gray-600">{entity.entity_type.replace(/_/g, ' ')}</p>
          </div>
        </div>
        {riskScore !== undefined && <RiskBadge score={riskScore} size="sm" showLabel={false} />}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-600 flex items-center gap-1">
          <Globe size={14} className="flex-shrink-0" />
          {entity.country}
        </span>
        {entity.senzing_confidence !== undefined && (
          <span className="text-xs font-mono bg-gray-100 px-2 py-1 rounded">
            Conf: {Math.round(entity.senzing_confidence * 100)}%
          </span>
        )}
      </div>
    </div>
  );
}
