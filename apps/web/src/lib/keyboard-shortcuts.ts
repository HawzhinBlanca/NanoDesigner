// Professional keyboard shortcuts system
import { useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

// Keyboard shortcut definitions
export const shortcuts = {
  // Navigation
  navigation: {
    home: { keys: ['Alt', 'H'], description: 'Go to home' },
    dashboard: { keys: ['Alt', 'D'], description: 'Go to dashboard' },
    projects: { keys: ['Alt', 'P'], description: 'View projects' },
    compose: { keys: ['Alt', 'C'], description: 'Open composer' },
    history: { keys: ['Alt', 'Y'], description: 'View history' },
  },
  
  // Actions
  actions: {
    generate: { keys: ['Ctrl', 'Enter'], mac: ['Cmd', 'Enter'], description: 'Generate design' },
    save: { keys: ['Ctrl', 'S'], mac: ['Cmd', 'S'], description: 'Save changes' },
    undo: { keys: ['Ctrl', 'Z'], mac: ['Cmd', 'Z'], description: 'Undo' },
    redo: { keys: ['Ctrl', 'Shift', 'Z'], mac: ['Cmd', 'Shift', 'Z'], description: 'Redo' },
    duplicate: { keys: ['Ctrl', 'D'], mac: ['Cmd', 'D'], description: 'Duplicate' },
    delete: { keys: ['Delete'], description: 'Delete selected' },
    selectAll: { keys: ['Ctrl', 'A'], mac: ['Cmd', 'A'], description: 'Select all' },
    copy: { keys: ['Ctrl', 'C'], mac: ['Cmd', 'C'], description: 'Copy' },
    paste: { keys: ['Ctrl', 'V'], mac: ['Cmd', 'V'], description: 'Paste' },
    cut: { keys: ['Ctrl', 'X'], mac: ['Cmd', 'X'], description: 'Cut' },
  },
  
  // UI
  ui: {
    search: { keys: ['Ctrl', 'K'], mac: ['Cmd', 'K'], description: 'Open search' },
    help: { keys: ['?'], description: 'Show help' },
    shortcuts: { keys: ['Ctrl', '/'], mac: ['Cmd', '/'], description: 'Show shortcuts' },
    fullscreen: { keys: ['F11'], description: 'Toggle fullscreen' },
    zen: { keys: ['Ctrl', '.'], mac: ['Cmd', '.'], description: 'Zen mode' },
    toggleSidebar: { keys: ['Ctrl', 'B'], mac: ['Cmd', 'B'], description: 'Toggle sidebar' },
    escape: { keys: ['Escape'], description: 'Close modal/dialog' },
  },
  
  // Advanced
  advanced: {
    refresh: { keys: ['Ctrl', 'R'], mac: ['Cmd', 'R'], description: 'Refresh data' },
    export: { keys: ['Ctrl', 'E'], mac: ['Cmd', 'E'], description: 'Export' },
    import: { keys: ['Ctrl', 'I'], mac: ['Cmd', 'I'], description: 'Import' },
    settings: { keys: ['Ctrl', ','], mac: ['Cmd', ','], description: 'Open settings' },
    newProject: { keys: ['Ctrl', 'N'], mac: ['Cmd', 'N'], description: 'New project' },
  },
};

// Platform detection
const isMac = typeof window !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;

// Get platform-specific keys
function getPlatformKeys(shortcut: any): string[] {
  if (isMac && shortcut.mac) {
    return shortcut.mac;
  }
  return shortcut.keys;
}

// Format shortcut for display
export function formatShortcut(shortcut: any): string {
  const keys = getPlatformKeys(shortcut);
  return keys.map(key => {
    if (key === 'Cmd') return '⌘';
    if (key === 'Ctrl') return isMac ? '⌃' : 'Ctrl';
    if (key === 'Alt') return isMac ? '⌥' : 'Alt';
    if (key === 'Shift') return isMac ? '⇧' : 'Shift';
    if (key === 'Enter') return '↵';
    if (key === 'Delete') return '⌫';
    if (key === 'Escape') return 'Esc';
    return key;
  }).join(isMac ? '' : '+');
}

// Keyboard event handler
interface ShortcutHandler {
  id: string;
  keys: string[];
  handler: () => void;
  preventDefault?: boolean;
  allowInInput?: boolean;
}

class KeyboardShortcutManager {
  private handlers: Map<string, ShortcutHandler> = new Map();
  private pressed: Set<string> = new Set();
  
  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', this.handleKeyDown);
      window.addEventListener('keyup', this.handleKeyUp);
      window.addEventListener('blur', this.handleBlur);
    }
  }
  
  register(handler: ShortcutHandler) {
    const key = this.getHandlerKey(handler.keys);
    this.handlers.set(key, handler);
  }
  
  unregister(id: string) {
    for (const [key, handler] of this.handlers.entries()) {
      if (handler.id === id) {
        this.handlers.delete(key);
      }
    }
  }
  
  private getHandlerKey(keys: string[]): string {
    return keys.map(k => k.toLowerCase()).sort().join('+');
  }
  
  private handleKeyDown = (e: KeyboardEvent) => {
    // Track pressed keys
    const key = this.getKeyName(e);
    this.pressed.add(key.toLowerCase());
    
    // Check if we're in an input field
    const target = e.target as HTMLElement;
    const isInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
    
    // Build current key combination
    const currentKeys: string[] = [];
    if (e.ctrlKey || e.metaKey) currentKeys.push(isMac ? 'cmd' : 'ctrl');
    if (e.altKey) currentKeys.push('alt');
    if (e.shiftKey) currentKeys.push('shift');
    if (!['Control', 'Alt', 'Shift', 'Meta'].includes(e.key)) {
      currentKeys.push(key.toLowerCase());
    }
    
    const handlerKey = this.getHandlerKey(currentKeys);
    const handler = this.handlers.get(handlerKey);
    
    if (handler && (!isInput || handler.allowInInput)) {
      if (handler.preventDefault) {
        e.preventDefault();
      }
      handler.handler();
    }
  };
  
  private handleKeyUp = (e: KeyboardEvent) => {
    const key = this.getKeyName(e);
    this.pressed.delete(key.toLowerCase());
  };
  
  private handleBlur = () => {
    this.pressed.clear();
  };
  
  private getKeyName(e: KeyboardEvent): string {
    if (e.key === ' ') return 'space';
    if (e.key === 'Control') return 'ctrl';
    if (e.key === 'Meta') return 'cmd';
    return e.key;
  }
  
  destroy() {
    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', this.handleKeyDown);
      window.removeEventListener('keyup', this.handleKeyUp);
      window.removeEventListener('blur', this.handleBlur);
    }
  }
}

