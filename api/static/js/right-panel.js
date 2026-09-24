/**
 * MAI Right Panel - Contextual Intelligence Panel
 * Collapsible right panel (320px) for contextual information
 * 
 * Usage:
 * import { MAIRightPanel } from './right-panel.js';
 * const panel = new MAIRightPanel({ container: '#right-panel' });
 * panel.open();
 * panel.setContent('section-id', htmlContent);
 */

// ============================================================================
// SVG ICONS
// ============================================================================

const ICONS = {
  x: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  chevronDown: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>`,
  chevronUp: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>`,
  refresh: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>`,
  sparkles: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 6 15 11 12 16 9 11"/></svg>`,
  heart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>`,
  target: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>`,
  clock: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  layers: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`,
  activity: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
  brain: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5a3 3 0 1 0-6 0 3 3 0 0 0 6 0z"/><path d="M12 5c-2.5 2-4 4.5-4 7a4 4 0 0 0 8 0c0-2.5-1.5-5-4-7z"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>`,
  link: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`,
  alertCircle: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
  checkCircle: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`
};

// ============================================================================
// DEFAULT SECTIONS
// ============================================================================

const DEFAULT_SECTIONS = [
  {
    id: 'current-context',
    title: 'CURRENT CONTEXT',
    icon: 'target',
    collapsible: false,
    priority: 'high'
  },
  {
    id: 'goals',
    title: 'ACTIVE GOALS',
    icon: 'target',
    collapsible: true,
    defaultOpen: true,
    priority: 'high'
  },
  {
    id: 'reasoning',
    title: 'CURRENT REASONING',
    icon: 'brain',
    collapsible: true,
    defaultOpen: true,
    priority: 'high'
  },
  {
    id: 'memory',
    title: 'RELEVANT MEMORIES',
    icon: 'layers',
    collapsible: true,
    defaultOpen: false,
    priority: 'medium'
  },
  {
    id: 'insights',
    title: 'INSIGHTS & PATTERNS',
    icon: 'sparkles',
    collapsible: true,
    defaultOpen: false,
    priority: 'medium'
  },
  {
    id: 'activity',
    title: 'RECENT ACTIVITY',
    icon: 'activity',
    collapsible: true,
    defaultOpen: true,
    priority: 'low'
  }
];

// ============================================================================
// MAI RIGHT PANEL CLASS
// ============================================================================

class MAIRightPanel {
  /**
   * Create a new MAI Right Panel
   * @param {Object} options
   * @param {string|HTMLElement} options.container - Container selector or element
   * @param {Array} options.sections - Panel sections configuration
   * @param {boolean} options.open - Start open (default: false)
   * @param {Function} options.onSectionToggle - Section toggle callback
   * @param {number} options.width - Panel width in pixels (default: 320)
   */
  constructor(options = {}) {
    this.container = typeof options.container === 'string'
      ? document.querySelector(options.container)
      : options.container;

    if (!this.container) {
      throw new Error('MAIRightPanel: Container not found');
    }

    this.sections = options.sections || DEFAULT_SECTIONS;
    this.open = options.open || false;
    this.onSectionToggle = options.onSectionToggle || null;
    this.width = options.width || 320;
    
    this._sectionElements = new Map();
    this._sectionContent = new Map();
    this._sectionOpenState = new Map();

    this._injectStyles();
    this._render();
    this._bindEvents();
    this._initSectionStates();
  }

