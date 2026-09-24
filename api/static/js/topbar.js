/**
 * MAI Topbar - Top Bar with MAI Status Indicator
 * Persistent top bar with search, MAI status, and user actions
 * 
 * Usage:
 * import { MAITopbar } from './topbar.js';
 * const topbar = new MAITopbar({ container: '#topbar' });
 * topbar.setStatus('listening');
 */

// ============================================================================
// SVG ICONS
// ============================================================================

const ICONS = {
  search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  bell: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>`,
  settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
  user: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
  command: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"/></svg>`,
  globe: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`,
  chevronDown: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>`,
  mic: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>`,
  micOff: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="1" y1="1" x2="23" y2="23"/><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"/><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>`
};

// ============================================================================
// MAI TOPBAR CLASS
// ============================================================================

class MAITopbar {
  /**
   * Create a new MAI Topbar
   * @param {Object} options
   * @param {string|HTMLElement} options.container - Container selector or element
   * @param {Function} options.onSearch - Search callback
   * @param {Function} options.onCommand - Command palette trigger
   * @param {Function} options.onGlobalSearch - Global search trigger
   * @param {Function} options.onNotificationClick - Notification click handler
   * @param {Function} options.onSettingsClick - Settings click handler
   * @param {Function} options.onProfileClick - Profile click handler
   * @param {boolean} options.showSearch - Show search input (default: true)
   * @param {string} options.placeholder - Search placeholder text
   */
  constructor(options = {}) {
    this.container = typeof options.container === 'string'
      ? document.querySelector(options.container)
      : options.container;

    if (!this.container) {
      throw new Error('MAITopbar: Container not found');
    }

    this.onSearch = options.onSearch || null;
    this.onCommand = options.onCommand || null;
    this.onGlobalSearch = options.onGlobalSearch || null;
    this.onNotificationClick = options.onNotificationClick || null;
    this.onSettingsClick = options.onSettingsClick || null;
    this.onProfileClick = options.onProfileClick || null;
    this.showSearch = options.showSearch !== false;
    this.placeholder = options.placeholder || 'Search...';
    
    this.currentStatus = 'idle';
    this.notificationCount = 0;
    this.micMuted = false;

    this._boundHandleKeydown = this._handleKeydown.bind(this);
    this._debouncedSearch = this._debounce(this._handleSearch.bind(this), 300);

    this._injectStyles();
    this._render();
    this._bindEvents();
    this._initStatusIndicator();
  }

  _injectStyles() {
    if (!document.getElementById('mai-topbar-styles')) {
      const style = document.createElement('style');
      style.id = 'mai-topbar-styles';
      style.textContent = `
        .mai-topbar {
          position: relative;
          z-index: 400;
        }
        
        .mai-topbar-search-input {
          transition: all 200ms ease-out;
        }
        
        .mai-topbar-search-input:focus {
          box-shadow: 0 0 0 3px rgba(124, 92, 255, 0.2);
        }
        
        .mai-topbar-btn {
          transition: all 150ms ease-out;
        }
        
        .mai-topbar-btn:hover {
          background: var(--color-bg-panel, #12141A);
          color: var(--color-text-primary, #F2F5FA);
        }
        
        .mai-topbar-status {
          transition: all 200ms ease-out;
        }
        
        .mai-status-indicator-topbar {
          transition: all 200ms ease-out;
        }
        
        /* Reduced motion */
        @media (prefers-reduced-motion: reduce) {
          .mai-topbar * {
            transition: none !important;
            animation: none !important;
          }
        }
        
        /* Mobile */
        @media (max-width: 768px) {
          .mai-topbar-center {
            display: none !important;
          }
          
          .mai-topbar {
            padding: 0 12px !important;
          }
        }
      `;
      document.head.appendChild(style);
    }
  }

