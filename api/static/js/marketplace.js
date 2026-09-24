// marketplace.js - Plugin Marketplace UI
import { showToast } from './notifications.js';

class MarketplaceUI {
    constructor() {
        this.plugins = [];
        this.installedPlugins = new Map();
        this.currentPage = 1;
        this.pageSize = 12;
        this.filters = {
            query: '',
            category: '',
            sort: 'popular',
            status: ''
        };
        this.modalPlugin = null;
        
        this.init();
    }

    async init() {
        // Load installed plugins first
        await this.loadInstalledPlugins();
        
        // Load marketplace plugins
        await this.loadMarketplacePlugins();
        
        // Setup event listeners
        this.bindEvents();
        
        // Check for deep link
        this.handleDeepLink();
    }

    async loadInstalledPlugins() {
        try {
            const response = await fetch('/api/plugins/installed');
            if (response.ok) {
                const plugins = await response.json();
                this.installedPlugins = new Map(plugins.map(p => [p.name, p]));
                this.updateInstalledStatus();
            }
        } catch (e) {
            console.error('Failed to load installed plugins:', e);
        }
    }

    async loadMarketplacePlugins() {
        this.showLoading();
        try {
            const params = new URLSearchParams({
                q: this.filters.query,
                category: this.filters.category || '',
                sort: this.filters.sort,
                status: this.filters.status || '',
                page: this.currentPage,
                limit: this.pageSize
            });
            
            const response = await fetch(`/api/plugins/marketplace/search?${new URLSearchParams(this.filters)}`);
            if (!response.ok) throw new Error('Failed to load marketplace');
            
            this.plugins = await response.json();
            this.renderPlugins();
        } catch (e) {
            console.error('Failed to load marketplace:', e);
            this.showError('Failed to load marketplace');
        }
    }

    showLoading() {
        const grid = document.getElementById('plugin-grid');
        grid.innerHTML = Array(6).fill(0).map(() => `
            <div class="plugin-card loading">
                <div class="skeleton skeleton-icon"></div>
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-text"></div>
                <div class="skeleton skeleton-text"></div>
            </div>
        `).join('');
    }

    updateInstalledStatus() {
        document.querySelectorAll('.plugin-card').forEach(card => {
            const name = card.dataset.pluginName;
            const installed = this.installedPlugins.has(name);
            const enabled = this.installedPlugins.get(name)?.state === 'enabled';
            
            card.classList.toggle('installed', installed);
            const actionBtn = card.querySelector('.plugin-action-btn');
            if (actionBtn) {
                actionBtn.textContent = installed ? (this.installedPlugins.get(name)?.state === 'enabled' ? 'Disable' : 'Enable') : 'Install';
                actionBtn.classList.toggle('btn-primary', !installed);
                actionBtn.classList.toggle('btn-secondary', installed);
                actionBtn.dataset.action = installed ? 'disable' : 'install';
            }
        });
    }

