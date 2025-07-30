// Dashboard Core Functions - Bassline Bot
// Main dashboard functionality and data management

class DashboardCore {
    constructor() {
        this.data = {};
        this.lastUpdate = null;
        this.updateInterval = null;
        this.wsManager = null;
        this.isInitialized = false;
    }

    // Initialize the dashboard
    async initialize() {
        try {
            console.log('Initializing dashboard...');
            
            // Initialize WebSocket connection
            this.wsManager = new WebSocketManager();
            await this.wsManager.connect();
            
            // Load initial data
            await this.loadInitialData();
            
            // Setup auto-refresh
            this.setupAutoRefresh();
            
            // Setup event listeners
            this.setupEventListeners();
            
            this.isInitialized = true;
            console.log('Dashboard initialized successfully');
            
        } catch (error) {
            console.error('Dashboard initialization failed:', error);
            this.showError('Failed to initialize dashboard: ' + error.message);
        }
    }

    // Load initial data from the server
    async loadInitialData() {
        try {
            console.log('Loading initial data...');
            
            // Load bot statistics
            const stats = await this.fetchData('/api/stats');
            this.updateBotStats(stats);
            
            // Load server information
            const servers = await this.fetchData('/api/guilds');
            this.updateServerOverview(servers);
            
            // Load system information
            const system = await this.fetchData('/api/system');
            this.updateSystemInfo(system);
            
            // Load health check
            const health = await this.fetchData('/api/health');
            this.updateHealthStatus(health);
            
            this.lastUpdate = new Date();
            this.updateLastUpdateTime();
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showError('Failed to load dashboard data');
        }
    }

