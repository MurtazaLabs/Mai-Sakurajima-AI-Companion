/**
 * MAI App Shell - Main Application Shell
 * Integrates Sidebar, Topbar, Bottombar, Right Panel, and Page Transitions
 * 
 * Usage:
 * import { MAIAppShell } from './app-shell.js';
 * const app = new MAIAppShell({ container: '#app' });
 * app.navigate('chat');
 * app.setStatus('listening');
 */

// ============================================================================
// IMPORTS (will be available globally or via modules)
// ============================================================================

// These will be loaded as scripts or modules
// import { MAISidebar } from './sidebar.js';
// import { MAITopbar } from './topbar.js';
// import { MAIBottombar } from './bottombar.js';
// import { MAIRightPanel } from './right-panel.js';
// import { MAIStatusIndicator } from './mai-status-indicator.js';
// import { MAIPageTransitions } from './page-transitions.js';
// import { MAICommandPalette } from './command-palette.js';
// import { MAIGlobalSearch } from './global-search.js';

// ============================================================================
// DEFAULT PAGE REGISTRY
// ============================================================================

const DEFAULT_PAGES = {
  presence: { title: 'Presence', icon: 'home', component: null },
  chat: { title: 'Chat', icon: 'message-square', component: null },
  memory: { title: 'Memory', icon: 'database', component: null },
  graph: { title: 'Graph', icon: 'git-branch', component: null },
  reasoning: { title: 'Reasoning', icon: 'brain', component: null },
  agency: { title: 'Agency', icon: 'zap', component: null },
  voice: { title: 'Voice', icon: 'mic', component: null },
  tasks: { title: 'Tasks', icon: 'check-square', component: null },
  system: { title: 'System', icon: 'cpu', component: null },
  permissions: { title: 'Permissions', icon: 'shield', component: null }
};

// ============================================================================
// MAI APP SHELL CLASS
// ============================================================================

class MAIAppShell {
  /**
   * Create a new MAI App Shell
   * @param {Object} options
   * @param {string|HTMLElement} options.container - Root container selector or element
   * @param {Object} options.pages - Page registry
   * @param {string} options.defaultPage - Default page to load
   * @param {Object} options.components - Component instances (sidebar, topbar, etc.)
   * @param {Function} options.onNavigate - Navigation callback
   * @param {Function} options.onStatusChange - Status change callback
   * @param {boolean} options.enableTransitions - Enable page transitions (default: true)
   * @param {boolean} options.enableCommandPalette - Enable command palette (default: true)
   * @param {boolean} options.enableGlobalSearch - Enable global search (default: true)
   */
  constructor(options = {}) {
    this.container = typeof options.container === 'string'
      ? document.querySelector(options.container)
      : options.container;

    if (!this.container) {
      throw new Error('MAIAppShell: Container not found');
    }

    this.pages = options.pages || DEFAULT_PAGES;
    this.defaultPage = options.defaultPage || 'presence';
    this.currentPage = null;
    this.previousPage = null;
    this.enableTransitions = options.enableTransitions !== false;
    this.enableCommandPalette = options.enableCommandPalette !== false;
    this.enableGlobalSearch = options.enableGlobalSearch !== false;

    this.onNavigate = options.onNavigate || null;
    this.onStatusChange = options.onStatusChange || null;

    // Component instances
    this.sidebar = options.components?.sidebar || null;
    this.topbar = options.components?.topbar || null;
    this.bottombar = options.components?.bottombar || null;
    this.rightPanel = options.components?.rightPanel || null;
    this.pageTransitions = options.components?.pageTransitions || null;
    this.commandPalette = options.components?.commandPalette || null;
    this.globalSearch = options.components?.globalSearch || null;

    // State
    this._pageComponents = new Map();
    this._boundHandleKeydown = this._handleKeydown.bind(this);
    this._boundHandleResize = this._debounce(this._handleResize.bind(this), 150);

    this._injectStyles();
    this._render();
    this._initComponents();
    this._bindEvents();
    this._registerPages();

    // Navigate to default page
    this.navigate(this.defaultPage);
  }