    renderPlugins() {
        const grid = document.getElementById('plugin-grid');
        const countEl = document.getElementById('result-count');
        
        if (this.plugins.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">🔍</div>
                    <h3>No plugins found</h3>
                    <p style="color: var(--text-muted); margin-top: 8px;">
                        Try adjusting your search or filters
                    </p>
                </div>
            `;
            document.getElementById('pagination').style.display = 'none';
            return;
        }

        document.getElementById('pagination').style.display = 'flex';
        
        grid.innerHTML = this.plugins.map(plugin => this.renderPluginCard(plugin)).join('');
        countEl.textContent = `${this.plugins.length} plugins found`;
        
        // Bind card actions
        grid.querySelectorAll('.plugin-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.plugin-action-btn')) {
                    this.openPluginModal(card.dataset.pluginName);
                }
            });
            
            card.querySelectorAll('.plugin-action-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const name = btn.dataset.pluginName;
                    const action = btn.dataset.action;
                    this.handlePluginAction(name, action);
                });
            });
        });
        
        this.updatePagination();
    }

    renderPluginCard(plugin) {
        const installed = this.installedPlugins.has(plugin.name);
        const enabled = this.installedPlugins.get(plugin.name)?.state === 'enabled';
        const status = installed ? (enabled ? 'enabled' : 'installed') : 'available';
        
        const tags = (plugin.tags || []).slice(0, 3).map(t => 
            `<span class="plugin-tag">${t}</span>`
        ).join('');
        
        const stars = '★'.repeat(Math.floor(plugin.rating || 0)) + '☆'.repeat(5 - Math.floor(plugin.rating || 0));
        
        return `
            <article class="plugin-card ${this.installedPlugins.has(plugin.name) ? 'installed' : ''}" 
                     data-plugin-name="${plugin.name}"
                     data-plugin-version="${plugin.version}">
                <div class="plugin-header">
                    <div class="plugin-icon">${this.getPluginIcon(plugin.name)}</div>
                    <div class="plugin-info">
                        <h3 class="plugin-name">${plugin.name}</h3>
                        <div class="plugin-meta">
                            <span class="plugin-version">v${plugin.version}</span>
                            <span class="plugin-tag">${plugin.tags?.[0] || 'utility'}</span>
                        </div>
                    </div>
                </div>
                <p class="plugin-description">${plugin.description}</p>
                <div class="plugin-footer">
                    <div class="plugin-meta">
                        <span class="plugin-rating">
                            <span class="plugin-stars">${'★'.repeat(Math.floor(plugin.rating || 0))}${'☆'.repeat(5 - Math.floor(plugin.rating || 0))}</span>
                            <span class="rating-value">${(plugin.rating || 0).toFixed(1)}</span>
                        </span>
                        <span class="plugin-downloads">${this.formatNumber(plugin.downloads || 0)} downloads</span>
                    </div>
                    <div class="plugin-actions">
                        <button class="btn btn-sm plugin-action-btn ${this.installedPlugins.has(plugin.name) ? 'btn-secondary' : 'btn-primary'}"
                                data-plugin-name="${plugin.name}"
                                data-action="${this.installedPlugins.has(plugin.name) ? 'disable' : 'install'}">
                            ${this.installedPlugins.has(plugin.name) ? 'Disable' : 'Install'}
                        </button>
                        <button class="btn btn-sm btn-secondary" 
                                data-plugin-name="${plugin.name}"
                                data-action="detail"
                                title="View details">
                            Details
                        </button>
                    </div>
                </article>
        `;
    }

    getPluginIcon(name) {
        const icons = {
            weather: '🌤️',
            calendar: '📅',
            news: '📰',
            system_monitor: '📊',
            web_scraper: '🕷️',
            news: '📰'
        };
        return icons[name] || '📦';
    }

    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    async openPluginModal(name) {
        const plugin = this.plugins.find(p => p.name === name) || 
                       this.installedPlugins.get(name)?.manifest;
        if (!plugin) return;

        this.modalPlugin = name;
        const modal = document.getElementById('plugin-modal');
        const modalBody = document.getElementById('modal-body');
        const modalFooter = document.getElementById('modal-footer');

        const installed = this.installedPlugins.has(name);
        const record = this.installedPlugins.get(name);
        const enabled = record?.state === 'enabled';

        modalBody.innerHTML = this.renderModalBody(name, installed);
        modalFooter.innerHTML = this.renderModalFooter(name, installed);

        document.getElementById('modal-plugin-name').textContent = name;
        document.getElementById('modal-version').textContent = `v${this.plugins.find(p => p.name === name)?.version || '1.0.0'}`;
        document.getElementById('modal-plugin-icon').textContent = this.getPluginIcon(name);

        document.getElementById('plugin-modal').style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Bind modal actions
        this.bindModalActions();
    }

    renderModalBody(name, installed) {
        // Find plugin data
        const plugin = this.plugins.find(p => p.name === name) || 
                       this.installedPlugins.get(name)?.manifest;
        
        if (!plugin) return '<div class="no-data">Plugin details not available</div>';

        const permissions = plugin.permissions || {};
        const installed = this.installedPlugins.has(name);
        const record = this.installedPlugins.get(name);
        const enabled = record?.state === 'enabled';

        return `
            <div class="plugin-detail">
                <div class="detail-section">
                    <h3>Description</h3>
                    <p>${plugin.description}</p>
                </div>

                <div class="detail-section">
                    <h3>Permissions</h3>
                    <div class="permission-list">
                        ${this.renderPermissionBadge('fs:read', 'Filesystem Read', permissions.filesystem !== 'none')}
                        ${this.renderPermissionBadge('fs:write', 'Filesystem Write', permissions.filesystem === 'write' || permissions.filesystem === 'full')}
                        ${this.renderPermissionBadge('net:outbound', 'Network Outbound', permissions.network === 'outbound' || permissions.network === 'full')}
                        ${this.renderPermissionBadge('net:inbound', 'Network Inbound', permissions.network === 'inbound' || permissions.network === 'full')}
                        ${this.renderPermissionBadge('exec:subprocess', 'Execute Subprocess', permissions.execution === 'subprocess' || permissions.execution === 'full')}
                        ${this.renderPermissionBadge('exec:eval', 'Code Evaluation', permissions.execution === 'eval' || permissions.execution === 'full')}
                        ${permissions.api_access?.map(api => this.renderPermissionBadge(`api:${api}`, `API: ${api}`, true)).join('') || ''}
                    </div>
                </div>

                <div class="detail-section">
                    <h3>Metadata</h3>
                    <div class="detail-meta">
                        <div class="meta-item">
                            <div class="meta-label">Version</div>
                            <div class="meta-value">${this.plugins.find(p => p.name === name)?.version || '1.0.0'}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Author</div>
                            <div class="meta-value">${plugin.author || 'Mai AI Team'}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">License</div>
                            <div class="meta-value">${plugin.license || 'MIT'}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Min MAI Version</div>
                            <div class="meta-value">${plugin.min_mai_version || '1.0.0'}</div>
                        </div>
                    </div>
                </div>

                ${plugin.readme ? `
                <div class="detail-section">
                    <h3>Documentation</h3>
                    <div class="readme-content">${this.renderMarkdown(plugin.readme)}</div>
                </div>
                ` : ''}
            </div>
        `;
    }

    renderPermissionBadge(perm, label, granted) {
        return `
            <span class="permission-badge ${granted ? 'has-permission' : ''}">
                <span class="dot"></span>
                ${label}
            </span>
        `;
    }

    renderModalFooter(name, installed) {
        const enabled = this.installedPlugins.get(name)?.state === 'enabled';
        return `
            <button class="btn btn-secondary" data-action="close-modal">Close</button>
            ${!installed ? `
                <button class="btn btn-primary" data-action="install" data-name="${name}">
                    Install
                </button>
            ` : `
                <button class="btn btn-secondary" data-action="${enabled ? 'disable' : 'enable'}" data-name="${name}">
                    ${enabled ? 'Disable' : 'Enable'}
                </button>
                <button class="btn btn-danger" data-action="uninstall" data-name="${name}">
                    Uninstall
                </button>
            `}
        `;
    }

    renderMarkdown(text) {
        // Simple markdown renderer for readme
        return text
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/gim, '<em>$1</em>')
            .replace(/`(.*?)`/gim, '<code>$1</code>')
            .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
            .replace(/^\- (.*$)/gim, '<li>$1</li>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
    }

    bindModalActions() {
        document.getElementById('modal-close').onclick = () => this.closeModal();
        document.getElementById('plugin-modal').onclick = (e) => {
            if (e.target === document.getElementById('plugin-modal')) this.closeModal();
        };
        
        document.getElementById('modal-footer').querySelectorAll('button').forEach(btn => {
            btn.onclick = (e) => {
                const action = btn.dataset.action;
                const name = btn.dataset.name;
                this.handlePluginAction(name, action);
                if (action !== 'detail') this.closeModal();
            };
        });
    }

    closeModal() {
        document.getElementById('plugin-modal').style.display = 'none';
        document.body.style.overflow = '';
        this.modalPlugin = null;
    }

    handlePluginAction(name, action) {
        switch (action) {
            case 'install':
                this.installPlugin(name);
                break;
            case 'enable':
                this.enablePlugin(name);
                break;
            case 'disable':
                this.disablePlugin(name);
                break;
            case 'uninstall':
                if (confirm(`Uninstall ${name}? This will remove all plugin data.`)) {
                    this.uninstallPlugin(name);
                }
                break;
            case 'detail':
                this.openPluginDetail(name);
                break;
        }
    }

    async installPlugin(name) {
        this.showToast(`Installing ${name}...`, 'info');
        try {
            const response = await fetch('/api/plugins/marketplace/install', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, version: 'latest' })
            });
            const result = await response.json();
            if (result.success) {
                this.showToast(result.message, 'success');
                this.loadInstalledPlugins();
                this.loadMarketplacePlugins();
            } else {
                this.showToast(result.error || 'Install failed', 'error');
            }
        } catch (e) {
            this.showToast('Install failed: ' + e.message, 'error');
        }
    }

    async enablePlugin(name) {
        try {
            const response = await fetch(`/api/plugins/marketplace/${name}/enable`, {
                method: 'POST'
            });
            const result = await response.json();
            if (result.success) {
                this.showToast(result.message, 'success');
                this.loadInstalledPlugins();
                this.updateInstalledStatus();
            } else {
                this.showToast(result.message || 'Enable failed', 'error');
            }
        } catch (e) {
            this.showToast('Enable failed: ' + e.message, 'error');
        }
    }

    async disablePlugin(name) {
        try {
            const response = await fetch(`/api/plugins/marketplace/${name}/disable`, {
                method: 'POST'
            });
            const result = await response.json();
            if (result.success) {
                this.showToast(result.message, 'success');
                this.loadInstalledPlugins();
                this.updateInstalledStatus();
            } else {
                this.showToast(result.message || 'Disable failed', 'error');
            }
        } catch (e) {
            this.showToast('Disable failed: ' + e.message, 'error');
        }
    }

    async uninstallPlugin(name) {
        try {
            const response = await fetch(`/api/plugins/marketplace/${name}/uninstall`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ purge: false })
            });
            const result = await response.json();
            if (result.success) {
                this.showToast(result.message, 'success');
                this.loadInstalledPlugins();
                this.loadMarketplacePlugins();
            } else {
                this.showToast(result.message || 'Uninstall failed', 'error');
            }
        } catch (e) {
            this.showToast('Uninstall failed: ' + e.message, 'error');
        }
    }

    openPluginDetail(name) {
        // Navigate to detail page
        window.location.href = `/marketplace/${name}`;
    }

    closeModal() {
        document.getElementById('plugin-modal').style.display = 'none';
        document.body.style.overflow = '';
    }

    bindEvents() {
        // Search
        const searchInput = document.getElementById('marketplace-search');
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.filters.query = e.target.value;
                this.currentPage = 1;
                this.loadMarketplacePlugins();
            }, 300);
        });

        // Filters
        document.getElementById('filter-category').addEventListener('change', (e) => {
            this.filters.category = e.target.value;
            this.currentPage = 1;
            this.loadMarketplacePlugins();
        });

        document.getElementById('filter-sort').addEventListener('change', (e) => {
            this.filters.sort = e.target.value;
            this.currentPage = 1;
            this.loadMarketplacePlugins();
        });

        document.getElementById('filter-status').addEventListener('change', (e) => {
            this.filters.status = e.target.value;
            this.currentPage = 1;
            this.loadMarketplacePlugins();
        });

        // Refresh button
        document.getElementById('btn-refresh-marketplace').addEventListener('click', () => {
            this.loadMarketplacePlugins();
        });

        // Pagination
        document.getElementById('btn-prev-page').addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadMarketplacePlugins();
            }
        });

        document.getElementById('btn-next-page').addEventListener('click', () => {
            this.currentPage++;
            this.loadMarketplacePlugins();
        });

        // Refresh button
        document.getElementById('btn-refresh-marketplace').addEventListener('click', () => {
            this.loadMarketplacePlugins();
        });
    }

    updatePagination() {
        const prevBtn = document.getElementById('btn-prev-page');
        const nextBtn = document.getElementById('btn-next-page');
        const pageInfo = document.getElementById('page-info');

        prevBtn.disabled = this.currentPage <= 1;
        nextBtn.disabled = this.plugins.length < this.pageSize;
        pageInfo.textContent = `Page ${this.currentPage}`;
    }

    handleDeepLink() {
        const path = window.location.pathname;
        if (path.startsWith('/marketplace/')) {
            const name = path.split('/').pop();
            if (name && name !== 'marketplace') {
                setTimeout(() => this.openPluginModal(name), 500);
            }
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        document.getElementById('toast-container').appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }

    showError(message) {
        const grid = document.getElementById('plugin-grid');
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
                <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                <h3>Failed to load</h3>
                <p style="color: var(--text-muted); margin-top: 8px;">${message}</p>
                <button class="btn btn-primary" onclick="window.location.reload()" style="margin-top: 16px;">Retry</button>
            </div>
        `;
    }

    showLoading() {
        const grid = document.getElementById('plugin-grid');
        grid.innerHTML = Array(6).fill(0).map(() => `
            <div class="plugin-card loading">
                <div class="skeleton skeleton-icon"></div>
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-text"></div>
                <div class="skeleton skeleton-text"></div>
            </div>
        `).join('');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.marketplaceUI = new MarketplaceUI();
});

// Export for module usage
export { MarketplaceUI };