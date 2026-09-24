/**
 * MAI Command Palette - Ctrl+K Command Interface
 * Fast, keyboard-driven command palette with fuzzy search
 * 
 * Usage:
 * import { MAICommandPalette } from './command-palette.js';
 * const palette = new MAICommandPalette({ container: document.body });
 * palette.registerCommand({ id: 'nav-chat', label: 'Go to Chat', action: () => navigate('chat') });
 * palette.open();
 */

// ============================================================================
// SVG ICONS
// ============================================================================

const ICONS = {
  command: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"/></svg>`,
  search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  navigate: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
  action: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
  settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
  help: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  keyboard: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h12"/><path d="M8 12h8"/><path d="M8 16h7"/></svg>`,
  chevronRight: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
  x: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  external: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`
};

// ============================================================================
// DEFAULT COMMANDS
// ============================================================================

const DEFAULT_COMMANDS = [
  // Navigation
  { id: 'nav-presence', label: 'Go to Presence', description: 'Open the presence dashboard', icon: 'navigate', section: 'Navigation', keys: ['g', 'p'], action: 'nav:presence' },
  { id: 'nav-chat', label: 'Go to Chat', description: 'Open chat conversations', icon: 'navigate', section: 'Navigation', keys: ['g', 'c'], action: 'nav:chat' },
  { id: 'nav-memory', label: 'Go to Memory', description: 'Browse memories', icon: 'navigate', section: 'Navigation', keys: ['g', 'm'], action: 'nav:memory' },
  { id: 'nav-graph', label: 'Go to Graph', description: 'Explore knowledge graph', icon: 'navigate', section: 'Navigation', keys: ['g', 'g'], action: 'nav:graph' },
  { id: 'nav-reasoning', label: 'Go to Reasoning', description: 'View reasoning flow', icon: 'navigate', section: 'Navigation', keys: ['g', 'r'], action: 'nav:reasoning' },
  { id: 'nav-agency', label: 'Go to Agency', description: 'Manage agency settings', icon: 'navigate', section: 'Navigation', keys: ['g', 'a'], action: 'nav:agency' },
  { id: 'nav-voice', label: 'Go to Voice', description: 'Voice controls', icon: 'navigate', section: 'Navigation', keys: ['g', 'v'], action: 'nav:voice' },
  { id: 'nav-tasks', label: 'Go to Tasks', description: 'Task management', icon: 'navigate', section: 'Navigation', keys: ['g', 't'], action: 'nav:tasks' },
  { id: 'nav-system', label: 'Go to System', description: 'System settings', icon: 'navigate', section: 'Navigation', keys: ['g', 's'], action: 'nav:system' },
  { id: 'nav-permissions', label: 'Go to Permissions', description: 'Permission settings', icon: 'navigate', section: 'Navigation', keys: ['g', 'e'], action: 'nav:permissions' },

  // Actions
  { id: 'new-chat', label: 'New Chat', description: 'Start a new conversation', icon: 'action', section: 'Actions', keys: ['n', 'c'], action: 'action:new-chat' },
  { id: 'toggle-voice', label: 'Toggle Voice', description: 'Enable/disable voice input', icon: 'action', section: 'Actions', keys: ['v'], action: 'action:toggle-voice' },
  { id: 'toggle-mic', label: 'Toggle Microphone', description: 'Mute/unmute microphone', icon: 'action', section: 'Actions', keys: ['m'], action: 'action:toggle-mic' },
  { id: 'clear-chat', label: 'Clear Chat', description: 'Clear current conversation', icon: 'action', section: 'Actions', keys: ['c', 'c'], action: 'action:clear-chat' },
  { id: 'save-memory', label: 'Save Memory', description: 'Save current context as memory', icon: 'action', section: 'Actions', keys: ['s', 'm'], action: 'action:save-memory' },
  { id: 'export-data', label: 'Export Data', description: 'Export memories and settings', icon: 'action', section: 'Actions', keys: ['e', 'd'], action: 'action:export-data' },

  // System
  { id: 'settings', label: 'Settings', description: 'Open settings', icon: 'settings', section: 'System', keys: [','], action: 'nav:system' },
  { id: 'help', label: 'Help & Shortcuts', description: 'Show keyboard shortcuts', icon: 'help', section: 'System', keys: ['?'], action: 'action:help' },
  { id: 'shortcuts', label: 'Keyboard Shortcuts', description: 'View all shortcuts', icon: 'keyboard', section: 'System', keys: ['k', 's'], action: 'action:shortcuts' },
  { id: 'theme', label: 'Toggle Theme', description: 'Switch theme (dark only)', icon: 'settings', section: 'System', keys: ['t', 't'], action: 'action:theme' },
  { id: 'status-idle', label: 'Set Status: Idle', description: 'Set MAI to idle', icon: 'action', section: 'Status', keys: ['s', 'i'], action: 'status:idle' },
  { id: 'status-thinking', label: 'Set Status: Thinking', description: 'Set MAI to thinking', icon: 'action', section: 'Status', keys: ['s', 't'], action: 'status:thinking' },
  { id: 'status-speaking', label: 'Set Status: Speaking', description: 'Set MAI to speaking', icon: 'action', section: 'Status', keys: ['s', 's'], action: 'status:speaking' },

  // Debug
  { id: 'debug-reload', label: 'Reload App', description: 'Hard reload the application', icon: 'action', section: 'Debug', keys: ['r', 'r'], action: 'debug:reload' },
  { id: 'debug-console', label: 'Open Console', description: 'Open developer console', icon: 'action', section: 'Debug', keys: ['d', 'c'], action: 'debug:console' }
];

// ============================================================================
// FUZZY SEARCH
// ============================================================================

function fuzzyMatch(query, text) {
  if (!query) return { score: 1, matches: [] };
  if (!text) return { score: 0, matches: [] };

  query = query.toLowerCase();
  text = text.toLowerCase();

  let score = 0;
  let matches = [];
  let queryIndex = 0;
  let consecutiveMatches = 0;
  let lastMatchIndex = -2;

  for (let i = 0; i < text.length && queryIndex < query.length; i++) {
    if (text[i] === query[queryIndex]) {
      matches.push(i);
      if (i === lastMatchIndex + 1) {
        consecutiveMatches++;
        score += 10 + consecutiveMatches * 5;
      } else {
        consecutiveMatches = 1;
        score += 10;
      }
      // Bonus for matching at word boundaries
      if (i === 0 || text[i - 1] === ' ' || text[i - 1] === '-' || text[i - 1] === '_') {
        score += 20;
      }
      lastMatchIndex = i;
      queryIndex++;
    }
  }

  if (queryIndex < query.length) return { score: 0, matches: [] };

  // Length penalty
  score = score * (1 - (text.length - query.length) * 0.01);
  
  return { score: Math.max(0, score), matches };
}

// ============================================================================
// MAI COMMAND PALETTE CLASS
// ============================================================================

class MAICommandPalette {
  /**
   * Create a new MAI Command Palette
   * @param {Object} options
   * @param {string|HTMLElement} options.container - Container (usually document.body)
   * @param {Array} options.commands - Custom commands array
   * @param {Function} options.onAction - Action callback
   * @param {Function} options.onNavigate - Navigate callback
   * @param {Function} options.onOpen - Open callback
   * @param {Function} options.onClose - Close callback
   * @param {string} options.placeholder - Input placeholder
   * @param {boolean} options.showShortcuts - Show keyboard shortcuts
   */
  constructor(options = {}) {
    this.container = typeof options.container === 'string'
      ? document.querySelector(options.container)
      : options.container;

    if (!this.container) {
      throw new Error('MAICommandPalette: Container not found');
    }

    this.commands = [...DEFAULT_COMMANDS, ...(options.commands || [])];
    this.onAction = options.onAction || null;
    this.onNavigate = options.onNavigate || null;
    this.onOpen = options.onOpen || null;
    this.onClose = options.onClose || null;
    this.placeholder = options.placeholder || 'Type a command or search...';
    this.showShortcuts = options.showShortcuts !== false;

    this._open = false;
    this._selectedIndex = 0;
    this._filteredCommands = [];
    this._debouncedSearch = this._debounce(this._filterCommands.bind(this), 50);
    this._boundKeydown = this._handleKeydown.bind(this);
    this._boundOutsideClick = this._handleOutsideClick.bind(this);

    this._injectStyles();
    this._render();
    this._bindEvents();
  }

  _injectStyles() {
    if (!document.getElementById('mai-command-palette-styles')) {
      const style = document.createElement('style');
      style.id = 'mai-command-palette-styles';
      style.textContent = `
        .mai-command-palette-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.6);
          backdrop-filter: blur(8px);
          z-index: 899;
          opacity: 0;
          visibility: hidden;
          transition: opacity 200ms ease-out, visibility 200ms;
        }
        
        .mai-command-palette-overlay.visible {
          opacity: 1;
          visibility: visible;
        }
        
        .mai-command-palette {
          position: fixed;
          top: 15%;
          left: 50%;
          transform: translateX(-50%) translateY(-20px) scale(0.95);
          width: 640px;
          max-width: calc(100vw - 32px);
          background: var(--color-bg-card, #181B22);
          border: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          border-radius: 16px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 60px rgba(124, 92, 255, 0.15);
          z-index: 900;
          opacity: 0;
          visibility: hidden;
          overflow: hidden;
          transition: opacity 200ms ease-out, transform 300ms cubic-bezier(0.34, 1.56, 0.64, 1), visibility 200ms;
        }
        
        .mai-command-palette.open {
          opacity: 1;
          visibility: visible;
          transform: translateX(-50%) translateY(0) scale(1);
        }
        
        .mai-command-palette-header {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px 20px;
          border-bottom: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
        }
        
        .mai-command-palette-icon {
          width: 20px;
          height: 20px;
          color: var(--color-accent-primary, #7C5CFF);
          flex-shrink: 0;
        }
        
        .mai-command-palette-input {
          flex: 1;
          background: none;
          border: none;
          font-family: var(--font-sans, 'Inter', 'Manrope', 'Space Grotesk', system-ui, sans-serif);
          font-size: 16px;
          color: var(--color-text-primary, #F2F5FA);
          outline: none;
          width: 100%;
        }
        
        .mai-command-palette-input::placeholder {
          color: var(--color-text-muted, #6E7785);
        }
        
        .mai-command-palette-hint {
          font-size: 12px;
          color: var(--color-text-muted, #6E7785);
          white-space: nowrap;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        
        .mai-command-palette-hint kbd {
          background: var(--color-bg-elevated, #1D2028);
          border: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          border-radius: 4px;
          padding: 2px 6px;
          font-family: var(--font-mono, 'JetBrains Mono', monospace);
          font-size: 11px;
        }
        
        .mai-command-palette-results {
          max-height: 400px;
          overflow-y: auto;
          padding: 8px;
        }
        
        .mai-command-palette-section {
          margin-bottom: 4px;
        }
        
        .mai-command-palette-section-title {
          font-size: 11px;
          font-weight: 600;
          color: var(--color-text-muted, #6E7785);
          text-transform: uppercase;
          letter-spacing: 0.08em;
          padding: 8px 12px;
        }
        
        .mai-command-palette-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 12px;
          background: none;
          border: none;
          border-radius: 8px;
          color: var(--color-text-primary, #F2F5FA);
          font-family: var(--font-sans, 'Inter', 'Manrope', 'Space Grotesk', system-ui, sans-serif);
          font-size: 14px;
          cursor: pointer;
          width: 100%;
          text-align: left;
          transition: background 150ms ease-out;
        }
        
        .mai-command-palette-item:hover,
        .mai-command-palette-item.selected {
          background: var(--color-bg-panel, #12141A);
        }
        
        .mai-command-palette-item-icon {
          width: 20px;
          height: 20px;
          color: var(--color-text-muted, #6E7785);
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .mai-command-palette-item-content {
          flex: 1;
          min-width: 0;
        }
        
        .mai-command-palette-item-title {
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .mai-command-palette-item-description {
          font-size: 12px;
          color: var(--color-text-muted, #6E7785);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          margin-top: 2px;
        }
        
        .mai-command-palette-item-shortcut {
          font-size: 11px;
          color: var(--color-text-muted, #6E7785);
          font-family: var(--font-mono, 'JetBrains Mono', monospace);
          background: var(--color-bg-elevated, #1D2028);
          border: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          border-radius: 4px;
          padding: 2px 8px;
          flex-shrink: 0;
        }
        
        .mai-command-palette-item-section {
          font-size: 10px;
          color: var(--color-text-muted, #6E7785);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-left: auto;
          padding: 2px 6px;
          background: var(--color-bg-elevated, #1D2028);
          border-radius: 4px;
        }
        
        .mai-command-palette-empty {
          padding: 32px 20px;
          text-align: center;
          color: var(--color-text-muted, #6E7785);
          font-size: 14px;
        }
        
        .mai-command-palette-footer {
          padding: 12px 20px;
          border-top: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 11px;
          color: var(--color-text-muted, #6E7785);
        }
        
        .mai-command-palette-footer kbd {
          background: var(--color-bg-elevated, #1D2028);
          border: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          border-radius: 4px;
          padding: 2px 6px;
          font-family: var(--font-mono, 'JetBrains Mono', monospace);
        }
        
        /* Highlight matched characters */
        .mai-command-palette-highlight {
          background: rgba(124, 92, 255, 0.3);
          color: var(--color-accent-soft, #9B86FF);
          border-radius: 2px;
          padding: 0 1px;
        }
        
        /* Reduced motion */
        @media (prefers-reduced-motion: reduce) {
          .mai-command-palette,
          .mai-command-palette-overlay {
            transition: none !important;
          }
        }
        
        /* Mobile */
        @media (max-width: 480px) {
          .mai-command-palette {
            top: 0;
            left: 0;
            width: 100vw;
            max-width: 100vw;
            height: 100vh;
            max-height: 100vh;
            border-radius: 0;
            transform: translateY(-100%);
          }
          
          .mai-command-palette.open {
            transform: translateY(0);
          }
        }
        
        /* Scrollbar */
        .mai-command-palette-results::-webkit-scrollbar {
          width: 6px;
        }
        
        .mai-command-palette-results::-webkit-scrollbar-track {
          background: transparent;
        }
        
        .mai-command-palette-results::-webkit-scrollbar-thumb {
          background: var(--color-border-strong, rgba(255,255,255,0.15));
          border-radius: 3px;
        }
      `;
      document.head.appendChild(style);
    }
  }

  _render() {
    this._overlay = document.createElement('div');
    this._overlay.className = 'mai-command-palette-overlay';
    this._overlay.setAttribute('data-mai-command-palette-overlay', '');

    this._palette = document.createElement('div');
    this._palette.className = 'mai-command-palette';
    this._palette.setAttribute('role', 'dialog');
    this._palette.setAttribute('aria-label', 'Command palette');
    this._palette.setAttribute('aria-modal', 'true');

    this._palette.innerHTML = `
      <div class="mai-command-palette-header">
        <span class="mai-command-palette-icon" aria-hidden="true">${ICONS.command}</span>
        <input 
          type="text" 
          class="mai-command-palette-input" 
          placeholder="${this.placeholder}"
          autocomplete="off"
          spellcheck="false"
          aria-label="Command input"
        >
        ${this.showShortcuts ? `
          <span class="mai-command-palette-hint">
            <kbd>⌘</kbd><kbd>K</kbd> to close
          </span>
        ` : ''}
      </div>
      <div class="mai-command-palette-results"></div>
      <div class="mai-command-palette-footer">
        <span>↑↓ Navigate • ↵ Execute • Esc Close</span>
        <span><kbd>⌘</kbd><kbd>⇧</kbd><kbd>K</kbd> Global Search</span>
      </div>
    `;

    this._input = this._palette.querySelector('.mai-command-palette-input');
    this._resultsContainer = this._palette.querySelector('.mai-command-palette-results');

    document.body.appendChild(this._overlay);
    document.body.appendChild(this._palette);
  }

  _bindEvents() {
    // Input events
    this._input.addEventListener('input', (e) => {
      this._debouncedSearch(e.target.value);
    });

    this._input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this._executeSelected();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        this._selectNext();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this._selectPrevious();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        this.close();
      } else if (e.key === 'Tab') {
        e.preventDefault();
        this._selectNext();
      }
    });

    // Overlay click
    this._overlay.addEventListener('click', this._boundOutsideClick);

    // Keyboard shortcuts
    document.addEventListener('keydown', this._boundKeydown);

    // Focus input on open
    this._overlay.addEventListener('click', () => this.close());
    this._palette.addEventListener('click', (e) => e.stopPropagation());
  }

  _handleKeydown(e) {
    // Cmd/Ctrl + K to toggle
    if ((e.metaKey || e.ctrlKey) && e.key === 'k' && !e.shiftKey) {
      if (e.target !== this._input) {
        e.preventDefault();
        this.toggle();
      }
    }
    
    // Cmd/Ctrl + Shift + K for global search
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'K') {
      if (e.target !== this._input) {
        e.preventDefault();
        this.close();
        if (window.MAIGlobalSearch) {
          const search = new window.MAIGlobalSearch({ container: document.body });
          search.open();
        }
      }
    }
  }

  _handleOutsideClick() {
    this.close();
  }

  _debounce(fn, delay) {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn(...args), delay);
    };
  }

  _filterCommands(query) {
    const scored = this.commands.map(cmd => {
      const labelMatch = fuzzyMatch(query, cmd.label);
      const descMatch = fuzzyMatch(query, cmd.description || '');
      const actionMatch = fuzzyMatch(query, cmd.action || '');
      const keysMatch = cmd.keys ? fuzzyMatch(query, cmd.keys.join(' ')) : { score: 0 };
      
      const score = Math.max(
        labelMatch.score * 1.5,
        descMatch.score,
        actionMatch.score,
        keysMatch.score * 2
      );

      return { ...cmd, _score: score, _matches: labelMatch.matches };
    }).filter(cmd => cmd._score > 0 || !query)
      .sort((a, b) => b._score - a._score);

    this._filteredCommands = scored;
    this._selectedIndex = 0;
    this._renderResults(query);
  }

  _renderResults(query) {
    // Group by section
    const sections = {};
    this._filteredCommands.forEach(cmd => {
      const section = cmd.section || 'Other';
      if (!sections[section]) sections[section] = [];
      sections[section].push(cmd);
    });

    this._resultsContainer.innerHTML = '';

    if (this._filteredCommands.length === 0) {
      this._resultsContainer.innerHTML = `
        <div class="mai-command-palette-empty">
          ${ICONS.search}
          <div>No commands found${query ? ` for "${query}"` : ''}</div>
        </div>
      `;
      return;
    }

    Object.entries(sections).forEach(([sectionName, commands]) => {
      const sectionEl = document.createElement('div');
      sectionEl.className = 'mai-command-palette-section';
      
      sectionEl.innerHTML = `
        <div class="mai-command-palette-section-title">${sectionName}</div>
        ${commands.map((cmd, index) => this._renderCommandItem(cmd, index, query)).join('')}
      `;
      
      this._resultsContainer.appendChild(sectionEl);
    });

    // Update selected item
    this._updateSelection();
  }

  _renderCommandItem(cmd, index, query) {
    const shortcut = cmd.keys && cmd.keys.length > 0 
      ? cmd.keys.map(k => k.toUpperCase()).join(' + ')
      : '';

    const title = this._highlightMatch(cmd.label, cmd._matches || []);
    const description = cmd.description ? this._highlightMatch(cmd.description, []) : '';

    return `
      <button class="mai-command-palette-item ${index === this._selectedIndex ? 'selected' : ''}" 
              data-command-id="${cmd.id}" 
              data-index="${index}"
              role="option"
              aria-selected="${index === this._selectedIndex}">
        <span class="mai-command-palette-item-icon" aria-hidden="true">${ICONS[cmd.icon] || ICONS.action}</span>
        <div class="mai-command-palette-item-content">
          <div class="mai-command-palette-item-title">${title}</div>
          ${description ? `<div class="mai-command-palette-item-description">${description}</div>` : ''}
        </div>
        ${shortcut ? `<span class="mai-command-palette-item-shortcut">${shortcut}</span>` : ''}
        <span class="mai-command-palette-item-section">${sectionName}</span>
      </button>
    `;
  }

  _highlightMatch(text, matches) {
    if (!matches.length) return this._escapeHtml(text);
    
    let result = '';
    let lastIndex = 0;
    
    matches.forEach(index => {
      if (index >= 0 && index < text.length) {
        result += this._escapeHtml(text.slice(lastIndex, index));
        result += `<span class="mai-command-palette-highlight">${this._escapeHtml(text[index])}</span>`;
        lastIndex = index + 1;
      }
    });
    
    result += this._escapeHtml(text.slice(lastIndex));
    return result;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  _selectNext() {
    if (this._filteredCommands.length === 0) return;
    this._selectedIndex = (this._selectedIndex + 1) % this._filteredCommands.length;
    this._updateSelection();
    this._scrollToSelected();
  }

  _selectPrevious() {
    if (this._filteredCommands.length === 0) return;
    this._selectedIndex = (this._selectedIndex - 1 + this._filteredCommands.length) % this._filteredCommands.length;
    this._updateSelection();
    this._scrollToSelected();
  }

  _updateSelection() {
    this._resultsContainer.querySelectorAll('.mai-command-palette-item').forEach((el, index) => {
      const selected = index === this._selectedIndex;
      el.classList.toggle('selected', selected);
      el.setAttribute('aria-selected', selected);
    });
  }

  _scrollToSelected() {
    const selectedEl = this._resultsContainer.querySelector('.mai-command-palette-item.selected');
    if (selectedEl) {
      selectedEl.scrollIntoView({ block: 'nearest' });
    }
  }

  _executeSelected() {
    const cmd = this._filteredCommands[this._selectedIndex];
    if (!cmd) return;

    this.close();

    // Execute action
    if (cmd.action.startsWith('nav:')) {
      const page = cmd.action.replace('nav:', '');
      if (this.onNavigate) this.onNavigate(page);
    } else if (cmd.action.startsWith('status:')) {
      const status = cmd.action.replace('status:', '');
      this.container.dispatchEvent(new CustomEvent('mai:statuschange', { detail: { status } }));
    } else if (cmd.action.startsWith('action:')) {
      const action = cmd.action.replace('action:', '');
      if (this.onAction) this.onAction(action, cmd);
    } else if (cmd.action.startsWith('debug:')) {
      const debug = cmd.action.replace('debug:', '');
      if (debug === 'reload') window.location.reload();
      if (debug === 'console') console.log('Console opened');
    }
  }

  /**
   * Open the command palette
   */
  open() {
    if (this._open) return;
    this._open = true;
    this._overlay.classList.add('visible');
    this._palette.classList.add('open');
    this._input.value = '';
    this._filterCommands('');
    
    // Focus input after animation
    setTimeout(() => this._input.focus(), 100);

    if (this.onOpen) this.onOpen();
    this.container.dispatchEvent(new CustomEvent('mai:commandpaletteopen', { bubbles: true }));
  }

  /**
   * Close the command palette
   */
  close() {
    if (!this._open) return;
    this._open = false;
    this._overlay.classList.remove('visible');
    this._palette.classList.remove('open');
    this._input.blur();

    if (this.onClose) this.onClose();
    this.container.dispatchEvent(new CustomEvent('mai:commandpaletteclose', { bubbles: true }));
  }

  /**
   * Toggle the command palette
   */
  toggle() {
    if (this._open) this.close();
    else this.open();
  }

  /**
   * Register a new command
   * @param {Object} command 
   */
  registerCommand(command) {
    this.commands.push(command);
    if (this._open) this._filterCommands(this._input.value);
  }

  /**
   * Unregister a command
   * @param {string} commandId 
   */
  unregisterCommand(commandId) {
    this.commands = this.commands.filter(c => c.id !== commandId);
    if (this._open) this._filterCommands(this._input.value);
  }

  /**
   * Check if palette is open
   * @returns {boolean}
   */
  isOpen() {
    return this._open;
  }

  /**
   * Show help
   * @param {string[]} helpLines 
   */
  showHelp(helpLines) {
    // Could show in a modal or toast
    console.log('Help:', helpLines);
  }

  /**
   * Destroy the command palette
   */
  destroy() {
    document.removeEventListener('keydown', this._boundKeydown);
    this._overlay.removeEventListener('click', this._boundOutsideClick);
    this._overlay.remove();
    this._palette.remove();
  }
}

// ============================================================================
// AUTO-INITIALIZATION
// ============================================================================

if (typeof window !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    // Global instance for keyboard shortcuts
    if (!window._maiCommandPalette) {
      window._maiCommandPalette = new MAICommandPalette({ container: document.body });
    }
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MAICommandPalette, DEFAULT_COMMANDS, fuzzyMatch };
}

if (typeof window !== 'undefined') {
  window.MAICommandPalette = MAICommandPalette;
}

export { MAICommandPalette, DEFAULT_COMMANDS, fuzzyMatch };
export default MAICommandPalette;