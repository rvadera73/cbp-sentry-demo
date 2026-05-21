import { Copy, Download, ExternalLink, Share2 } from 'lucide-react';
import { useEffect, useRef } from 'react';
import './CaseContextMenu.css';

interface CaseContextMenuProps {
  isOpen: boolean;
  x: number;
  y: number;
  shipmentId: string;
  manifestId?: string;
  riskScore: number;
  onClose: () => void;
  onCopyManifestId?: () => void;
  onCopyRiskScore?: () => void;
  onOpenNewTab?: () => void;
  onGenerateReferral?: () => void;
}

export default function CaseContextMenu({
  isOpen,
  x,
  y,
  shipmentId,
  manifestId,
  riskScore,
  onClose,
  onCopyManifestId,
  onCopyRiskScore,
  onOpenNewTab,
  onGenerateReferral,
}: CaseContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Adjust position if menu goes off-screen
  let menuX = x;
  let menuY = y;
  const offsetX = 8; // Distance from cursor
  const offsetY = 8;

  return (
    <div
      ref={menuRef}
      className="case-context-menu"
      style={{
        left: `${menuX + offsetX}px`,
        top: `${menuY + offsetY}px`,
      }}
      role="menu"
    >
      {manifestId && (
        <button
          className="context-menu-item"
          onClick={() => {
            onCopyManifestId?.();
            onClose();
          }}
          role="menuitem"
        >
          <Copy size={16} />
          <span>Copy Manifest ID</span>
          <span className="context-menu-code">{manifestId}</span>
        </button>
      )}

      <button
        className="context-menu-item"
        onClick={() => {
          onCopyRiskScore?.();
          onClose();
        }}
        role="menuitem"
      >
        <Copy size={16} />
        <span>Copy Risk Score</span>
        <span className="context-menu-code">{Math.round(riskScore)}/100</span>
      </button>

      <div className="context-menu-divider" role="separator" />

      {onOpenNewTab && (
        <button
          className="context-menu-item"
          onClick={() => {
            onOpenNewTab?.();
            onClose();
          }}
          role="menuitem"
        >
          <ExternalLink size={16} />
          <span>Open in New Tab</span>
        </button>
      )}

      {onGenerateReferral && (
        <button
          className="context-menu-item"
          onClick={() => {
            onGenerateReferral?.();
            onClose();
          }}
          role="menuitem"
        >
          <Download size={16} />
          <span>Generate Referral</span>
        </button>
      )}

      <div className="context-menu-divider" role="separator" />

      <button
        className="context-menu-item"
        onClick={() => {
          // Copy entire case info
          const caseInfo = `Manifest ID: ${manifestId || 'N/A'}
Risk Score: ${Math.round(riskScore)}/100
Shipment ID: ${shipmentId}`;
          navigator.clipboard.writeText(caseInfo);
          onClose();
        }}
        role="menuitem"
      >
        <Share2 size={16} />
        <span>Copy Case Summary</span>
      </button>
    </div>
  );
}
