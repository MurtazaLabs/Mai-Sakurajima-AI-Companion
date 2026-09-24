/**
 * MAI Sidebar - Navigation Rail Component
 * Collapsible sidebar (72px ↔ 220px) with smooth animations
 * 
 * Usage:
 * import { MAISidebar } from './sidebar.js';
 * const sidebar = new MAISidebar({ container: '#sidebar' });
 * sidebar.expand();
 * sidebar.collapse();
 * sidebar.toggle();
 */

// ============================================================================
// DEFAULT NAVIGATION ITEMS
// ============================================================================

const DEFAULT_NAV_ITEMS = [
  { id: 'presence', icon: 'home', label: 'Presence', section: 'primary', badge: null },
  { id: 'chat', icon: 'message-square', label: 'Chat', section: 'primary', badge: null },
  { id: 'memory', icon: 'database', label: 'Memory', section: 'primary', badge: null },
  { id: 'graph', icon: 'git-branch', label: 'Graph', section: 'primary', badge: null },
  { id: 'reasoning', icon: 'brain', label: 'Reasoning', section: 'primary', badge: null },
  { id: 'agency', icon: 'zap', label: 'Agency', section: 'primary', badge: null },
  { id: 'voice', icon: 'mic', label: 'Voice', section: 'primary', badge: null },
  { id: 'tasks', icon: 'check-square', label: 'Tasks', section: 'secondary', badge: null },
  { id: 'system', icon: 'cpu', label: 'System', section: 'secondary', badge: null },
  { id: 'permissions', icon: 'shield', label: 'Permissions', section: 'secondary', badge: null }
];

const SECTION_CONFIG = {
  primary: { title: 'NAVIGATION', order: 1 },
  secondary: { title: 'TOOLS', order: 2 }
};

// ============================================================================
// SVG ICONS
// ============================================================================

const ICONS = {
  home: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
  'message-square': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
  database: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>`,
  'git-branch': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>`,
  brain: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5a3 3 0 1 0-6 0 3 3 0 0 0 6 0z"/><path d="M12 5c-2.5 2-4 4.5-4 7a4 4 0 0 0 8 0c0-2.5-1.5-5-4-7z"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>`,
  zap: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
  mic: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>`,
  'check-square': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
  cpu: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="15" x2="4" y2="15"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="15" x2="23" y2="15"/></svg>`,
  shield: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
  chevronLeft: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>`,
  chevronRight: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
  user: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`
};

// ============================================================================
// CSS STYLES
// ============================================================================

const STYLES = `
.mai-sidebar {
  position: relative;
  z-index: 300;
}

/* Mobile sidebar */
.mai-sidebar-mobile {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  transform: translateX(-100%);
  transition: transform 300ms cubic-bezier(0.23, 1, 0.32, 1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.mai-sidebar-mobile.open {
  transform: translateX(0);
}

.mai-sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 299;
  opacity: 0;
  visibility: hidden;
  transition: opacity 300ms ease-out, visibility 300ms;
}

.mai-sidebar-overlay.visible {
  opacity: 1;
  visibility: visible;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .mai-sidebar,
  .mai-sidebar-mobile {
    transition: none !important;
  }
}
`;

// ============================================================================
// MAI SIDEBAR CLASS
// ============================================================================

class MAISidebar {
  /**
   * Create a new MAI Sidebar
   * @param {Object} options
   * @param {string|HTMLElement} options.container - Container selector or element
   * @param {Array} options.items - Navigation items array
   * @param {boolean} options.collapsed - Start collapsed (default: true)
   * @param {Function} options.onNavigate - Callback when nav item clicked
   * @param {string} options.activeItem - Initially active item ID
   * @param {boolean} options.mobile - Enable mobile behavior (default: auto-detect)
   */
  constructor(options = {}) {
    this.container = typeof options.container === 'string'
      ? document.querySelector(options.container)
      : options.container;

    if (!this.container) {
      throw new Error('MAISidebar: Container not found');
    }

    this.items = options.items || DEFAULT_NAV_ITEMS;
    this.collapsed = options.collapsed !== false;
    this.onNavigate = options.onNavigate || null;
    this.activeItem = options.activeItem || 'presence';
    this.mobile = options.mobile ?? (window.innerWidth <= 768);

    this._boundHandleResize = this._handleResize.bind(this);
    this._boundHandleClick = this._handleClick.bind(this);
    this._boundHandleKeydown = this._handleKeydown.bind(this);

    this._injectStyles();
    this._render();
    this._bindEvents();
    this._updateAria();
  }

  _injectStyles() {
    if (!document.getElementById('mai-sidebar-styles')) {
      const style = document.createElement('style');
      style.id = 'mai-sidebar-styles';
      style.textContent = STYLES;
      document.head.appendChild(style);
    }
  }