// Global manager instance
let manager: KeyboardShortcutManager | null = null;

if (typeof window !== 'undefined') {
  manager = new KeyboardShortcutManager();
}

// React hook for keyboard shortcuts
export function useKeyboardShortcut(
  keys: string[],
  handler: () => void,
  options: {
    preventDefault?: boolean;
    allowInInput?: boolean;
    enabled?: boolean;
  } = {}
) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;
  
  useEffect(() => {
    if (!manager || options.enabled === false) return;
    
    const id = Math.random().toString(36);
    manager.register({
      id,
      keys: keys.map(k => k.toLowerCase()),
      handler: () => handlerRef.current(),
      preventDefault: options.preventDefault ?? true,
      allowInInput: options.allowInInput ?? false,
    });
    
    return () => {
      manager?.unregister(id);
    };
  }, [keys.join('+'), options.enabled, options.preventDefault, options.allowInInput]);
}

// Hook for common shortcuts
export function useCommonShortcuts() {
  const router = useRouter();
  
  // Navigation shortcuts
  useKeyboardShortcut(['alt', 'h'], () => router.push('/'));
  useKeyboardShortcut(['alt', 'd'], () => router.push('/dashboard'));
  useKeyboardShortcut(['alt', 'p'], () => router.push('/projects'));
  
  // UI shortcuts
  useKeyboardShortcut(['escape'], () => {
    window.dispatchEvent(new CustomEvent('closeModal'));
  });
  
  useKeyboardShortcut(['ctrl', 'k'], () => {
    window.dispatchEvent(new CustomEvent('openSearch'));
  }, { preventDefault: true });
  
  useKeyboardShortcut(['?'], () => {
    window.dispatchEvent(new CustomEvent('showHelp'));
  }, { allowInInput: false });
}

// Shortcut hints component
export function ShortcutHint({ shortcut }: { shortcut: any }) {
  const formatted = formatShortcut(shortcut);
  
  return (
    <kbd className="px-2 py-1 text-xs font-semibold text-muted-foreground bg-secondary rounded-md border border-border">
      {formatted}
    </kbd>
  );
}

// Global shortcuts provider
export function useGlobalShortcuts() {
  const router = useRouter();
  
  // Save handler
  const handleSave = useCallback(() => {
    window.dispatchEvent(new CustomEvent('save'));
    toast.success('Changes saved');
  }, []);
  
  // Generate handler
  const handleGenerate = useCallback(() => {
    window.dispatchEvent(new CustomEvent('generate'));
  }, []);
  
  // Undo/Redo
  const handleUndo = useCallback(() => {
    window.dispatchEvent(new CustomEvent('undo'));
  }, []);
  
  const handleRedo = useCallback(() => {
    window.dispatchEvent(new CustomEvent('redo'));
  }, []);
  
  // Register all shortcuts
  useKeyboardShortcut(['ctrl', 's'], handleSave, { preventDefault: true });
  useKeyboardShortcut(['cmd', 's'], handleSave, { preventDefault: true });
  
  useKeyboardShortcut(['ctrl', 'enter'], handleGenerate);
  useKeyboardShortcut(['cmd', 'enter'], handleGenerate);
  
  useKeyboardShortcut(['ctrl', 'z'], handleUndo, { preventDefault: true });
  useKeyboardShortcut(['cmd', 'z'], handleUndo, { preventDefault: true });
  
  useKeyboardShortcut(['ctrl', 'shift', 'z'], handleRedo, { preventDefault: true });
  useKeyboardShortcut(['cmd', 'shift', 'z'], handleRedo, { preventDefault: true });
  
  // New project
  useKeyboardShortcut(['ctrl', 'n'], () => {
    router.push('/projects/new');
  }, { preventDefault: true });
  
  useKeyboardShortcut(['cmd', 'n'], () => {
    router.push('/projects/new');
  }, { preventDefault: true });
}

// Keyboard shortcuts modal content
export function KeyboardShortcutsHelp() {
  return (
    <div className="space-y-6">
      {Object.entries(shortcuts).map(([category, items]) => (
        <div key={category}>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            {category}
          </h3>
          <div className="space-y-2">
            {Object.entries(items).map(([key, shortcut]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-sm">{shortcut.description}</span>
                <ShortcutHint shortcut={shortcut} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}