  _injectStyles() {
    if (!document.getElementById('mai-right-panel-styles')) {
      const style = document.createElement('style');
      style.id = 'mai-right-panel-styles';
      style.textContent = `
        .mai-right-panel {
          position: relative;
          z-index: 300;
        }
        
        .mai-right-panel-content {
          scrollbar-width: thin;
          scrollbar-color: var(--color-border-strong, rgba(255,255,255,0.15)) transparent;
        }
        
        .mai-right-panel-section {
          transition: all 250ms ease-out;
        }
        
        .mai-right-panel-section.collapsed .mai-right-panel-section-content {
          max-height: 0;
          opacity: 0;
          padding-top: 0;
          padding-bottom: 0;
          overflow: hidden;
        }
        
        .mai-right-panel-section-header {
          transition: all 150ms ease-out;
        }
        
        .mai-right-panel-section-header:hover {
          background: var(--color-bg-panel, #12141A);
        }
        
        .mai-right-panel-section-toggle {
          transition: transform 250ms ease-out;
        }
        
        .mai-right-panel-section.collapsed .mai-right-panel-section-toggle {
          transform: rotate(-90deg);
        }
        
        .mai-right-panel-item {
          transition: all 150ms ease-out;
        }
        
        .mai-right-panel-item:hover {
          background: var(--color-bg-panel, #12141A);
        }
        
        .mai-right-panel-loading {
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          color: var(--color-text-muted, #6E7785);
          font-size: 13px;
        }
        
        .mai-right-panel-empty {
          text-align: center;
          padding: 32px 16px;
          color: var(--color-text-muted, #6E7785);
          font-size: 13px;
        }
        
        .mai-right-panel-empty-icon {
          width: 48px;
          height: 48px;
          margin: 0 auto 16px;
          opacity: 0.3;
        }
        
        /* Scrollbar */
        .mai-right-panel-content::-webkit-scrollbar {
          width: 6px;
        }
        
        .mai-right-panel-content::-webkit-scrollbar-track {
          background: transparent;
        }
        
        .mai-right-panel-content::-webkit-scrollbar-thumb {
          background: var(--color-border-strong, rgba(255,255,255,0.15));
          border-radius: 3px;
        }
        
        .mai-right-panel-content::-webkit-scrollbar-thumb:hover {
          background: var(--color-text-muted, #6E7785);
        }
        
        /* Reduced motion */
        @media (prefers-reduced-motion: reduce) {
          .mai-right-panel * {
            transition: none !important;
            animation: none !important;
          }
        }
        
        /* Mobile - panel slides from right */
        @media (max-width: 768px) {
          .mai-right-panel {
            position: fixed;
            right: 0;
            top: 0;
            bottom: 0;
            transform: translateX(100%);
            transition: transform 300ms cubic-bezier(0.23, 1, 0.32, 1);
            box-shadow: -8px 0 32px rgba(0, 0, 0, 0.5);
          }
          
          .mai-right-panel.open {
            transform: translateX(0);
          }
        }
      `;
      document.head.appendChild(style);
    }
  }

  _render() {
    this.container.innerHTML = '';
    this.container.className = `mai-right-panel ${this.open ? 'open' : 'collapsed'}`;
    this.container.style.width = `${this.width}px`;
    this.container.setAttribute('role', 'complementary');
    this.container.setAttribute('aria-label', 'Contextual intelligence panel');

    this.container.innerHTML = `
      <div class="mai-right-panel-header">
        <h2 class="mai-right-panel-title">Context</h2>
        <button class="mai-right-panel-close" aria-label="Close panel">
          ${ICONS.x}
        </button>
      </div>
      
      <div class="mai-right-panel-content"></div>
    `;

    // Render sections
    const contentContainer = this.container.querySelector('.mai-right-panel-content');
    
    this.sections.forEach(section => {
      const sectionEl = this._createSection(section);
      contentContainer.appendChild(sectionEl);
      this._sectionElements.set(section.id, sectionEl);
      this._sectionOpenState.set(section.id, section.defaultOpen !== false);
    });

    // Store references
    this._closeButton = this.container.querySelector('.mai-right-panel-close');
    this._contentContainer = contentContainer;
  }

  _createSection(section) {
    const isOpen = section.defaultOpen !== false;
    const sectionEl = document.createElement('div');
    sectionEl.className = `mai-right-panel-section ${!isOpen ? 'collapsed' : ''}`;
    sectionEl.setAttribute('data-section-id', section.id);
    
    sectionEl.innerHTML = `
      <div class="mai-right-panel-section-header" data-section-toggle="${section.id}">
        <span class="mai-right-panel-section-icon" aria-hidden="true">${ICONS[section.icon] || ''}</span>
        <span class="mai-right-panel-section-title">${section.title}</span>
        ${section.collapsible ? `
          <span class="mai-right-panel-section-toggle" aria-hidden="true">${ICONS.chevronDown}</span>
        ` : ''}
      </div>
      <div class="mai-right-panel-section-content" data-section-content="${section.id}">
        <div class="mai-right-panel-empty">
          <span class="mai-right-panel-empty-icon">${ICONS[section.icon] || ''}</span>
          <div>No data available</div>
        </div>
      </div>
    `;
    
    return sectionEl;
  }

