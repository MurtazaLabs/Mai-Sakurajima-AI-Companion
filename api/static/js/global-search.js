/**
 * MAI Global Search - Cmd+Shift+K Global Search Interface
 * Searches across all content types with grouped results
 * 
 * Usage:
 * import { MAIGlobalSearch } from './global-search.js';
 * const search = new MAIGlobalSearch({ container: document.body });
 * search.registerProvider('memories', async (query) => { ... });
 * search.open();
 */

// ============================================================================
// SVG ICONS
// ============================================================================

const ICONS = {
  search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  x: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  navigate: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
  file: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
  folder: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`,
  message: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
  user: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
  brain: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5a3 3 0 1 0-6 0 3 3 0 0 0 6 0z"/><path d="M12 5c-2.5 2-4 4.5-4 7a4 4 0 0 0 8 0c0-2.5-1.5-5-4-7z"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>`,
  link: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`,
  clock: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  star: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  chevronRight: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`
};

// ============================================================================
// SEARCH PROVIDERS (to be registered by the app)
// ============================================================================

const DEFAULT_PROVIDERS = {
  memories: {
    name: 'Memories',
    icon: 'brain',
    search: async (query) => {
      // This will be replaced by the app
      return [];
    }
  },
  conversations: {
    name: 'Conversations',
    icon: 'message',
    search: async (query) => {
      return [];
    }
  },
  knowledge: {
    name: 'Knowledge',
    icon: 'file',
    search: async (query) => {
      return [];
    }
  },
  entities: {
    name: 'Entities',
    icon: 'link',
    search: async (query) => {
      return [];
    }
  },
  commands: {
    name: 'Commands',
    icon: 'navigate',
    search: async (query) => {
      return [];
    }
  }
};

// ============================================================================
// FUZZY SEARCH (shared with command palette)
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
      if (i === 0 || text[i - 1] === ' ' || text[i - 1] === '-' || text[i - 1] === '_') {
        score += 20;
      }
      lastMatchIndex = i;
      queryIndex++;
    }
  }

  if (queryIndex < query.length) return { score: 0, matches: [] };

  score = score * (1 - (text.length - query.length) * 0.01);
  return { score: Math.max(0, score), matches };
}

// ============================================================================
// MAI GLOBAL SEARCH CLASS
// ============================================================================

class MAIGlobalSearch {
  /**
   * Create a new MAI Global Search
   * @param {Object} options
   * @param {string|HTMLElement} options.container - Container (usually document.body)
   * @param {Object} options.providers - Search providers
   * @param {Function} options.onResultClick - Result click handler
   * @param {Function} options.onOpen - Open callback
   * @param {Function} options.onClose - Close callback
   * @param {number} options.maxResultsPerSection - Max results per section
   * @param {number} options.debounceMs - Search debounce time
   */
  constructor(options = {}) {
    this.container = typeof options.container === 'string'
      ? document.querySelector(options.container)
      : options.container;

    if (!this.container) {
      throw new Error('MAIGlobalSearch: Container not found');
    }

    this.providers = { ...DEFAULT_PROVIDERS, ...(options.providers || {}) };
    this.onResultClick = options.onResultClick || null;
    this.onOpen = options.onOpen || null;
    this.onClose = options.onClose || null;
    this.maxResultsPerSection = options.maxResultsPerSection || 10;
    this.debounceMs = options.debounceMs || 150;

    this._open = false;
    this._selectedSection = null;
    this._selectedIndex = 0;
    this._searchResults = {};
    this._debouncedSearch = this._debounce(this._performSearch.bind(this), this.debounceMs);
    this._boundKeydown = this._handleKeydown.bind(this);
    this._boundOutsideClick = this._handleOutsideClick.bind(this);

    this._injectStyles();
    this._render();
    this._bindEvents();
  }

