import { X } from 'lucide-react';
import './KeyboardHelpModal.css';

interface KeyboardHelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function KeyboardHelpModal({ isOpen, onClose }: KeyboardHelpModalProps) {
  if (!isOpen) return null;

  const shortcuts = [
    {
      group: 'Navigation',
      items: [
        { key: '↑ / ↓', description: 'Navigate case queue' },
        { key: 'Tab', description: 'Switch between tab sections' },
      ],
    },
    {
      group: 'Actions',
      items: [
        { key: 'E', description: 'Expand current tab fullscreen' },
        { key: 'Ctrl+P', description: 'Print referral package' },
        { key: 'Ctrl+E', description: 'Export referral package' },
      ],
    },
    {
      group: 'Help',
      items: [
        { key: '?', description: 'Show this help modal' },
        { key: 'Esc', description: 'Close modal' },
      ],
    },
  ];

  return (
    <div className="keyboard-help-backdrop" onClick={onClose}>
      <div className="keyboard-help-modal" onClick={(e) => e.stopPropagation()}>
        <div className="help-header">
          <h2>Keyboard Shortcuts</h2>
          <button className="help-close" onClick={onClose} aria-label="Close help">
            <X size={20} />
          </button>
        </div>

        <div className="help-content">
          {shortcuts.map((group) => (
            <div key={group.group} className="shortcut-group">
              <h3>{group.group}</h3>
              <div className="shortcut-list">
                {group.items.map((item, idx) => (
                  <div key={idx} className="shortcut-item">
                    <kbd className="shortcut-key">{item.key}</kbd>
                    <span className="shortcut-description">{item.description}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="help-footer">
          <p className="help-hint">Press <kbd className="shortcut-key">?</kbd> or <kbd className="shortcut-key">Esc</kbd> to close</p>
        </div>
      </div>
    </div>
  );
}
