/**
 * MAI Bottombar - Bottom Command/Status Bar
 * Persistent bottom bar with status items, command input, and system info
 * 
 * Usage:
 * import { MAIBottombar } from './bottombar.js';
 * const bottombar = new MAIBottombar({ container: '#bottombar' });
 * bottombar.addStatusItem({ id: 'cpu', label: 'CPU', value: '12%' });
 * bottombar.setCommandMode(true);
 */

// ============================================================================
// SVG ICONS
// ============================================================================

const ICONS = {
  cpu: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="15" x2="4" y2="15"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="15" x2="23" y2="15"/></svg>`,
  memory: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2"/><path d="M6 10h12"/><path d="M6 14h12"/></svg>`,
  network: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="1" width="22" height="22" rx="2"/><path d="M12 5v14"/><path d="M5 12h14"/></svg>`,
  database: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>`,
  mic: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>`,
  speaker: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>`,
  command: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"/></svg>`,
  search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  chevronUp: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>`,
  chevronDown: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>`,
  x: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  terminal: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>`,
  layout: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>`
};

// ============================================================================
// DEFAULT STATUS ITEMS
// ============================================================================

const DEFAULT_STATUS_ITEMS = [
  { id: 'cpu', icon: 'cpu', label: 'CPU', value: '0%', color: 'var(--color-accent-primary)' },
  { id: 'memory', icon: 'memory', label: 'RAM', value: '0%', color: 'var(--color-accent-blue)' },
  { id: 'network', icon: 'network', label: 'NET', value: '0 KB/s', color: 'var(--color-success)' },
  { id: 'storage', icon: 'database', label: 'DISK', value: '0%', color: 'var(--color-warning)' }
];

// ============================================================================
// MAI BOTTOMBAR CLASS
// ============================================================================

class MAIBottombar {
  /**
   * Create a new MAI Bottombar
   * @param {Object} options
   * @param {string|HTMLElement} options.container - Container selector or element
   * @param {Array} options.statusItems - Status items array
   * @param {Function} options.onCommand - Command submit handler
   * @param {Function} options.onCommandModeChange - Command mode toggle handler
   * @param {boolean} options.commandMode - Start in command mode (default: false)
   * @param {string} options.placeholder - Command input placeholder
   */
  constructor(options = {}) {
    this.container = typeof options.container === 'string'
      ? document.querySelector(options.container)
      : options.container;

    if (!this.container) {
      throw new Error('MAIBottombar: Container not found');
    }

    this.statusItems = options.statusItems || DEFAULT_STATUS_ITEMS;
    this.onCommand = options.onCommand || null;
    this.onCommandModeChange = options.onCommandModeChange || null;
    this.commandMode = options.commandMode || false;
    this.placeholder = options.placeholder || 'Type a command or / for help...';
    
    this._statusElements = new Map();
    this._boundHandleKeydown = this._handleKeydown.bind(this);

    this._injectStyles();
    this._render();
    this._bindEvents();
    this._initStatusIndicators();
  }

  _injectStyles() {
    if (!document.getElementById('mai-bottombar-styles')) {
      const style = document.createElement('style');
      style.id = 'mai-bottombar-styles';
      style.textContent = `
        .mai-bottombar {
          position: relative;
          z-index: 200;
        }
        
        .mai-bottombar-input {
          transition: all 200ms ease-out;
        }
        
        .mai-bottombar-input:focus {
          box-shadow: 0 0 0 3px rgba(124, 92, 255, 0.2);
        }
        
        .mai-bottombar-status {
          transition: all 150ms ease-out;
        }
        
        .mai-bottombar-status:hover {
          border-color: var(--color-border-strong, rgba(255,255,255,0.15));
          color: var(--color-text-primary, #F2F5FA);
        }
        
        .mai-bottombar-status-value {
          font-variant-numeric: tabular-nums;
          font-family: var(--font-mono, 'JetBrains Mono', monospace);
        }
        
        /* Command mode */
        .mai-bottombar.command-mode .mai-bottombar-left,
        .mai-bottombar.command-mode .mai-bottombar-center {
          opacity: 0;
          pointer-events: none;
          width: 0;
          overflow: hidden;
        }
        
        .mai-bottombar.command-mode .mai-bottombar-input-wrapper {
          max-width: none;
          flex: 1;
        }
        
        /* Reduced motion */
        @media (prefers-reduced-motion: reduce) {
          .mai-bottombar * {
            transition: none !important;
            animation: none !important;
          }
        }
        
        /* Mobile */
        @media (max-width: 768px) {
          .mai-bottombar-center {
            display: none !important;
          }
          
          .mai-bottombar {
            padding: 0 12px !important;
          }
        }
      `;
      document.head.appendChild(style);
    }
  }