  _injectStyles() {
    if (!document.getElementById('mai-app-shell-styles')) {
      const style = document.createElement('style');
      style.id = 'mai-app-shell-styles';
      style.textContent = `
        .mai-app-shell {
          display: grid;
          grid-template-rows: var(--topbar-height, 48px) 1fr var(--bottombar-height, 64px);
          grid-template-columns: var(--sidebar-width-collapsed, 72px) 1fr var(--right-panel-width-collapsed, 0);
          height: 100vh;
          width: 100vw;
          overflow: hidden;
          background: var(--color-bg-primary, #0A0B0F);
          font-family: var(--font-sans, 'Inter', 'Manrope', 'Space Grotesk', system-ui, sans-serif);
          color: var(--color-text-primary, #F2F5FA);
          transition: grid-template-columns 300ms cubic-bezier(0.23, 1, 0.32, 1);
        }

        .mai-app-shell.sidebar-expanded {
          grid-template-columns: var(--sidebar-width-expanded, 220px) 1fr var(--right-panel-width-collapsed, 0);
        }

        .mai-app-shell.right-panel-open {
          grid-template-columns: var(--sidebar-width-collapsed, 72px) 1fr var(--right-panel-width, 320px);
        }

        .mai-app-shell.sidebar-expanded.right-panel-open {
          grid-template-columns: var(--sidebar-width-expanded, 220px) 1fr var(--right-panel-width, 320px);
        }

        .mai-app-shell .mai-sidebar {
          grid-row: 1 / -1;
          grid-column: 1;
        }

        .mai-app-shell .mai-topbar {
          grid-row: 1;
          grid-column: 2 / -1;
        }

        .mai-app-shell .mai-main {
          grid-row: 2;
          grid-column: 2;
          overflow: auto;
        }

        .mai-app-shell .mai-right-panel {
          grid-row: 1 / -1;
          grid-column: 3;
        }

        .mai-app-shell .mai-bottombar {
          grid-row: 3;
          grid-column: 1 / -1;
        }

        .mai-page {
          height: 100%;
          width: 100%;
          overflow: auto;
        }

        .mai-page-enter {
          animation: mai-page-enter 500ms cubic-bezier(0.23, 1, 0.32, 1) forwards;
        }

        .mai-page-exit {
          animation: mai-page-exit 250ms cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }

        @keyframes mai-page-enter {
          from { opacity: 0; transform: translateY(20px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }

        @keyframes mai-page-exit {
          from { opacity: 1; transform: translateY(0) scale(1); }
          to { opacity: 0; transform: translateY(-20px) scale(0.98); }
        }

        @media (prefers-reduced-motion: reduce) {
          .mai-app-shell,
          .mai-page {
            transition: none !important;
            animation: none !important;
          }
        }
      `;
      document.head.appendChild(style);
    }
  }

  _render() {
    this.container.innerHTML = '';
    this.container.className = 'mai-app-shell';
    this.container.setAttribute('role', 'application');

    this.container.innerHTML = `
      <aside class="mai-sidebar" data-mai-sidebar data-active="${this.defaultPage}"></aside>
      <header class="mai-topbar" data-mai-topbar></header>
      <main class="mai-main" role="main"></main>
      <aside class="mai-right-panel" data-mai-right-panel></aside>
      <footer class="mai-bottombar" data-mai-bottombar></footer>
    `;

    // Store references to child containers
    this._sidebarContainer = this.container.querySelector('.mai-sidebar');
    this._topbarContainer = this.container.querySelector('.mai-topbar');
    this._mainContainer = this.container.querySelector('.mai-main');
    this._rightPanelContainer = this.container.querySelector('.mai-right-panel');
    this._bottombarContainer = this.container.querySelector('.mai-bottombar');
  }