  _injectStyles() {
    if (!document.getElementById('mai-global-search-styles')) {
      const style = document.createElement('style');
      style.id = 'mai-global-search-styles';
      style.textContent = `
        .mai-global-search-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.6);
          backdrop-filter: blur(8px);
          z-index: 899;
          opacity: 0;
          visibility: hidden;
          transition: opacity 200ms ease-out, visibility 200ms;
        }
        
        .mai-global-search-overlay.visible {
          opacity: 1;
          visibility: visible;
        }
        
        .mai-global-search {
          position: fixed;
          top: 10%;
          left: 50%;
          transform: translateX(-50%) translateY(-20px) scale(0.95);
          width: 720px;
          max-width: calc(100vw - 32px);
          max-height: 80vh;
          background: var(--color-bg-card, #181B22);
          border: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          border-radius: 16px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 60px rgba(124, 92, 255, 0.15);
          z-index: 900;
          opacity: 0;
          visibility: hidden;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          transition: opacity 200ms ease-out, transform 300ms cubic-bezier(0.34, 1.56, 0.64, 1), visibility 200ms;
        }
        
        .mai-global-search.open {
          opacity: 1;
          visibility: visible;
          transform: translateX(-50%) translateY(0) scale(1);
        }
        
        .mai-global-search-header {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px 20px;
          border-bottom: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
        }
        
        .mai-global-search-icon {
          width: 20px;
          height: 20px;
          color: var(--color-accent-primary, #7C5CFF);
          flex-shrink: 0;
        }
        
        .mai-global-search-input {
          flex: 1;
          background: none;
          border: none;
          font-family: var(--font-sans, 'Inter', 'Manrope', 'Space Grotesk', system-ui, sans-serif);
          font-size: 16px;
          color: var(--color-text-primary, #F2F5FA);
          outline: none;
          width: 100%;
        }
        
        .mai-global-search-input::placeholder {
          color: var(--color-text-muted, #6E7785);
        }
        
        .mai-global-search-loading {
          width: 20px;
          height: 20px;
          border: 2px solid var(--color-border-default, rgba(255,255,255,0.1));
          border-top-color: var(--color-accent-primary, #7C5CFF);
          border-radius: 50%;
          animation: mai-spin 1s linear infinite;
        }
        
        @keyframes mai-spin {
          to { transform: rotate(360deg); }
        }
        
        .mai-global-search-results {
          flex: 1;
          overflow-y: auto;
          padding: 8px;
        }
        
        .mai-global-search-section {
          margin-bottom: 8px;
          border: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          border-radius: 8px;
          overflow: hidden;
        }
        
        .mai-global-search-section-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 16px;
          background: var(--color-bg-panel, #12141A);
        }
        
        .mai-global-search-section-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 11px;
          font-weight: 600;
          color: var(--color-text-muted, #6E7785);
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }
        
        .mai-global-search-section-count {
          font-size: 11px;
          color: var(--color-text-muted, #6E7785);
          font-family: var(--font-mono, 'JetBrains Mono', monospace);
          background: var(--color-bg-elevated, #1D2028);
          border: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          border-radius: 4px;
          padding: 2px 8px;
        }
        
        .mai-global-search-result {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          background: none;
          border: none;
          border-top: 1px solid var(--color-border-default, rgba(255,255,255,0.05));
          color: var(--color-text-primary, #F2F5FA);
          font-family: var(--font-sans, 'Inter', 'Manrope', 'Space Grotesk', system-ui, sans-serif);
          font-size: 14px;
          cursor: pointer;
          width: 100%;
          text-align: left;
          transition: background 150ms ease-out;
        }
        
        .mai-global-search-result:first-child {
          border-top: none;
        }
        
        .mai-global-search-result:hover,
        .mai-global-search-result.selected {
          background: var(--color-bg-panel, #12141A);
        }
        
        .mai-global-search-result-icon {
          width: 20px;
          height: 20px;
          color: var(--color-text-muted, #6E7785);
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .mai-global-search-result-content {
          flex: 1;
          min-width: 0;
        }
        
        .mai-global-search-result-title {
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .mai-global-search-result-meta {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 4px;
          font-size: 11px;
          color: var(--color-text-muted, #6E7785);
        }
        
        .mai-global-search-result-type {
          padding: 1px 6px;
          background: var(--color-bg-elevated, #1D2028);
          border: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          border-radius: 4px;
          font-family: var(--font-mono, 'JetBrains Mono', monospace);
          text-transform: uppercase;
          font-size: 9px;
        }
        
        .mai-global-search-result-score {
          color: var(--color-accent-primary, #7C5CFF);
          font-family: var(--font-mono, 'JetBrains Mono', monospace);
        }
        
        .mai-global-search-result-time {
          color: var(--color-text-muted, #6E7785);
        }
        
        .mai-global-search-result-description {
          font-size: 12px;
          color: var(--color-text-secondary, #A6B0BF);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          margin-top: 2px;
        }
        
        .mai-global-search-section-loading {
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          color: var(--color-text-muted, #6E7785);
          font-size: 13px;
        }
        
        .mai-global-search-section-empty {
          padding: 24px 16px;
          text-align: center;
          color: var(--color-text-muted, #6E7785);
          font-size: 13px;
        }
        
        .mai-global-search-empty {
          padding: 48px 20px;
          text-align: center;
          color: var(--color-text-muted, #6E7785);
          font-size: 14px;
        }
        
        .mai-global-search-footer {
          padding: 12px 20px;
          border-top: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 11px;
          color: var(--color-text-muted, #6E7785);
        }
        
        .mai-global-search-footer kbd {
          background: var(--color-bg-elevated, #1D2028);
          border: 1px solid var(--color-border-default, rgba(255,255,255,0.1));
          border-radius: 4px;
          padding: 2px 6px;
          font-family: var(--font-mono, 'JetBrains Mono', monospace);
        }
        
        /* Highlight matched characters */
        .mai-global-search-highlight {
          background: rgba(124, 92, 255, 0.3);
          color: var(--color-accent-soft, #9B86FF);
          border-radius: 2px;
          padding: 0 1px;
        }
        
        /* Reduced motion */
        @media (prefers-reduced-motion: reduce) {
          .mai-global-search,
          .mai-global-search-overlay {
            transition: none !important;
          }
        }
        
        /* Mobile */
        @media (max-width: 480px) {
          .mai-global-search {
            top: 0;
            left: 0;
            width: 100vw;
            max-width: 100vw;
            height: 100vh;
            max-height: 100vh;
            border-radius: 0;
            transform: translateY(-100%);
          }
          
          .mai-global-search.open {
            transform: translateY(0);
          }
        }
        
        /* Scrollbar */
        .mai-global-search-results::-webkit-scrollbar {
          width: 6px;
        }
        
        .mai-global-search-results::-webkit-scrollbar-track {
          background: transparent;
        }
        
        .mai-global-search-results::-webkit-scrollbar-thumb {
          background: var(--color-border-strong, rgba(255,255,255,0.15));
          border-radius: 3px;
        }
      `;
      document.head.appendChild(style);
    }
  }