  _render() {
    this.container.innerHTML = '';
    this.container.className = `mai-bottombar ${this.commandMode ? 'command-mode' : ''}`;
    this.container.setAttribute('role', 'status');

    this.container.innerHTML = `
      <div class="mai-bottombar-left">
        <!-- Status items will be inserted here -->
      </div>
      
      <div class="mai-bottombar-center">
        <!-- Center status items -->
      </div>
      
      <div class="mai-bottombar-right">
        <div class="mai-bottombar-input-wrapper">
          <input 
            type="text" 
            class="mai-bottombar-input" 
            placeholder="${this.placeholder}"
            aria-label="Command input"
            autocomplete="off"
            spellcheck="false"
            ${!this.commandMode ? 'style="display: none;"' : ''}
          >
          <span class="mai-bottombar-input-icon" aria-hidden="true">${ICONS.command}</span>
        </div>
        
        <button class="mai-bottombar-btn mai-bottombar-mode-toggle" aria-label="Toggle command mode" aria-pressed="${this.commandMode}">
          <span class="mai-bottombar-btn-icon">${this.commandMode ? ICONS.chevronUp : ICONS.chevronDown}</span>
        </button>
      </div>
    `;

    // Render status items
    this._renderStatusItems();

    // Store references
    this._leftContainer = this.container.querySelector('.mai-bottombar-left');
    this._centerContainer = this.container.querySelector('.mai-bottombar-center');
    this._inputWrapper = this.container.querySelector('.mai-bottombar-input-wrapper');
    this._input = this.container.querySelector('.mai-bottombar-input');
    this._inputIcon = this.container.querySelector('.mai-bottombar-input-icon');
    this._modeToggle = this.container.querySelector('.mai-bottombar-mode-toggle');
  }

  _renderStatusItems() {
    // Split items between left and center
    const mid = Math.ceil(this.statusItems.length / 2);
    const leftItems = this.statusItems.slice(0, mid);
    const centerItems = this.statusItems.slice(mid);

    // Render left
    if (this._leftContainer) {
      this._leftContainer.innerHTML = leftItems.map(item => this._createStatusItem(item)).join('');
    }

    // Render center
    if (this._centerContainer) {
      this._centerContainer.innerHTML = centerItems.map(item => this._createStatusItem(item)).join('');
    }

    // Store references
    this._statusElements.clear();
    this.container.querySelectorAll('.mai-bottombar-status').forEach(el => {
      const id = el.getAttribute('data-status-id');
      if (id) this._statusElements.set(id, el);
    });
  }

  _createStatusItem(item) {
    return `
      <div class="mai-bottombar-status" data-status-id="${item.id}" role="status" aria-live="polite">
        <span class="mai-bottombar-status-icon" style="color: ${item.color};">${ICONS[item.icon] || ''}</span>
        <span class="mai-bottombar-status-label">${item.label}</span>
        <span class="mai-bottombar-status-value">${item.value}</span>
      </div>
    `;
  }