  _initComponents() {
    // Initialize sidebar
    if (!this.sidebar && window.MAISidebar) {
      this.sidebar = new window.MAISidebar({
        container: this._sidebarContainer,
        onNavigate: (itemId) => this.navigate(itemId)
      });
    }

    // Initialize topbar
    if (!this.topbar && window.MAITopbar) {
      this.topbar = new window.MAITopbar({
        container: this._topbarContainer,
        onCommand: () => this.toggleCommandPalette(),
        onGlobalSearch: () => this.toggleGlobalSearch(),
        onNotificationClick: () => this._handleNotifications(),
        onSettingsClick: () => this.navigate('system'),
        onProfileClick: () => this._handleProfile()
      });
    }

    // Initialize bottombar
    if (!this.bottombar && window.MAIBottombar) {
      this.bottombar = new window.MAIBottombar({
        container: this._bottombarContainer,
        onCommand: (cmd) => this.executeCommand(cmd),
        onCommandModeChange: (enabled) => this._handleCommandModeChange(enabled)
      });
    }

    // Initialize right panel
    if (!this.rightPanel && window.MAIRightPanel) {
      this.rightPanel = new window.MAIRightPanel({
        container: this._rightPanelContainer
      });
    }

    // Initialize page transitions
    if (!this.pageTransitions && window.MAIPageTransitions && this.enableTransitions) {
      this.pageTransitions = new window.MAIPageTransitions({
        container: this._mainContainer
      });
    }

    // Initialize command palette
    if (!this.commandPalette && window.MAICommandPalette && this.enableCommandPalette) {
      this.commandPalette = new window.MAICommandPalette({
        container: document.body,
        onAction: (action) => this.executeCommand(action),
        onNavigate: (page) => this.navigate(page)
      });
    }

    // Initialize global search
    if (!this.globalSearch && window.MAIGlobalSearch && this.enableGlobalSearch) {
      this.globalSearch = new window.MAIGlobalSearch({
        container: document.body,
        onResultClick: (result) => this._handleSearchResult(result)
      });
    }
  }

  _bindEvents() {
    // Keyboard shortcuts
    document.addEventListener('keydown', this._boundHandleKeydown);

    // Resize handler
    window.addEventListener('resize', this._boundHandleResize);

    // Sidebar events
    if (this.sidebar) {
      this.sidebar.container.addEventListener('mai:navigate', (e) => {
        this.navigate(e.detail.itemId);
      });
      this.sidebar.container.addEventListener('mai:sidebartoggle', (e) => {
        this.container.classList.toggle('sidebar-expanded', !e.detail.collapsed);
      });
    }

    // Right panel events
    if (this.rightPanel) {
      this.rightPanel.container.addEventListener('mai:panelopen', () => {
        this.container.classList.add('right-panel-open');
      });
      this.rightPanel.container.addEventListener('mai:panelclose', () => {
        this.container.classList.remove('right-panel-open');
      });
    }

    // Command palette events
    if (this.commandPalette) {
      document.addEventListener('mai:command', () => this.toggleCommandPalette());
      document.addEventListener('mai:globalsearch', () => this.toggleGlobalSearch());
    }

    // Topbar events
    if (this.topbar) {
      this.topbar.container.addEventListener('mai:menutoggle', () => this.sidebar?.toggle());
      this.topbar.container.addEventListener('mai:mictoggle', (e) => {
        this.container.dispatchEvent(new CustomEvent('mai:mictoggle', { detail: e.detail }));
      });
    }

    // Bottombar events
    if (this.bottombar) {
      this.bottombar.container.addEventListener('mai:commandmodetoggle', (e) => {
        this.container.classList.toggle('command-mode', e.detail.commandMode);
      });
    }
  }

  _registerPages() {
    // Register built-in page renderers
    Object.entries(this.pages).forEach(([pageId, config]) => {
      if (config.render) {
        this._pageComponents.set(pageId, config.render);
      }
    });
  }