  _render() {
    // Group items by section
    const sections = {};
    this.items.forEach(item => {
      const section = item.section || 'primary';
      if (!sections[section]) sections[section] = [];
      sections[section].push(item);
    });

    // Sort sections by order
    const sortedSections = Object.entries(sections)
      .sort((a, b) => (SECTION_CONFIG[a[0]]?.order || 99) - (SECTION_CONFIG[b[0]]?.order || 99));

    this.container.innerHTML = '';
    this.container.className = `mai-sidebar ${this.collapsed ? 'collapsed' : 'expanded'} ${this.mobile ? 'mai-sidebar-mobile' : ''}`;
    this.container.setAttribute('role', 'navigation');
    this.container.setAttribute('aria-label', 'Main navigation');

    // Header with logo and toggle
    const header = document.createElement('div');
    header.className = 'mai-sidebar-header';
    header.innerHTML = `
      <div class="mai-sidebar-logo">
        <div class="mai-sidebar-logo-icon">
          ${ICONS.home}
        </div>
        <span class="mai-sidebar-logo-text">MAI</span>
      </div>
      <button class="mai-sidebar-toggle" aria-label="${this.collapsed ? 'Expand sidebar' : 'Collapse sidebar'}" aria-expanded="${!this.collapsed}">
        ${this.collapsed ? ICONS.chevronRight : ICONS.chevronLeft}
      </button>
    `;
    this.container.appendChild(header);

    // Navigation
    const nav = document.createElement('nav');
    nav.className = 'mai-sidebar-nav';
    nav.setAttribute('role', 'list');

    sortedSections.forEach(([sectionKey, items]) => {
      const sectionConfig = SECTION_CONFIG[sectionKey] || { title: sectionKey.toUpperCase() };
      
      const sectionTitle = document.createElement('div');
      sectionTitle.className = 'mai-nav-section-title';
      sectionTitle.textContent = sectionConfig.title;
      nav.appendChild(sectionTitle);

      items.forEach(item => {
        const button = document.createElement('button');
        button.className = `mai-nav-item ${item.id === this.activeItem ? 'active' : ''}`;
        button.setAttribute('data-nav-id', item.id);
        button.setAttribute('role', 'listitem');
        button.setAttribute('aria-current', item.id === this.activeItem ? 'page' : 'false');
        button.setAttribute('aria-label', item.label);
        
        button.innerHTML = `
          <span class="mai-nav-item-icon">${ICONS[item.icon] || ''}</span>
          <span class="mai-nav-item-label">${item.label}</span>
          ${item.badge ? `<span class="mai-nav-item-badge badge badge-primary">${item.badge}</span>` : ''}
        `;
        
        nav.appendChild(button);
      });
    });

    this.container.appendChild(nav);

    // Footer with user info
    const footer = document.createElement('div');
    footer.className = 'mai-sidebar-footer';
    footer.innerHTML = `
      <div class="mai-user-info">
        <div class="mai-user-avatar">${this._getInitials()}</div>
        <div class="mai-user-details">
          <div class="mai-user-name">User</div>
          <div class="mai-user-status">Online</div>
        </div>
      </div>
    `;
    this.container.appendChild(footer);

    // Store references
    this._navButtons = this.container.querySelectorAll('.mai-nav-item');
    this._toggleButton = this.container.querySelector('.mai-sidebar-toggle');
    this._logoText = this.container.querySelector('.mai-sidebar-logo-text');
  }

  _getInitials() {
    return 'U'; // Would come from user context
  }

  _bindEvents() {
    // Toggle button
    this._toggleButton?.addEventListener('click', () => this.toggle());

    // Navigation items
    this._navButtons?.forEach(button => {
      button.addEventListener('click', (e) => {
        const itemId = button.getAttribute('data-nav-id');
        this._handleNavigation(itemId);
      });
    });

    // Keyboard navigation
    this.container.addEventListener('keydown', this._boundHandleKeydown);

    // Resize handler for mobile detection
    window.addEventListener('resize', this._boundHandleResize);

    // Mobile: close on outside click
    if (this.mobile) {
      this._createOverlay();
      this._overlay.addEventListener('click', () => this.collapse());
    }
  }

  _createOverlay() {
    if (this._overlay) return;
    this._overlay = document.createElement('div');
    this._overlay.className = 'mai-sidebar-overlay';
    document.body.appendChild(this._overlay);
  }

  _handleResize() {
    const wasMobile = this.mobile;
    this.mobile = window.innerWidth <= 768;

    if (wasMobile !== this.mobile) {
      this.container.classList.toggle('mai-sidebar-mobile', this.mobile);
      
      if (this.mobile) {
        this._createOverlay();
        this.collapse();
      } else {
        this._overlay?.remove();
        this._overlay = null;
        this.container.style.transform = '';
      }
    }
  }

  _handleClick(e) {
    // Handle clicks on nav items (delegated)
    const navItem = e.target.closest('.mai-nav-item');
    if (navItem) {
      const itemId = navItem.getAttribute('data-nav-id');
      this._handleNavigation(itemId);
    }
  }