  _bindEvents() {
    // Mode toggle
    this._modeToggle?.addEventListener('click', () => this.toggleCommandMode());

    // Input events
    this._input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this._handleCommandSubmit(e.target.value);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        if (this.commandMode) {
          this.toggleCommandMode();
        } else {
          e.target.blur();
        }
      } else if (e.key === 'Tab') {
        e.preventDefault();
        this._handleTabComplete(e.target.value);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this._handleHistory('up');
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        this._handleHistory('down');
      }
    });

    this._input?.addEventListener('input', (e) => {
      this.container.dispatchEvent(new CustomEvent('mai:commandinput', {
        detail: { value: e.target.value },
        bubbles: true
      }));
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', this._boundHandleKeydown);

    // Focus input on click of wrapper
    this._inputWrapper?.addEventListener('click', (e) => {
      if (e.target === this._inputWrapper || e.target === this._inputIcon) {
        this._input?.focus();
      }
    });
  }

  _initStatusIndicators() {
    // Initialize MAIStatusIndicator for any status items that need it
    this._statusElements.forEach((el, id) => {
      const item = this.statusItems.find(i => i.id === id);
      if (item && item.indicator) {
        if (window.MAIStatusIndicator) {
          new window.MAIStatusIndicator({
            container: el.querySelector('.mai-bottombar-status-icon'),
            size: 'xs',
            showLabel: false,
            initialState: item.indicator
          });
        }
      }
    });
  }

  _handleKeydown(e) {
    // Cmd/Ctrl + Shift + C for command mode toggle
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'C') {
      e.preventDefault();
      this.toggleCommandMode();
    }
    
    // Backtick for command mode
    if (e.key === '`' && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.target.matches('input, textarea, [contenteditable]')) {
      e.preventDefault();
      this.toggleCommandMode();
    }
  }

  _handleCommandSubmit(value) {
    const trimmed = value.trim();
    if (!trimmed) return;

    this._input.value = '';
    
    if (this.onCommand) {
      this.onCommand(trimmed);
    }
    
    this.container.dispatchEvent(new CustomEvent('mai:command', {
      detail: { command: trimmed },
      bubbles: true
    }));
  }

  _handleTabComplete(value) {
    this.container.dispatchEvent(new CustomEvent('mai:commandcomplete', {
      detail: { value },
      bubbles: true
    }));
  }

  _handleHistory(direction) {
    this.container.dispatchEvent(new CustomEvent('mai:commandhistory', {
      detail: { direction },
      bubbles: true
    }));
  }

  /**
   * Add a status item
   * @param {Object} item - Status item config
   */
  addStatusItem(item) {
    this.statusItems.push(item);
    this._renderStatusItems();
    this._initStatusIndicators();
  }

  /**
   * Remove a status item
   * @param {string} id 
   */
  removeStatusItem(id) {
    this.statusItems = this.statusItems.filter(i => i.id !== id);
    this._renderStatusItems();
  }

  /**
   * Update a status item value
   * @param {string} id 
   * @param {string} value 
   * @param {string} color 
   */
  updateStatusItem(id, value, color) {
    const item = this.statusItems.find(i => i.id === id);
    if (item) {
      item.value = value;
      if (color) item.color = color;
      
      const el = this._statusElements.get(id);
      if (el) {
        const valueEl = el.querySelector('.mai-bottombar-status-value');
        const iconEl = el.querySelector('.mai-bottombar-status-icon');
        if (valueEl) valueEl.textContent = value;
        if (iconEl && color) iconEl.style.color = color;
      }
    }
  }

  /**
   * Set multiple status items at once
   * @param {Object} updates - Map of id -> { value, color }
   */
  updateStatusItems(updates) {
    Object.entries(updates).forEach(([id, data]) => {
      this.updateStatusItem(id, data.value, data.color);
    });
  }

  /**
   * Toggle command mode
   */
  toggleCommandMode() {
    this.commandMode = !this.commandMode;
    this.container.classList.toggle('command-mode', this.commandMode);
    this._modeToggle.setAttribute('aria-pressed', this.commandMode.toString());
    this._modeToggle.innerHTML = this.commandMode ? ICONS.chevronUp : ICONS.chevronDown;
    this._input.style.display = this.commandMode ? 'block' : 'none';
    
    if (this.commandMode) {
      // Focus input after transition
      setTimeout(() => this._input?.focus(), 150);
    } else {
      this._input.blur();
      this._input.value = '';
    }

    if (this.onCommandModeChange) {
      this.onCommandModeChange(this.commandMode);
    }

    this.container.dispatchEvent(new CustomEvent('mai:commandmodetoggle', {
      detail: { commandMode: this.commandMode },
      bubbles: true
    }));
  }

  /**
   * Set command mode explicitly
   * @param {boolean} enabled 
   */
  setCommandMode(enabled) {
    if (this.commandMode !== enabled) {
      this.toggleCommandMode();
    }
  }

  /**
   * Focus command input
   */
  focusCommand() {
    if (!this.commandMode) this.toggleCommandMode();
    this._input?.focus();
  }

  /**
   * Get command mode state
   * @returns {boolean}
   */
  isCommandMode() {
    return this.commandMode;
  }

  /**
   * Destroy the bottombar
   */
  destroy() {
    document.removeEventListener('keydown', this._boundHandleKeydown);
    this.container.innerHTML = '';
    this.container.className = '';
  }
}

// ============================================================================
// AUTO-INITIALIZATION
// ============================================================================

if (typeof window !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-mai-bottombar]').forEach(el => {
      const commandMode = el.hasAttribute('data-command-mode');
      new MAIBottombar({ container: el, commandMode });
    });
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MAIBottombar, DEFAULT_STATUS_ITEMS };
}

if (typeof window !== 'undefined') {
  window.MAIBottombar = MAIBottombar;
}

export { MAIBottombar, DEFAULT_STATUS_ITEMS };
export default MAIBottombar;