  _handleKeydown(e) {
    // Global shortcuts
    if (e.target.matches('input, textarea, [contenteditable]')) return;

    // Navigation shortcuts (Cmd/Ctrl + 1-9)
    if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '9') {
      const index = parseInt(e.key) - 1;
      const pageIds = Object.keys(this.pages);
      if (pageIds[index]) {
        e.preventDefault();
        this.navigate(pageIds[index]);
      }
    }
  }

  _handleResize() {
    // Handle responsive behavior
    const wasMobile = this._wasMobile;
    this._wasMobile = window.innerWidth <= 768;

    if (wasMobile !== this._wasMobile) {
      if (this.sidebar) {
        this.sidebar.mobile = this._wasMobile;
        if (this._wasMobile) this.sidebar.collapse();
      }
      if (this.rightPanel) {
        if (this._wasMobile) this.rightPanel.close();
      }
    }
  }

  _debounce(fn, delay) {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn(...args), delay);
    };
  }

  /**
   * Navigate to a page
   * @param {string} pageId 
   * @param {Object} params - Route parameters
   */
  async navigate(pageId, params = {}) {
    if (!this.pages[pageId]) {
      console.warn(`MAIAppShell: Page "${pageId}" not found`);
      return;
    }

    if (this.currentPage === pageId) return;

    this.previousPage = this.currentPage;
    const pageConfig = this.pages[pageId];

    // Update sidebar active state
    if (this.sidebar) {
      this.sidebar.setActiveItem(pageId);
    }

    // Trigger page exit animation
    if (this.currentPage && this.pageTransitions && this.enableTransitions) {
      await this.pageTransitions.exit(this.currentPage);
    }

    // Render new page
    this.currentPage = pageId;
    await this._renderPage(pageId, params);

    // Trigger page enter animation
    if (this.pageTransitions && this.enableTransitions) {
      await this.pageTransitions.enter(pageId);
    }

    // Update document title
    document.title = `${pageConfig.title} • MAI`;

    // Update URL hash
    history.replaceState({ page: pageId, params }, '', `#${pageId}`);

    // Trigger callbacks
    if (this.onNavigate) {
      this.onNavigate(pageId, params, this.previousPage);
    }

    this.container.dispatchEvent(new CustomEvent('mai:navigate', {
      detail: { pageId, params, previousPage: this.previousPage },
      bubbles: true
    }));
  }

  async _renderPage(pageId, params) {
    const pageConfig = this.pages[pageId];
    let pageElement;

    if (pageConfig.component) {
      // React/Vue component
      pageElement = pageConfig.component({ params, app: this });
    } else if (pageConfig.render) {
      // Render function
      pageElement = pageConfig.render({ params, app: this });
    } else {
      // Default: create empty page container
      pageElement = document.createElement('div');
      pageElement.className = 'mai-page';
      pageElement.innerHTML = `
        <div class="mai-page-header">
          <h1 class="mai-page-title">${pageConfig.title}</h1>
        </div>
        <div class="mai-page-content">
          <div class="mai-right-panel-empty">
            <span class="mai-right-panel-empty-icon">${this._getPageIcon(pageConfig.icon)}</span>
            <div>${pageConfig.title} page - implementation pending</div>
          </div>
        </div>
      `;
    }

    // Apply page transition classes
    if (this.enableTransitions) {
      pageElement.classList.add('mai-page-enter');
    }

    // Replace main content
    this._mainContainer.innerHTML = '';
    this._mainContainer.appendChild(pageElement);

    // Initialize page-specific logic
    if (pageConfig.init) {
      await pageConfig.init({ params, app: this, container: pageElement });
    }
  }

  _getPageIcon(iconName) {
    const icons = {
      home: '🏠',
      'message-square': '💬',
      database: '🗄️',
      'git-branch': '🌐',
      brain: '🧠',
      zap: '⚡',
      mic: '🎤',
      'check-square': '✅',
      cpu: '💻',
      shield: '🛡️'
    };
    return icons[iconName] || '📄';
  }

  /**
   * Set MAI status across all indicators
   * @param {string} status 
   */
  setStatus(status) {
    if (this.topbar) this.topbar.setStatus(status);
    if (this.bottombar) {
      // Update bottombar status items if needed
    }
    if (this.rightPanel) {
      // Could update right panel status section
    }

    if (this.onStatusChange) {
      this.onStatusChange(status);
    }

    this.container.dispatchEvent(new CustomEvent('mai:statuschange', {
      detail: { status },
      bubbles: true
    }));
  }

  /**
   * Execute a command
   * @param {string} command 
   */
  executeCommand(command) {
    this.container.dispatchEvent(new CustomEvent('mai:command', {
      detail: { command },
      bubbles: true
    }));

    // Built-in commands
    if (command.startsWith('/')) {
      this._handleBuiltinCommand(command);
    }
  }

  _handleBuiltinCommand(command) {
    const parts = command.slice(1).split(' ');
    const cmd = parts[0].toLowerCase();
    const args = parts.slice(1);

    switch (cmd) {
      case 'help':
        this._showHelp();
        break;
      case 'nav':
      case 'go':
        if (args[0]) this.navigate(args[0]);
        break;
      case 'status':
        if (args[0]) this.setStatus(args[0]);
        break;
      case 'theme':
        // Theme handling
        break;
      case 'clear':
        if (this.bottombar) this.bottombar._input.value = '';
        break;
      default:
        console.log(`Unknown command: ${cmd}`);
    }
  }

  _showHelp() {
    const help = [
      'Available commands:',
      '/help - Show this help',
      '/nav <page> - Navigate to page',
      '/go <page> - Alias for nav',
      '/status <state> - Set MAI status',
      '/theme <dark|light> - Set theme',
      '/clear - Clear command input'
    ];
    console.log(help.join('\n'));
    
    // Could show in a toast or modal
    if (this.commandPalette) {
      this.commandPalette.showHelp(help);
    }
  }

  _handleNotifications() {
    // Open notifications panel in right panel
    if (this.rightPanel) {
      this.rightPanel.open();
      // Could navigate to notifications section
    }
  }

  _handleProfile() {
    // Open profile/settings
    this.navigate('system');
  }

  _handleSearchResult(result) {
    if (result.type === 'page') {
      this.navigate(result.id);
    } else if (result.type === 'action') {
      this.executeCommand(result.action);
    }
  }

  _handleCommandModeChange(enabled) {
    this.container.classList.toggle('command-mode', enabled);
  }

  /**
   * Toggle command palette
   */
  toggleCommandPalette() {
    if (this.commandPalette) {
      this.commandPalette.toggle();
    }
  }

  /**
   * Toggle global search
   */
  toggleGlobalSearch() {
    if (this.globalSearch) {
      this.globalSearch.toggle();
    }
  }

  /**
   * Register a page
   * @param {string} pageId 
   * @param {Object} config 
   */
  registerPage(pageId, config) {
    this.pages[pageId] = config;
    if (config.render) {
      this._pageComponents.set(pageId, config.render);
    }
  }

  /**
   * Get current page
   * @returns {string|null}
   */
  getCurrentPage() {
    return this.currentPage;
  }

  /**
   * Get previous page
   * @returns {string|null}
   */
  getPreviousPage() {
    return this.previousPage;
  }

  /**
   * Go back to previous page
   */
  goBack() {
    if (this.previousPage) {
      this.navigate(this.previousPage);
    }
  }

  /**
   * Toggle sidebar
   */
  toggleSidebar() {
    this.sidebar?.toggle();
  }

  /**
   * Toggle right panel
   */
  toggleRightPanel() {
    this.rightPanel?.toggle();
  }

  /**
   * Destroy the app shell
   */
  destroy() {
    document.removeEventListener('keydown', this._boundHandleKeydown);
    window.removeEventListener('resize', this._boundHandleResize);
    
    [this.sidebar, this.topbar, this.bottombar, this.rightPanel, 
     this.pageTransitions, this.commandPalette, this.globalSearch].forEach(c => {
      if (c && c.destroy) c.destroy();
    });

    this.container.innerHTML = '';
    this.container.className = '';
  }
}

// ============================================================================
// AUTO-INITIALIZATION
// ============================================================================

if (typeof window !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-mai-app-shell]').forEach(el => {
      const defaultPage = el.getAttribute('data-default-page') || 'presence';
      new MAIAppShell({ container: el, defaultPage });
    });
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MAIAppShell, DEFAULT_PAGES };
}

if (typeof window !== 'undefined') {
  window.MAIAppShell = MAIAppShell;
}

export { MAIAppShell, DEFAULT_PAGES };
export default MAIAppShell;