  _bindEvents() {
    // Close button
    this._closeButton?.addEventListener('click', () => this.close());

    // Section toggles
    this.container.querySelectorAll('[data-section-toggle]').forEach(header => {
      header.addEventListener('click', () => {
        const sectionId = header.getAttribute('data-section-toggle');
        this.toggleSection(sectionId);
      });
    });

    // Keyboard navigation
    this.container.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.close();
      }
    });
  }

  _initSectionStates() {
    this._sectionOpenState.forEach((isOpen, sectionId) => {
      const el = this._sectionElements.get(sectionId);
      if (el) {
        el.classList.toggle('collapsed', !isOpen);
      }
    });
  }

  _createSectionContent(sectionId, content) {
    const contentEl = this._sectionElements.get(sectionId)?.querySelector('[data-section-content]');
    if (!contentEl) return;

    if (typeof content === 'string') {
      contentEl.innerHTML = content;
    } else if (content instanceof HTMLElement) {
      contentEl.innerHTML = '';
      contentEl.appendChild(content);
    } else if (Array.isArray(content)) {
      contentEl.innerHTML = content.map(item => this._renderContentItem(item)).join('');
    }
  }

  _renderContentItem(item) {
    if (typeof item === 'string') return item;
    
    const {
      type = 'text',
      title,
      description,
      value,
      icon,
      action,
      timestamp,
      tags,
      metadata
    } = item;

    switch (type) {
      case 'goal':
        return `
          <div class="mai-right-panel-item mai-right-panel-goal" data-goal-id="${item.id || ''}">
            <div class="mai-right-panel-item-header">
              <span class="mai-right-panel-item-icon" style="color: var(--color-accent-primary);">${ICONS.target || ''}</span>
              <div class="mai-right-panel-item-title-row">
                <span class="mai-right-panel-item-title">${title || 'Untitled Goal'}</span>
                ${item.priority ? `<span class="mai-right-panel-item-priority badge badge-${item.priority}">${item.priority}</span>` : ''}
              </div>
            </div>
            ${description ? `<div class="mai-right-panel-item-description">${description}</div>` : ''}
            ${value !== undefined ? `
              <div class="mai-right-panel-item-progress">
                <div class="progress" style="height: 4px;">
                  <div class="progress-bar" style="width: ${value}%"></div>
                </div>
                <span class="mai-right-panel-item-progress-text">${value}%</span>
              </div>
            ` : ''}
            ${timestamp ? `<div class="mai-right-panel-item-meta"><span class="mai-right-panel-item-time">${this._formatTime(timestamp)}</span></div>` : ''}
          </div>
        `;

      case 'memory':
        return `
          <div class="mai-right-panel-item mai-right-panel-memory" data-memory-id="${item.id || ''}">
            <div class="mai-right-panel-item-header">
              <span class="mai-right-panel-item-icon" style="color: var(--color-accent-blue);">${ICONS.layers || ''}</span>
              <span class="mai-right-panel-item-title">${title || 'Memory'}</span>
            </div>
            ${description ? `<div class="mai-right-panel-item-description">${description}</div>` : ''}
            <div class="mai-right-panel-item-meta">
              ${item.importance !== undefined ? `<span class="mai-right-panel-item-badge">Importance: ${Math.round(item.importance * 100)}%</span>` : ''}
              ${item.emotionalWeight !== undefined ? `<span class="mai-right-panel-item-badge">Emotion: ${Math.round(item.emotionalWeight * 100)}%</span>` : ''}
              ${tags ? tags.map(t => `<span class="mai-right-panel-item-tag">#${t}</span>`).join('') : ''}
              ${timestamp ? `<span class="mai-right-panel-item-time">${this._formatTime(timestamp)}</span>` : ''}
            </div>
          </div>
        `;

      case 'reasoning':
        return `
          <div class="mai-right-panel-item mai-right-panel-reasoning">
            <div class="mai-right-panel-item-header">
              <span class="mai-right-panel-item-icon" style="color: var(--color-accent-soft);">${ICONS.brain || ''}</span>
              <span class="mai-right-panel-item-title">${title || 'Reasoning Step'}</span>
            </div>
            ${description ? `<div class="mai-right-panel-item-description">${description}</div>` : ''}
            ${value !== undefined ? `
              <div class="mai-right-panel-item-meta">
                <span class="mai-right-panel-item-badge badge-${value >= 0.7 ? 'success' : value >= 0.4 ? 'warning' : 'danger'}">Confidence: ${Math.round(value * 100)}%</span>
              </div>
            ` : ''}
            ${timestamp ? `<div class="mai-right-panel-item-meta"><span class="mai-right-panel-item-time">${this._formatTime(timestamp)}</span></div>` : ''}
          </div>
        `;

      case 'activity':
        return `
          <div class="mai-right-panel-item mai-right-panel-activity" data-activity-id="${item.id || ''}">
            <div class="mai-right-panel-item-header">
              <span class="mai-right-panel-item-icon" style="color: ${item.color || 'var(--color-accent-primary)'};">${ICONS[item.icon || 'activity'] || ''}</span>
              <span class="mai-right-panel-item-title">${title || 'Activity'}</span>
            </div>
            ${description ? `<div class="mai-right-panel-item-description">${description}</div>` : ''}
            ${timestamp ? `<div class="mai-right-panel-item-meta"><span class="mai-right-panel-item-time">${this._formatTime(timestamp)}</span></div>` : ''}
          </div>
        `;

      case 'insight':
        return `
          <div class="mai-right-panel-item mai-right-panel-insight">
            <div class="mai-right-panel-item-header">
              <span class="mai-right-panel-item-icon" style="color: var(--color-warning);">${ICONS.sparkles || ''}</span>
              <span class="mai-right-panel-item-title">${title || 'Insight'}</span>
            </div>
            ${description ? `<div class="mai-right-panel-item-description">${description}</div>` : ''}
            ${metadata ? `<div class="mai-right-panel-item-meta">${JSON.stringify(metadata)}</div>` : ''}
            ${timestamp ? `<div class="mai-right-panel-item-meta"><span class="mai-right-panel-item-time">${this._formatTime(timestamp)}</span></div>` : ''}
          </div>
        `;

      case 'alert':
        return `
          <div class="mai-right-panel-item mai-right-panel-alert" style="border-left: 3px solid var(--color-danger, #E87575);">
            <div class="mai-right-panel-item-header">
              <span class="mai-right-panel-item-icon" style="color: var(--color-danger);">${ICONS.alertCircle || ''}</span>
              <span class="mai-right-panel-item-title">${title || 'Alert'}</span>
            </div>
            ${description ? `<div class="mai-right-panel-item-description">${description}</div>` : ''}
            ${action ? `<button class="btn btn-sm btn-primary" data-action="${action}">${action}</button>` : ''}
            ${timestamp ? `<div class="mai-right-panel-item-meta"><span class="mai-right-panel-item-time">${this._formatTime(timestamp)}</span></div>` : ''}
          </div>
        `;

      default:
        return `
          <div class="mai-right-panel-item">
            ${title ? `<div class="mai-right-panel-item-title">${title}</div>` : ''}
            ${description ? `<div class="mai-right-panel-item-description">${description}</div>` : ''}
          </div>
        `;
    }
  }

  _formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  }

  /**
   * Open the panel
   */
  open() {
    if (this.open) return;
    this.open = true;
    this.container.classList.add('open');
    this.container.classList.remove('collapsed');
    this.container.dispatchEvent(new CustomEvent('mai:panelopen', { bubbles: true }));
  }

  /**
   * Close the panel
   */
  close() {
    if (!this.open) return;
    this.open = false;
    this.container.classList.remove('open');
    this.container.classList.add('collapsed');
    this.container.dispatchEvent(new CustomEvent('mai:panelclose', { bubbles: true }));
  }

  /**
   * Toggle panel
   */
  toggle() {
    if (this.open) this.close();
    else this.open();
  }

  /**
   * Toggle a section
   * @param {string} sectionId 
   */
  toggleSection(sectionId) {
    const el = this._sectionElements.get(sectionId);
    if (!el) return;

    const isOpen = !el.classList.contains('collapsed');
    el.classList.toggle('collapsed', isOpen);
    this._sectionOpenState.set(sectionId, !isOpen);

    if (this.onSectionToggle) {
      this.onSectionToggle(sectionId, !isOpen);
    }

    this.container.dispatchEvent(new CustomEvent('mai:sectiontoggle', {
      detail: { sectionId, open: !isOpen },
      bubbles: true
    }));
  }

  /**
   * Set section content
   * @param {string} sectionId 
   * @param {string|HTMLElement|Array} content 
   */
  setContent(sectionId, content) {
    this._sectionContent.set(sectionId, content);
    this._createSectionContent(sectionId, content);
  }

  /**
   * Get section content
   * @param {string} sectionId 
   * @returns {any}
   */
  getContent(sectionId) {
    return this._sectionContent.get(sectionId);
  }

  /**
   * Add a section
   * @param {Object} section 
   */
  addSection(section) {
    this.sections.push(section);
    const sectionEl = this._createSection(section);
    this._contentContainer.appendChild(sectionEl);
    this._sectionElements.set(section.id, sectionEl);
    this._sectionOpenState.set(section.id, section.defaultOpen !== false);
  }

  /**
   * Remove a section
   * @param {string} sectionId 
   */
  removeSection(sectionId) {
    this.sections = this.sections.filter(s => s.id !== sectionId);
    const el = this._sectionElements.get(sectionId);
    if (el) el.remove();
    this._sectionElements.delete(sectionId);
    this._sectionOpenState.delete(sectionId);
    this._sectionContent.delete(sectionId);
  }

  /**
   * Show loading state for a section
   * @param {string} sectionId 
   * @param {string} message 
   */
  showLoading(sectionId, message = 'Loading...') {
    const contentEl = this._sectionElements.get(sectionId)?.querySelector('[data-section-content]');
    if (contentEl) {
      contentEl.innerHTML = `<div class="mai-right-panel-loading">${message}</div>`;
    }
  }

  /**
   * Show empty state for a section
   * @param {string} sectionId 
   * @param {string} message 
   * @param {string} icon 
   */
  showEmpty(sectionId, message = 'No data available', icon = 'layers') {
    const contentEl = this._sectionElements.get(sectionId)?.querySelector('[data-section-content]');
    if (contentEl) {
      contentEl.innerHTML = `
        <div class="mai-right-panel-empty">
          <span class="mai-right-panel-empty-icon">${ICONS[icon] || ''}</span>
          <div>${message}</div>
        </div>
      `;
    }
  }

  /**
   * Set panel width
   * @param {number} width 
   */
  setWidth(width) {
    this.width = width;
    this.container.style.width = `${width}px`;
  }

  /**
   * Check if panel is open
   * @returns {boolean}
   */
  isOpen() {
    return this.open;
  }

  /**
   * Check if section is open
   * @param {string} sectionId 
   * @returns {boolean}
   */
  isSectionOpen(sectionId) {
    return this._sectionOpenState.get(sectionId) !== false;
  }

  /**
   * Destroy the panel
   */
  destroy() {
    this.container.innerHTML = '';
    this.container.className = '';
  }
}

// ============================================================================
// AUTO-INITIALIZATION
// ============================================================================

if (typeof window !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-mai-right-panel]').forEach(el => {
      const open = el.hasAttribute('data-open');
      new MAIRightPanel({ container: el, open });
    });
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MAIRightPanel, DEFAULT_SECTIONS };
}

if (typeof window !== 'undefined') {
  window.MAIRightPanel = MAIRightPanel;
}

export { MAIRightPanel, DEFAULT_SECTIONS };
export default MAIRightPanel;