    // Fetch data from API endpoint
    async fetchData(endpoint) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Failed to fetch ${endpoint}:`, error);
            throw error;
        }
    }

    // Update bot statistics display
    updateBotStats(stats) {
        const container = document.getElementById('bot-stats');
        if (!container || !stats) return;

        const html = `
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-signal"></i>
                    Status
                </span>
                <span class="metric-value ${stats.status === 'online' ? 'status-connected' : 'status-disconnected'}">
                    ${this.capitalizeFirst(stats.status || 'Unknown')}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-clock"></i>
                    Uptime
                </span>
                <span class="metric-value">
                    ${this.formatUptime(stats.uptime || 0)}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-server"></i>
                    Guilds
                </span>
                <span class="metric-value">
                    ${(stats.guild_count || 0).toLocaleString()}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-users"></i>
                    Users
                </span>
                <span class="metric-value">
                    ${(stats.user_count || 0).toLocaleString()}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-terminal"></i>
                    Commands Today
                </span>
                <span class="metric-value">
                    ${(stats.commands_today || 0).toLocaleString()}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-music"></i>
                    Songs Played
                </span>
                <span class="metric-value">
                    ${(stats.songs_played || 0).toLocaleString()}
                </span>
            </div>
        `;
        
        container.innerHTML = html;
    }

    // Update server overview
    updateServerOverview(servers) {
        const container = document.getElementById('server-overview');
        if (!container || !servers) return;

        const totalServers = servers.length || 0;
        const activeServers = servers.filter(s => s.active_voice_connections > 0).length;
        const totalUsers = servers.reduce((sum, s) => sum + (s.member_count || 0), 0);

        const html = `
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-server"></i>
                    Total Servers
                </span>
                <span class="metric-value">
                    ${totalServers.toLocaleString()}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-volume-up"></i>
                    Active Voice
                </span>
                <span class="metric-value">
                    ${activeServers.toLocaleString()}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-users"></i>
                    Total Members
                </span>
                <span class="metric-value">
                    ${totalUsers.toLocaleString()}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-percentage"></i>
                    Activity Rate
                </span>
                <span class="metric-value">
                    ${totalServers > 0 ? Math.round((activeServers / totalServers) * 100) : 0}%
                </span>
            </div>
        `;
        
        container.innerHTML = html;
    }

    // Update system information
    updateSystemInfo(system) {
        const container = document.getElementById('system-info');
        if (!container || !system) return;

        const html = `
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-microchip"></i>
                    CPU Usage
                </span>
                <span class="metric-value">
                    ${(system.cpu_percent || 0).toFixed(1)}%
                </span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${system.cpu_percent || 0}%"></div>
            </div>
            
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-memory"></i>
                    Memory Usage
                </span>
                <span class="metric-value">
                    ${this.formatBytes(system.memory_used || 0)} / ${this.formatBytes(system.memory_total || 0)}
                </span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${system.memory_percent || 0}%"></div>
            </div>
            
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-hdd"></i>
                    Disk Usage
                </span>
                <span class="metric-value">
                    ${this.formatBytes(system.disk_used || 0)} / ${this.formatBytes(system.disk_total || 0)}
                </span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${system.disk_percent || 0}%"></div>
            </div>
            
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-network-wired"></i>
                    Network Latency
                </span>
                <span class="metric-value">
                    ${(system.discord_latency || 0).toFixed(0)}ms
                </span>
            </div>
        `;
        
        container.innerHTML = html;
    }

    // Update health status
    updateHealthStatus(health) {
        const indicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        
        if (!health) return;

        const healthScore = health.overall_score || 0;
        let status, className;

        if (healthScore >= 80) {
            status = 'Healthy';
            className = 'status-healthy';
        } else if (healthScore >= 60) {
            status = 'Degraded';
            className = 'status-degraded';
        } else {
            status = 'Unhealthy';
            className = 'status-unhealthy';
        }

        if (indicator) {
            indicator.className = `status-indicator ${className}`;
        }
        
        if (statusText) {
            statusText.textContent = `System ${status} (${healthScore}%)`;
        }

        // Update recent issues
        this.updateRecentIssues(health.issues || []);
        
        // Update recommendations
        this.updateRecommendations(health.recommendations || []);
    }

    // Update recent issues display
    updateRecentIssues(issues) {
        const container = document.getElementById('recent-issues');
        if (!container) return;

        if (issues.length === 0) {
            container.innerHTML = `
                <p style="color: #4CAF50; text-align: center; padding: 20px;">
                    <i class="fas fa-check-circle"></i> No recent issues detected!
                </p>
            `;
            return;
        }

        const html = issues.slice(0, 3).map(issue => `
            <div class="error-item ${issue.severity || 'info'}">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px;">
                    <i class="fas fa-${issue.severity === 'critical' ? 'exclamation-circle' : 'exclamation-triangle'}"></i>
                    <strong>${this.escapeHtml(issue.title || 'Unknown Issue')}</strong>
                </div>
                <small>${this.escapeHtml(issue.description || 'No description available')}</small>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }

    // Update recommendations
    updateRecommendations(recommendations) {
        const container = document.getElementById('recommendations');
        if (!container) return;

        if (recommendations.length === 0) {
            container.innerHTML = `
                <div class="recommendation">
                    <i class="fas fa-check"></i>
                    <span>All systems are running optimally!</span>
                </div>
            `;
            return;
        }

        const html = recommendations.map(rec => `
            <div class="recommendation">
                <i class="fas fa-lightbulb"></i>
                <span>${this.escapeHtml(rec)}</span>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }

    // Setup auto-refresh functionality
    setupAutoRefresh() {
        // Clear existing interval
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        // Set up new interval (30 seconds)
        this.updateInterval = setInterval(() => {
            this.refreshData();
        }, 30000);
    }

    // Refresh dashboard data
    async refreshData() {
        try {
            await this.loadInitialData();
        } catch (error) {
            console.error('Failed to refresh data:', error);
        }
    }

    // Setup event listeners
    setupEventListeners() {
        // Handle visibility change to pause/resume updates
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                if (this.updateInterval) {
                    clearInterval(this.updateInterval);
                    this.updateInterval = null;
                }
            } else {
                this.setupAutoRefresh();
            }
        });

        // Handle connection status clicks
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) {
            statusIndicator.addEventListener('click', () => {
                this.showConnectionModal();
            });
        }
    }

    // Update last update time display
    updateLastUpdateTime() {
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement && this.lastUpdate) {
            lastUpdateElement.textContent = this.lastUpdate.toLocaleTimeString();
        }
    }

    // Show error message
    showError(message) {
        console.error('Dashboard Error:', message);
        
        // You could implement a toast notification system here
        // For now, we'll just log it and show an alert
        if (this.isInitialized) {
            // Show a less intrusive error for initialized dashboard
            const errorContainer = document.createElement('div');
            errorContainer.className = 'error-toast';
            errorContainer.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i>
                ${this.escapeHtml(message)}
            `;
            document.body.appendChild(errorContainer);
            
            setTimeout(() => {
                errorContainer.remove();
            }, 5000);
        } else {
            // Show alert for initialization errors
            alert('Dashboard Error: ' + message);
        }
    }

    // Show connection status modal
    showConnectionModal() {
        const modal = document.getElementById('connection-modal');
        if (modal) {
            // Update connection status
            const wsStatus = document.getElementById('ws-status');
            if (wsStatus && this.wsManager) {
                wsStatus.textContent = this.wsManager.isConnected ? 'Connected' : 'Disconnected';
                wsStatus.className = this.wsManager.isConnected ? 'status-connected' : 'status-disconnected';
            }
            
            this.updateLastUpdateTime();
            modal.style.display = 'flex';
        }
    }

    // Utility functions
    formatUptime(seconds) {
        if (!seconds) return '0s';
        
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        const parts = [];
        if (days > 0) parts.push(`${days}d`);
        if (hours > 0) parts.push(`${hours}h`);
        if (minutes > 0) parts.push(`${minutes}m`);
        if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);
        
        return parts.join(' ');
    }

    formatBytes(bytes) {
        if (!bytes) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global dashboard instance
let dashboardCore = null;

// Initialize dashboard when called
function initializeDashboard() {
    dashboardCore = new DashboardCore();
    return dashboardCore.initialize();
}

// Tab switching function
function showTab(tabId) {
    // Remove active class from all tabs and content
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    // Add active class to selected tab and content
    const selectedTab = document.querySelector(`[onclick="showTab('${tabId}')"]`);
    const selectedContent = document.getElementById(tabId);
    
    if (selectedTab) selectedTab.classList.add('active');
    if (selectedContent) selectedContent.classList.add('active');
    
    // Load tab-specific data if needed
    loadTabData(tabId);
}

// Load data specific to a tab
async function loadTabData(tabId) {
    if (!dashboardCore) return;
    
    try {
        switch (tabId) {
            case 'servers':
                await loadServersData();
                break;
            case 'performance':
                await loadPerformanceData();
                break;
            case 'system':
                await loadSystemData();
                break;
            case 'logs':
                await loadLogsData();
                break;
        }
    } catch (error) {
        console.error(`Failed to load ${tabId} data:`, error);
    }
}

// Load servers data
async function loadServersData() {
    const container = document.getElementById('servers-list');
    if (!container) return;
    
    try {
        const servers = await dashboardCore.fetchData('/api/guilds');
        
        if (!servers || servers.length === 0) {
            container.innerHTML = `
                <p style="text-align: center; padding: 40px; color: #ccc;">
                    <i class="fas fa-server"></i><br>
                    No servers connected
                </p>
            `;
            return;
        }
        
        const html = servers.map(server => `
            <div class="server-item">
                <div class="server-info">
                    <div class="server-icon">
                        ${server.name ? server.name.charAt(0).toUpperCase() : 'S'}
                    </div>
                    <div>
                        <strong>${dashboardCore.escapeHtml(server.name || 'Unknown Server')}</strong><br>
                        <small>ID: ${server.id}</small>
                    </div>
                </div>
                <div class="server-stats">
                    <span><i class="fas fa-users"></i> ${(server.member_count || 0).toLocaleString()}</span>
                    <span><i class="fas fa-volume-up"></i> ${server.active_voice_connections || 0}</span>
                    <span><i class="fas fa-list"></i> ${server.queue_length || 0}</span>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
        
    } catch (error) {
        container.innerHTML = `
            <div class="error-item">
                <strong>Failed to load servers</strong><br>
                <small>${dashboardCore.escapeHtml(error.message)}</small>
            </div>
        `;
    }
}

// Refresh functions for buttons
function refreshServers() {
    loadServersData();
}

function refreshLogs() {
    loadLogsData();
}

function clearLogs() {
    if (confirm('Are you sure you want to clear the error log?')) {
        // Implementation would depend on your backend API
        console.log('Clear logs requested');
    }
}

// Connection modal functions
function closeConnectionModal() {
    const modal = document.getElementById('connection-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function reconnectWebSocket() {
    if (dashboardCore && dashboardCore.wsManager) {
        dashboardCore.wsManager.reconnect();
    }
}

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    const modal = document.getElementById('connection-modal');
    if (event.target === modal) {
        closeConnectionModal();
    }
});

// Export for use in other modules
window.DashboardCore = DashboardCore;