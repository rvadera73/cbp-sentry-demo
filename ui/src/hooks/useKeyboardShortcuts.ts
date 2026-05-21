import { useEffect } from 'react';

export interface KeyboardShortcuts {
  [key: string]: () => void;
}

/**
 * Hook to handle keyboard shortcuts
 * Shortcuts:
 * - Arrow Up/Down: Navigate case queue
 * - Tab: Switch between tab sections
 * - ?: Show help modal
 * - E: Expand current tab
 * - Ctrl+P: Print referral package
 * - Ctrl+E: Export referral package
 */
export function useKeyboardShortcuts(shortcuts: KeyboardShortcuts) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input/textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        // Allow Ctrl+E and Ctrl+P even in inputs
        if (!((e.ctrlKey || e.metaKey) && (e.key === 'e' || e.key === 'p'))) {
          return;
        }
      }

      const key = buildKeyString(e);
      if (shortcuts[key]) {
        e.preventDefault();
        shortcuts[key]();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}

/**
 * Build a normalized key string from KeyboardEvent
 */
function buildKeyString(e: KeyboardEvent): string {
  const parts = [];
  if (e.ctrlKey || e.metaKey) parts.push('ctrl');
  if (e.shiftKey) parts.push('shift');
  if (e.altKey) parts.push('alt');

  const keyName = e.key.toLowerCase();
  parts.push(keyName === ' ' ? 'space' : keyName);

  return parts.join('+');
}