  _handleKeydown(e) {
    const items = Array.from(this._navButtons || []);
    const activeIndex = items.findIndex(btn => btn.classList.contains('active'));
    
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault();
      const nextIndex = (activeIndex + 1) % items.length;
      items[nextIndex]?.focus();
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault();
      const prevIndex = (activeIndex - 1 + items.length) % items.length;
      items[prevIndex]?.focus();
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      const activeButton = items[activeIndex];
      if (activeButton) {
        const itemId = activeButton.getAttribute('data-nav-id');
        this._handleNavigation(itemId);
      }
    } else if (e.key === 'Home') {
      e.preventDefault();
      items[0]?.focus();
    } else if (e.key === 'End') {
      e.preventDefault();
      items[items.length - 1]?.focus();
    }
  }

  _handleNavigation(itemId) {
    // Update active state
    this._navButtons?.forEach(btn => {
      const isActive = btn.getAttribute('data-nav-id') === itemId;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-current', isActive ? 'page' : 'false');
    });

    this.activeItem = itemId;

    // Trigger callback
    if (this.onNavigate) {
      this.onNavigate(itemId, this.items.find(i => i.id === itemId));
    }

    // Emit event
    this.container.dispatchEvent(new CustomEvent('mai:navigate', {
      detail: { itemId, item: this.items.find(i => i.id === itemId) },
      bubbles: true
    }));

    // Auto-collapse on mobile
    if (this.mobile) {
      this.collapse();
    }
  }

  _updateAria() {
    this._toggleButton?.setAttribute('aria-label', this.collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    this._toggleButton?.setAttribute('aria-expanded', (!this.collapsed).toString());
    this._toggleButton?.innerHTML = this.collapsed ? ICONS.chevronRight : ICONS.chevronLeft;
  }

  /**
   * Expand the sidebar
   */
  expand() {
    if (!this.collapsed) return;
    this.collapsed = false;
    this.container.classList.remove('collapsed');
    this.container.classList.add('expanded');
    this._updateAria();
    this.container.dispatchEvent(new CustomEvent('mai:sidebartoggle', {
      detail: { collapsed: false },
      bubbles: true
    }));
  }

  /**
   * Collapse the sidebar
   */
  collapse() {
    if (this.collapsed) return;
    this.collapsed = true;
    this.container.classList.remove('expanded');
    this.container.classList.add('collapsed');
    this._updateAria();
    
    if (this.mobile && this._overlay) {
      this._overlay.classList.remove('visible');
    }
    
    this.container.dispatchEvent(new CustomEvent('mai:sidebartoggle', {
      detail: { collapsed: true },
      bubbles: true
    }));
  }

  /**
   * Toggle sidebar state
   */
  toggle() {
    if (this.collapsed) {
      this.expand();
      if (this.mobile && this._overlay) {
        this._overlay.classList.add('visible');
      }
    } else {
      this.collapse();
    }
  }

  /**
   * Set active navigation item
   * @param {string} itemId 
   */
  setActiveItem(itemId) {
    this._handleNavigation(itemId);
  }

  /**
   * Update badge for a nav item
   * @param {string} itemId 
   * @param {string|number|null} badge 
   */
  setBadge(itemId, badge) {
    const item = this.items.find(i => i.id === itemId);
    if (item) {
      item.badge = badge;
      this._render();
      this.setActiveItem(this.activeItem);
    }
  }

  /**
   * Add a navigation item
   * @param {Object} item 
   */
  addItem(item) {
    this.items.push(item);
    this._render();
    this.setActiveItem(this.activeItem);
  }

  /**
   * Remove a navigation item
   * @param {string} itemId 
   */
  removeItem(itemId) {
    this.items = this.items.filter(i => i.id !== itemId);
    if (this.activeItem === itemId) {
      this.activeItem = this.items[0]?.id || null;
    }
    this._render();
    if (this.activeItem) this.setActiveItem(this.activeItem);
  }

  /**
   * Destroy the sidebar
   */
  destroy() {
    window.removeEventListener('resize', this._boundHandleResize);
    this.container.removeEventListener('keydown', this._boundHandleKeydown);
    this._overlay?.remove();
    this.container.innerHTML = '';
    this.container.className = '';
  }
}

// ============================================================================
// AUTO-INITIALIZATION
// ============================================================================

if (typeof window !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-mai-sidebar]').forEach(el => {
      const collapsed = !el.hasAttribute('data-expanded');
      const activeItem = el.getAttribute('data-active') || 'presence';
      const mobile = el.hasAttribute('data-mobile');
      
      new MAISidebar({
        container: el,
        collapsed,
        activeItem,
        mobile
      });
    });
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MAISidebar, DEFAULT_NAV_ITEMS, ICONS };
}

if (typeof window !== 'undefined') {
  window.MAISidebar = MAISidebar;
}

export { MAISidebar, DEFAULT_NAV_ITEMS, ICONS };
export default MAISidebar;