  _render() {
    this._overlay = document.createElement('div');
    this._overlay.className = 'mai-global-search-overlay';
    this._overlay.setAttribute('data-mai-global-search-overlay', '');

    this._search = document.createElement('div');
    this._search.className = 'mai-global-search';
    this._search.setAttribute('role', 'dialog');
    this._search.setAttribute('aria-label', 'Global search');
    this._search.setAttribute('aria-modal', 'true');

    this._search.innerHTML = `
      <div class="mai-global-search-header">
        <span class="mai-global-search-icon" aria-hidden="true">${ICONS.search}</span>
        <input 
          type="text" 
          class="mai-global-search-input" 
          placeholder="Search memories, conversations, knowledge, entities..."
          autocomplete="off"
          spellcheck="false"
          aria-label="Global search"
        >
        <span class="mai-global-search-loading" style="display: none;" aria-hidden="true"></span>
      </div>
      <div class="mai-global-search-results"></div>
      <div class="mai-global-search-footer">
        <span>↑↓ Navigate • ↵ Open • Esc Close</span>
        <span><kbd>⌘</kbd><kbd>K</kbd> Command Palette</span>
      </div>
    `;

    this._input = this._search.querySelector('.mai-global-search-input');
    this._loadingIndicator = this._search.querySelector('.mai-global-search-loading');
    this._resultsContainer = this._search.querySelector('.mai-global-search-results');

    document.body.appendChild(this._overlay);
    document.body.appendChild(this._search);
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
        this._selectNextSection();
      }
    });

    // Overlay click
    this._overlay.addEventListener('click', this._boundOutsideClick);

    // Keyboard shortcuts
    document.addEventListener('keydown', this._boundKeydown);

    // Focus input on open
    this._overlay.addEventListener('click', () => this.close());
    this._search.addEventListener('click', (e) => e.stopPropagation());
  }

  _handleKeydown(e) {
    // Cmd/Ctrl + Shift + K to toggle
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'K') {
      if (e.target !== this._input) {
        e.preventDefault();
        this.toggle();
      }
    }
    
    // Cmd/Ctrl + K for command palette
    if ((e.metaKey || e.ctrlKey) && e.key === 'k' && !e.shiftKey) {
      if (e.target !== this._input) {
        e.preventDefault();
        this.close();
        if (window.MAICommandPalette) {
          const palette = new window.MAICommandPalette({ container: document.body });
          palette.open();
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

  async _performSearch(query) {
    if (!query.trim()) {
      this._searchResults = {};
      this._renderResults();
      return;
    }

    this._loadingIndicator.style.display = 'block';
    this._searchResults = {};

    // Search all providers in parallel
    const providerEntries = Object.entries(this.providers);
    const searchPromises = providerEntries.map(async ([providerId, provider]) => {
      if (!provider.search) return { providerId, results: [] };
      
      try {
        const results = await provider.search(query);
        return { providerId, results: results.slice(0, this.maxResultsPerSection) };
      } catch (error) {
        console.error(`Search provider ${providerId} failed:`, error);
        return { providerId, results: [], error: true };
      }
    });

    const results = await Promise.all(searchPromises);
    
    results.forEach(({ providerId, results: providerResults, error }) => {
      this._searchResults[providerId] = {
        results: providerResults,
        error,
        provider: this.providers[providerId]
      };
    });

    this._loadingIndicator.style.display = 'none';
    this._renderResults(query);
  }

  _renderResults(query = '') {
    this._resultsContainer.innerHTML = '';

    const providerEntries = Object.entries(this._searchResults);
    
    if (providerEntries.length === 0) {
      this._resultsContainer.innerHTML = `
        <div class="mai-global-search-empty">
          ${ICONS.search}
          <div>Start typing to search...</div>
        </div>
      `;
      return;
    }

    let hasResults = false;

    providerEntries.forEach(([providerId, data]) => {
      const provider = data.provider;
      const results = data.results || [];
      
      if (results.length === 0 && !data.error) return;
      hasResults = true;

      const sectionEl = document.createElement('div');
      sectionEl.className = 'mai-global-search-section';
      sectionEl.setAttribute('data-provider', providerId);
      
      const isError = data.error;
      const isLoading = results.length === 0 && !isError;

      sectionEl.innerHTML = `
        <div class="mai-global-search-section-header">
          <span class="mai-global-search-section-title">
            ${ICONS[provider.icon] || ICONS.file}
            ${provider.name}
          </span>
          ${!isError ? `
            <span class="mai-global-search-section-count">${results.length}</span>
          ` : `
            <span class="mai-global-search-section-count" style="color: var(--color-danger);">Error</span>
          `}
        </div>
        ${isLoading ? `
          <div class="mai-global-search-section-loading">
            <span class="mai-global-search-loading" style="width: 16px; height: 16px; border-width: 1.5px;"></span>
            Searching...
          </div>
        ` : isError ? `
          <div class="mai-global-search-section-empty">Search failed</div>
        ` : results.length === 0 ? `
          <div class="mai-global-search-section-empty">No results</div>
        ` : results.map((result, index) => this._renderResultItem(result, index, providerId, query)).join('')}
      `;
      
      this._resultsContainer.appendChild(sectionEl);
    });

    if (!hasResults) {
      this._resultsContainer.innerHTML = `
        <div class="mai-global-search-empty">
          ${ICONS.search}
          <div>No results found${query ? ` for "${this._escapeHtml(query)}"` : ''}</div>
        </div>
      `;
    }

    // Update selection
    this._updateSelection();
  }

  _renderResultItem(result, index, providerId, query) {
    const {
      id,
      title,
      description,
      type,
      score,
      timestamp,
      metadata,
      url,
      action
    } = result;

    const metaParts = [];
    if (type) metaParts.push(`<span class="mai-global-search-result-type">${type}</span>`);
    if (score !== undefined) metaParts.push(`<span class="mai-global-search-result-score">${Math.round(score * 100)}%</span>`);
    if (timestamp) metaParts.push(`<span class="mai-global-search-result-time">${this._formatTime(timestamp)}</span>`);

    return `
      <button class="mai-global-search-result ${index === this._selectedIndex && this._selectedSection === providerId ? 'selected' : ''}" 
              data-provider="${providerId}"
              data-index="${index}"
              data-result-id="${id}"
              role="option"
              aria-selected="${index === this._selectedIndex && this._selectedSection === providerId}">
        <span class="mai-global-search-result-icon" aria-hidden="true">${ICONS[this.providers[providerId]?.icon] || ICONS.file}</span>
        <div class="mai-global-search-result-content">
          <div class="mai-global-search-result-title">${this._highlightMatch(title || 'Untitled', query)}</div>
          ${description ? `<div class="mai-global-search-result-description">${this._highlightMatch(description, query)}</div>` : ''}
          ${metaParts.length > 0 ? `<div class="mai-global-search-result-meta">${metaParts.join('')}</div>` : ''}
        </div>
      </button>
    `;
  }

  _highlightMatch(text, query) {
    if (!query || !text) return this._escapeHtml(text);
    
    const match = fuzzyMatch(query, text);
    if (match.score === 0) return this._escapeHtml(text);
    
    let result = '';
    let lastIndex = 0;
    
    match.matches.forEach(index => {
      if (index >= 0 && index < text.length) {
        result += this._escapeHtml(text.slice(lastIndex, index));
        result += `<span class="mai-global-search-highlight">${this._escapeHtml(text[index])}</span>`;
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

  _formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  }

  _selectNext() {
    const sections = Object.keys(this._searchResults);
    if (sections.length === 0) return;

    const currentSection = this._selectedSection || sections[0];
    const currentResults = this._searchResults[currentSection]?.results || [];
    
    if (this._selectedIndex < currentResults.length - 1) {
      this._selectedIndex++;
    } else {
      // Move to next section
      const currentSectionIndex = sections.indexOf(currentSection);
      const nextSectionIndex = (currentSectionIndex + 1) % sections.length;
      this._selectedSection = sections[nextSectionIndex];
      this._selectedIndex = 0;
    }
    
    this._updateSelection();
    this._scrollToSelected();
  }

  _selectPrevious() {
    const sections = Object.keys(this._searchResults);
    if (sections.length === 0) return;

    const currentSection = this._selectedSection || sections[0];
    
    if (this._selectedIndex > 0) {
      this._selectedIndex--;
    } else {
      // Move to previous section
      const currentSectionIndex = sections.indexOf(currentSection);
      const prevSectionIndex = (currentSectionIndex - 1 + sections.length) % sections.length;
      this._selectedSection = sections[prevSectionIndex];
      this._selectedIndex = (this._searchResults[this._selectedSection]?.results?.length || 1) - 1;
    }
    
    this._updateSelection();
    this._scrollToSelected();
  }

  _selectNextSection() {
    const sections = Object.keys(this._searchResults);
    if (sections.length <= 1) return;

    const currentSection = this._selectedSection || sections[0];
    const currentSectionIndex = sections.indexOf(currentSection);
    const nextSectionIndex = (currentSectionIndex + 1) % sections.length;
    this._selectedSection = sections[nextSectionIndex];
    this._selectedIndex = 0;
    
    this._updateSelection();
    this._scrollToSelected();
  }

  _updateSelection() {
    // Remove all selected
    this._resultsContainer.querySelectorAll('.mai-global-search-result.selected').forEach(el => {
      el.classList.remove('selected');
      el.setAttribute('aria-selected', 'false');
    });

    // Add selected to current
    if (this._selectedSection) {
      const selectedEl = this._resultsContainer.querySelector(
        `.mai-global-search-result[data-provider="${this._selectedSection}"][data-index="${this._selectedIndex}"]`
      );
      if (selectedEl) {
        selectedEl.classList.add('selected');
        selectedEl.setAttribute('aria-selected', 'true');
      }
    }
  }

  _scrollToSelected() {
    const selectedEl = this._resultsContainer.querySelector('.mai-global-search-result.selected');
    if (selectedEl) {
      selectedEl.scrollIntoView({ block: 'nearest' });
    }
  }

  _executeSelected() {
    if (!this._selectedSection) return;
    
    const results = this._searchResults[this._selectedSection]?.results || [];
    const result = results[this._selectedIndex];
    if (!result) return;

    this.close();

    if (this.onResultClick) {
      this.onResultClick(result, this._selectedSection);
    }

    this.container.dispatchEvent(new CustomEvent('mai:searchresultclick', {
      detail: { result, provider: this._selectedSection },
      bubbles: true
    }));
  }

  /**
   * Open the global search
   */
  open() {
    if (this._open) return;
    this._open = true;
    this._overlay.classList.add('visible');
    this._search.classList.add('open');
    this._input.value = '';
    this._searchResults = {};
    this._selectedSection = null;
    this._selectedIndex = 0;
    this._renderResults();
    
    // Focus input after animation
    setTimeout(() => this._input.focus(), 100);

    if (this.onOpen) this.onOpen();
    this.container.dispatchEvent(new CustomEvent('mai:globalsearchopen', { bubbles: true }));
  }

  /**
   * Close the global search
   */
  close() {
    if (!this._open) return;
    this._open = false;
    this._overlay.classList.remove('visible');
    this._search.classList.remove('open');
    this._input.blur();

    if (this.onClose) this.onClose();
    this.container.dispatchEvent(new CustomEvent('mai:globalsearchclose', { bubbles: true }));
  }

  /**
   * Toggle the global search
   */
  toggle() {
    if (this._open) this.close();
    else this.open();
  }

  /**
   * Register a search provider
   * @param {string} id 
   * @param {Object} provider 
   */
  registerProvider(id, provider) {
    this.providers[id] = provider;
  }

  /**
   * Unregister a search provider
   * @param {string} id 
   */
  unregisterProvider(id) {
    delete this.providers[id];
  }

  /**
   * Set search query programmatically
   * @param {string} query 
   */
  setQuery(query) {
    this._input.value = query;
    this._debouncedSearch(query);
  }

  /**
   * Check if search is open
   * @returns {boolean}
   */
  isOpen() {
    return this._open;
  }

  /**
   * Destroy the global search
   */
  destroy() {
    document.removeEventListener('keydown', this._boundKeydown);
    this._overlay.removeEventListener('click', this._boundOutsideClick);
    this._overlay.remove();
    this._search.remove();
  }
}

// ============================================================================
// AUTO-INITIALIZATION
// ============================================================================

if (typeof window !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    // Global instance for keyboard shortcuts
    if (!window._maiGlobalSearch) {
      window._maiGlobalSearch = new MAIGlobalSearch({ container: document.body });
    }
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MAIGlobalSearch, DEFAULT_PROVIDERS, fuzzyMatch };
}

if (typeof window !== 'undefined') {
  window.MAIGlobalSearch = MAIGlobalSearch;
}

export { MAIGlobalSearch, DEFAULT_PROVIDERS, fuzzyMatch };
export default MAIGlobalSearch;