  _render() {
    this.container.innerHTML = '';
    this.container.className = 'mai-topbar';
    this.container.setAttribute('role', 'banner');

    this.container.innerHTML = `
      <div class="mai-topbar-left">
        <button class="mai-topbar-btn mai-topbar-menu-toggle" aria-label="Toggle navigation" aria-expanded="false">
          <span class="mai-topbar-btn-icon">${ICONS.command}</span>
        </button>
        <div class="mai-topbar-brand" style="display: flex; align-items: center; gap: 8px; margin-left: 8px;">
          <span style="font-size: 18px; font-weight: 700; letter-spacing: -0.02em;">MAI</span>
        </div>
      </div>
      
      <div class="mai-topbar-center">
        ${this.showSearch ? `
          <div class="mai-topbar-search" style="position: relative; width: 100%; max-width: 480px;">
            <input 
              type="search" 
              class="mai-topbar-search-input" 
              placeholder="${this.placeholder}"
              aria-label="Search"
              autocomplete="off"
              spellcheck="false"
            >
            <span class="mai-topbar-search-icon" aria-hidden="true">${ICONS.search}</span>
          </div>
        ` : ''}
      </div>
      
      <div class="mai-topbar-right">
        <div class="mai-topbar-status" role="status" aria-live="polite" aria-atomic="true">
          <span class="mai-status-indicator-topbar" aria-hidden="true"></span>
          <span class="mai-topbar-status-text">IDLE</span>
        </div>
        
        <div class="mai-topbar-actions">
          <button class="mai-topbar-btn mai-topbar-voice-btn" aria-label="Toggle voice" aria-pressed="false">
            <span class="mai-topbar-btn-icon">${ICONS.mic}</span>
          </button>
          
          <button class="mai-topbar-btn mai-topbar-notifications-btn" aria-label="Notifications" aria-haspopup="true">
            <span class="mai-topbar-btn-icon">${ICONS.bell}</span>
            <span class="mai-topbar-btn-badge" style="display: none;">0</span>
          </button>
          
          <button class="mai-topbar-btn mai-topbar-settings-btn" aria-label="Settings">
            <span class="mai-topbar-btn-icon">${ICONS.settings}</span>
          </button>
          
          <div class="mai-topbar-user" style="display: flex; align-items: center; gap: 8px; margin-left: 8px; padding: 4px 8px; border-radius: 8px; background: var(--color-bg-panel, #12141A);">
            <button class="mai-topbar-btn mai-topbar-profile-btn" aria-label="Profile" style="width: auto; height: auto; padding: 4px 8px; background: transparent;">
              <span class="mai-topbar-btn-icon" style="width: 28px; height: 28px; border-radius: 50%; background: var(--color-accent-primary, #7C5CFF); display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 12px;">U</span>
            </button>
            <span style="font-size: 13px; font-weight: 500; color: var(--color-text-primary, #F2F5FA);">User</span>
            <span class="mai-topbar-btn-icon">${ICONS.chevronDown}</span>
          </div>
        </div>
      </div>
    `;

    // Store references
    this._menuToggle = this.container.querySelector('.mai-topbar-menu-toggle');
    this._searchInput = this.container.querySelector('.mai-topbar-search-input');
    this._statusContainer = this.container.querySelector('.mai-topbar-status');
    this._statusDot = this.container.querySelector('.mai-status-indicator-topbar');
    this._statusText = this.container.querySelector('.mai-topbar-status-text');
    this._voiceBtn = this.container.querySelector('.mai-topbar-voice-btn');
    this._notificationsBtn = this.container.querySelector('.mai-topbar-notifications-btn');
    this._notificationsBadge = this.container.querySelector('.mai-topbar-btn-badge');
    this._settingsBtn = this.container.querySelector('.mai-topbar-settings-btn');
    this._profileBtn = this.container.querySelector('.mai-topbar-profile-btn');
  }

  _bindEvents() {
    // Menu toggle
    this._menuToggle?.addEventListener('click', () => {
      this.container.dispatchEvent(new CustomEvent('mai:menutoggle', { bubbles: true }));
    });

    // Search input
    this._searchInput?.addEventListener('input', (e) => {
      this._debouncedSearch(e.target.value);
    });

    this._searchInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this._handleSearchSubmit(e.target.value);
      } else if (e.key === 'Escape') {
        e.target.blur();
        e.target.value = '';
      }
    });

    // Focus/blur search
    this._searchInput?.addEventListener('focus', () => {
      this.container.classList.add('search-focused');
    });

    this._searchInput?.addEventListener('blur', () => {
      this.container.classList.remove('search-focused');
    });

    // Voice button
    this._voiceBtn?.addEventListener('click', () => this.toggleMic());

    // Notifications
    this._notificationsBtn?.addEventListener('click', () => {
      if (this.onNotificationClick) this.onNotificationClick();
      this.container.dispatchEvent(new CustomEvent('mai:notifications', { bubbles: true }));
    });

    // Settings
    this._settingsBtn?.addEventListener('click', () => {
      if (this.onSettingsClick) this.onSettingsClick();
      this.container.dispatchEvent(new CustomEvent('mai:settings', { bubbles: true }));
    });

    // Profile
    this._profileBtn?.addEventListener('click', () => {
      if (this.onProfileClick) this.onProfileClick();
      this.container.dispatchEvent(new CustomEvent('mai:profile', { bubbles: true }));
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', this._boundHandleKeydown);
  }

  _initStatusIndicator() {
    // Create MAIStatusIndicator instance for the status dot
    if (window.MAIStatusIndicator) {
      this._statusIndicator = new window.MAIStatusIndicator({
        container: this._statusDot,
        size: 'sm',
        showLabel: false,
        initialState: this.currentStatus
      });
    }
  }

  _handleKeydown(e) {
    // Cmd/Ctrl + K for command palette
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      if (this.onCommand) this.onCommand();
      this.container.dispatchEvent(new CustomEvent('mai:command', { bubbles: true }));
    }
    
    // Cmd/Ctrl + Shift + K for global search
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'K') {
      e.preventDefault();
      if (this.onGlobalSearch) this.onGlobalSearch();
      this.container.dispatchEvent(new CustomEvent('mai:globalsearch', { bubbles: true }));
    }
    
    // Focus search with /
    if (e.key === '/' && e.target !== this._searchInput && !e.metaKey && !e.ctrlKey && !e.target.matches('input, textarea, [contenteditable]')) {
      e.preventDefault();
      this._searchInput?.focus();
    }
  }

  _debounce(fn, delay) {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn(...args), delay);
    };
  }

  _handleSearch(query) {
    if (this.onSearch) {
      this.onSearch(query);
    }
    this.container.dispatchEvent(new CustomEvent('mai:search', {
      detail: { query },
      bubbles: true
    }));
  }

  _handleSearchSubmit(query) {
    this.container.dispatchEvent(new CustomEvent('mai:searchsubmit', {
      detail: { query },
      bubbles: true
    }));
  }

  /**
   * Set MAI status
   * @param {string} status - One of: idle, listening, thinking, speaking, processing, sleeping, updating, offline
   */
  setStatus(status) {
    if (this._statusIndicator) {
      this._statusIndicator.setState(status);
    } else {
      this.currentStatus = status;
      this._updateStatusUI(status);
    }
  }

  _updateStatusUI(status) {
    this.currentStatus = status;
    const config = {
      idle: { label: 'IDLE', color: '#7C5CFF' },
      listening: { label: 'LISTENING', color: '#6EA8FF' },
      thinking: { label: 'THINKING', color: '#9B86FF' },
      speaking: { label: 'SPEAKING', color: '#72D6A5' },
      processing: { label: 'PROCESSING', color: '#E8B86A' },
      sleeping: { label: 'SLEEPING', color: '#7C5CFF' },
      updating: { label: 'UPDATING', color: '#6EA8FF' },
      offline: { label: 'OFFLINE', color: '#6E7785' }
    };
    
    const c = config[status] || config.idle;
    this._statusText.textContent = c.label;
    this._statusDot.style.backgroundColor = c.color;
    this._statusDot.style.boxShadow = `0 0 8px ${c.color}`;
    this._statusContainer.setAttribute('data-state', status);
  }

  /**
   * Toggle microphone
   */
  toggleMic() {
    this.micMuted = !this.micMuted;
    this._voiceBtn.setAttribute('aria-pressed', this.micMuted.toString());
    this._voiceBtn.innerHTML = this.micMuted ? ICONS.micOff : ICONS.mic;
    this._voiceBtn.title = this.micMuted ? 'Microphone muted' : 'Microphone active';
    
    this.container.dispatchEvent(new CustomEvent('mai:mictoggle', {
      detail: { muted: this.micMuted },
      bubbles: true
    }));
  }

  /**
   * Set notification count
   * @param {number} count 
   */
  setNotificationCount(count) {
    this.notificationCount = count;
    if (this._notificationsBadge) {
      if (count > 0) {
        this._notificationsBadge.textContent = count > 99 ? '99+' : count;
        this._notificationsBadge.style.display = 'flex';
      } else {
        this._notificationsBadge.style.display = 'none';
      }
    }
  }

  /**
   * Set search placeholder
   * @param {string} placeholder 
   */
  setPlaceholder(placeholder) {
    this.placeholder = placeholder;
    this._searchInput?.setAttribute('placeholder', placeholder);
  }

  /**
   * Focus search input
   */
  focusSearch() {
    this._searchInput?.focus();
  }

  /**
   * Clear search
   */
  clearSearch() {
    if (this._searchInput) {
      this._searchInput.value = '';
      this._handleSearch('');
    }
  }

  /**
   * Get current status
   * @returns {string}
   */
  getStatus() {
    return this.currentStatus;
  }

  /**
   * Destroy the topbar
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
    document.querySelectorAll('[data-mai-topbar]').forEach(el => {
      new MAITopbar({ container: el });
    });
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MAITopbar };
}

if (typeof window !== 'undefined') {
  window.MAITopbar = MAITopbar;
}

export { MAITopbar };
export default MAITopbar;