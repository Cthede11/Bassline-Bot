// WebSocket Manager for Dashboard - Bassline Bot
// Handles real-time updates via WebSocket connection

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        this.pingInterval = null;
        this.pingTimeout = null;
        this.messageHandlers = new Map();
        
        // Bind methods to preserve 'this' context
        this.onOpen = this.onOpen.bind(this);
        this.onMessage = this.onMessage.bind(this);
        this.onClose = this.onClose.bind(this);
        this.onError = this.onError.bind(this);
    }

    // Connect to WebSocket server
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                console.log(`Connecting to WebSocket: ${wsUrl}`);
                
                this.ws = new WebSocket(wsUrl);
                this.ws.onopen = (event) => {
                    this.onOpen(event);
                    resolve();
                };
                this.ws.onmessage = this.onMessage;
                this.ws.onclose = this.onClose;
                this.ws.onerror = (event) => {
                    this.onError(event);
                    reject(new Error('WebSocket connection failed'));
                };
                
                // Set connection timeout
                setTimeout(() => {
                    if (this.ws.readyState === WebSocket.CONNECTING) {
                        this.ws.close();
                        reject(new Error('WebSocket connection timeout'));
                    }
                }, 10000);
                
            } catch (error) {
                console.error('Failed to create WebSocket connection:', error);
                reject(error);
            }
        });
    }

    // Handle WebSocket open event
    onOpen(event) {
        console.log('WebSocket connected successfully');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        
        // Start ping/pong mechanism
        //this.startPing();
        
        // Update UI
        this.updateConnectionStatus(true);
        
        // Send initial subscription message
        this.send({
            type: 'subscribe',
            channels: ['stats', 'health', 'logs', 'system']
        });
    }

    // Handle WebSocket message event
    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data.type);
            
            // Handle ping/pong
            if (data.type === 'ping') {
                this.send({ type: 'pong' });
                return;
            }
            
            if (data.type === 'pong') {
                this.clearPingTimeout();
                return;
            }
            
            // Route message to appropriate handler
            this.handleMessage(data);
            
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }

    // Handle WebSocket close event
    onClose(event) {
        console.log(`WebSocket closed: ${event.code} - ${event.reason}`);
        this.isConnected = false;
        this.stopPing();
        
        // Update UI
        this.updateConnectionStatus(false);
        
        // Attempt reconnection unless it was intentional
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.showReconnectionError();
        }
    }

    // Handle WebSocket error event
    onError(event) {
        console.error('WebSocket error:', event);
        this.updateConnectionStatus(false, 'Connection error occurred');
    }

    // Schedule reconnection attempt
    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), this.maxReconnectDelay);
        
        console.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (!this.isConnected) {
                this.reconnect();
            }
        }, delay);
    }

    // Attempt to reconnect
    async reconnect() {
        try {
            console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            await this.connect();
        } catch (error) {
            console.error('Reconnection failed:', error);
            // onClose will handle scheduling the next attempt
        }
    }

    // Send message via WebSocket
    send(data) {
        if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(data));
                return true;
            } catch (error) {
                console.error('Failed to send WebSocket message:', error);
                return false;
            }
        } else {
            console.warn('Cannot send message: WebSocket not connected');
            return false;
        }
    }

    // Start ping mechanism
    startPing() {
        this.stopPing(); // Clear any existing ping
        
        this.pingInterval = setInterval(() => {
            if (this.isConnected) {
                this.send({ type: 'ping' });
                
                // Set timeout for pong response
                this.pingTimeout = setTimeout(() => {
                    console.warn('Ping timeout - closing connection');
                    this.ws.close();
                }, 5000);
            }
        }, 30000); // Ping every 30 seconds
    }

    // Stop ping mechanism
    stopPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        this.clearPingTimeout();
    }

    // Clear ping timeout
    clearPingTimeout() {
        if (this.pingTimeout) {
            clearTimeout(this.pingTimeout);
            this.pingTimeout = null;
        }
    }

    // Handle incoming messages
    handleMessage(data) {
        const { type, payload } = data;
        
        switch (type) {
            case 'stats_update':
                this.handleStatsUpdate(payload);
                break;
            case 'health_update':
                this.handleHealthUpdate(payload);
                break;
            case 'log_update':
                this.handleLogUpdate(payload);
                break;
            case 'system_update':
                this.handleSystemUpdate(payload);
                break;
            case 'error':
                this.handleError(payload);
                break;
            default:
                console.log(`Unhandled message type: ${type}`, payload);
        }
        
        // Call custom handlers
        if (this.messageHandlers.has(type)) {
            const handlers = this.messageHandlers.get(type);
            handlers.forEach(handler => {
                try {
                    handler(payload);
                } catch (error) {
                    console.error(`Error in message handler for ${type}:`, error);
                }
            });
        }
    }

    // Handle stats updates
    handleStatsUpdate(stats) {
        if (window.dashboardCore) {
            window.dashboardCore.updateBotStats(stats);
            
            // Update charts if visible
            if (window.dashboardCharts) {
                window.dashboardCharts.updateCharts(stats);
            }
        }
    }

    // Handle health updates
    handleHealthUpdate(health) {
        if (window.dashboardCore) {
            window.dashboardCore.updateHealthStatus(health);
        }
    }

    // Handle log updates
    handleLogUpdate(logData) {
        this.updateErrorLog(logData);
    }

    // Handle system updates
    handleSystemUpdate(system) {
        if (window.dashboardCore) {
            window.dashboardCore.updateSystemInfo(system);
        }
    }

    // Handle error messages
    handleError(error) {
        console.error('Server error received:', error);
        if (window.dashboardCore) {
            window.dashboardCore.showError(error.message || 'Server error occurred');
        }
    }

    // Update error log display
    updateErrorLog(logData) {
        const container = document.getElementById('error-log');
        if (!container || !logData) return;

        const { recent_errors } = logData;
        
        if (!recent_errors || recent_errors.length === 0) {
            container.innerHTML = `
                <p style="color: #4CAF50; text-align: center; padding: 20px;">
                    <i class="fas fa-check-circle"></i> No recent errors detected!
                </p>
            `;
            return;
        }

        // Error categories for styling
        const errorCategories = {
            'ConnectionClosed': { icon: '🔌', color: '#f44336', category: 'Connection' },
            'HTTPException': { icon: '🌐', color: '#ff9800', category: 'API' },
            'YouTubeError': { icon: '📺', color: '#ff5722', category: 'Media' },
            'CommandError': { icon: '⚡', color: '#9c27b0', category: 'Command' },
            'TimeoutError': { icon: '⏱️', color: '#607d8b', category: 'Timeout' },
            'DatabaseError': { icon: '🗄️', color: '#795548', category: 'Database' }
        };

        const html = recent_errors.slice(0, 15).map(error => {
            const category = errorCategories[error.error_type] || { icon: '❌', color: '#f44336', category: 'Other' };
            const timeAgo = this.getTimeAgo(error.timestamp);
            
            return `
                <div class="error-item" style="border-left-color: ${category.color}">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 5px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 1.2em;">${category.icon}</span>
                            <strong>${error.error_type}</strong>
                            <span style="background: ${category.color}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 0.7em;">
                                ${category.category}
                            </span>
                        </div>
                        <small style="color: #999;">${timeAgo}</small>
                    </div>
                    <div style="margin-bottom: 5px;">
                        <strong>Command:</strong> ${error.command || 'Unknown'}
                        ${error.guild_id ? `<br><strong>Guild:</strong> ${error.guild_id}` : ''}
                    </div>
                    <div style="font-size: 0.9em; color: #ccc;">
                        ${this.escapeHtml(error.error_message)}
                    </div>
                </div>
            `;
        }).join('');

        // Add error summary
        const errorTypes = {};
        recent_errors.forEach(error => {
            errorTypes[error.error_type] = (errorTypes[error.error_type] || 0) + 1;
        });

        const summaryHtml = `
            <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <strong>Error Summary (Last ${recent_errors.length} errors):</strong><br>
                ${Object.entries(errorTypes).map(([type, count]) => {
                    const category = errorCategories[type] || { icon: '❌' };
                    return `<span style="margin-right: 15px;">${category.icon} ${type}: ${count}</span>`;
                }).join('')}
            </div>
        `;

        container.innerHTML = summaryHtml + html;
    }

    // Register message handler
    addMessageHandler(type, handler) {
        if (!this.messageHandlers.has(type)) {
            this.messageHandlers.set(type, []);
        }
        this.messageHandlers.get(type).push(handler);
    }

    // Remove message handler
    removeMessageHandler(type, handler) {
        if (this.messageHandlers.has(type)) {
            const handlers = this.messageHandlers.get(type);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    // Update connection status in UI
    updateConnectionStatus(connected, message = '') {
        // Update WebSocket status in connection modal
        const wsStatus = document.getElementById('ws-status');
        if (wsStatus) {
            wsStatus.textContent = connected ? 'Connected' : 'Disconnected';
            wsStatus.className = connected ? 'status-connected' : 'status-disconnected';
        }

        // Update auto-refresh indicator
        const autoRefresh = document.querySelector('.auto-refresh');
        if (autoRefresh) {
            const indicator = autoRefresh.querySelector('.refresh-indicator');
            if (connected) {
                autoRefresh.style.background = 'linear-gradient(45deg, #4CAF50, #45a049)';
                if (indicator) indicator.style.display = 'block';
            } else {
                autoRefresh.style.background = 'linear-gradient(45deg, #F44336, #d32f2f)';
                if (indicator) indicator.style.display = 'none';
            }
        }

        // Show connection message if provided
        if (message && window.dashboardCore) {
            window.dashboardCore.showError(message);
        }
    }

    // Show reconnection error
    showReconnectionError() {
        const errorMessage = `
            Failed to maintain connection to the server after ${this.maxReconnectAttempts} attempts. 
            Please check your internet connection and refresh the page.
        `;
        
        if (window.dashboardCore) {
            window.dashboardCore.showError(errorMessage);
        }
        
        // Show a persistent reconnection button
        this.showReconnectionButton();
    }

    // Show manual reconnection option
    showReconnectionButton() {
        const existingButton = document.getElementById('reconnect-button');
        if (existingButton) return; // Already showing

        const button = document.createElement('div');
        button.id = 'reconnect-button';
        button.className = 'reconnect-button';
        button.innerHTML = `
            <div style="background: linear-gradient(45deg, #F44336, #d32f2f); color: white; padding: 15px 20px; 
                        border-radius: 25px; position: fixed; bottom: 20px; right: 20px; z-index: 1001;
                        cursor: pointer; box-shadow: 0 4px 15px rgba(244, 67, 54, 0.3);
                        display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-wifi"></i>
                <span>Reconnect</span>
            </div>
        `;
        
        button.addEventListener('click', () => {
            button.remove();
            this.reconnectAttempts = 0; // Reset attempts
            this.reconnect();
        });
        
        document.body.appendChild(button);
    }

    // Close connection
    close() {
        this.stopPing();
        if (this.ws) {
            this.ws.close(1000, 'Client closing');
            this.ws = null;
        }
        this.isConnected = false;
        this.updateConnectionStatus(false);
    }

    // Utility functions
    getTimeAgo(timestamp) {
        const now = Date.now();
        const diff = now - (timestamp * 1000);
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (days > 0) return `${days}d ago`;
        if (hours > 0) return `${hours}h ago`;
        if (minutes > 0) return `${minutes}m ago`;
        return 'Just now';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Load additional data functions for tabs
async function loadPerformanceData() {
    const container = document.getElementById('response-times');
    if (!container) return;
    
    try {
        const performance = await dashboardCore.fetchData('/api/performance');
        
        const html = `
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-tachometer-alt"></i>
                    Avg Response Time
                </span>
                <span class="metric-value">
                    ${(performance.avg_response_time || 0).toFixed(0)}ms
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-check-circle"></i>
                    Success Rate
                </span>
                <span class="metric-value">
                    ${(performance.success_rate || 0).toFixed(1)}%
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-bolt"></i>
                    Commands/min
                </span>
                <span class="metric-value">
                    ${(performance.commands_per_minute || 0).toFixed(1)}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-music"></i>
                    Music Latency
                </span>
                <span class="metric-value">
                    ${(performance.music_latency || 0).toFixed(0)}ms
                </span>
            </div>
        `;
        
        container.innerHTML = html;
        
        // Update resource usage
        const resourceContainer = document.getElementById('resource-usage');
        if (resourceContainer && performance.resources) {
            const resources = performance.resources;
            resourceContainer.innerHTML = `
                <div class="metric">
                    <span class="metric-label">
                        <i class="fas fa-microchip"></i>
                        CPU Load
                    </span>
                    <span class="metric-value">
                        ${(resources.cpu_load || 0).toFixed(1)}%
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">
                        <i class="fas fa-memory"></i>
                        Memory Usage
                    </span>
                    <span class="metric-value">
                        ${dashboardCore.formatBytes(resources.memory_usage || 0)}
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">
                        <i class="fas fa-network-wired"></i>
                        Network I/O
                    </span>
                    <span class="metric-value">
                        ${dashboardCore.formatBytes(resources.network_io || 0)}/s
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">
                        <i class="fas fa-hdd"></i>
                        Disk I/O
                    </span>
                    <span class="metric-value">
                        ${dashboardCore.formatBytes(resources.disk_io || 0)}/s
                    </span>
                </div>
            `;
        }
        
    } catch (error) {
        container.innerHTML = `
            <div class="error-item">
                <strong>Failed to load performance data</strong><br>
                <small>${dashboardCore.escapeHtml(error.message)}</small>
            </div>
        `;
    }
}

async function loadSystemData() {
    // System data is already loaded in the main dashboard
    // This could load additional system-specific information
    const healthContainer = document.getElementById('health-check');
    if (!healthContainer) return;
    
    try {
        const health = await dashboardCore.fetchData('/api/health');
        
        const checks = health.checks || {};
        const html = Object.entries(checks).map(([check, status]) => `
            <div class="metric">
                <span class="metric-label">
                    <i class="fas fa-${status.healthy ? 'check-circle' : 'exclamation-triangle'}"></i>
                    ${check.replace('_', ' ').toUpperCase()}
                </span>
                <span class="metric-value ${status.healthy ? 'status-connected' : 'status-disconnected'}">
                    ${status.healthy ? 'Healthy' : 'Unhealthy'}
                </span>
            </div>
        `).join('');
        
        healthContainer.innerHTML = html || '<p>No health checks available</p>';
        
    } catch (error) {
        healthContainer.innerHTML = `
            <div class="error-item">
                <strong>Failed to load health data</strong><br>
                <small>${dashboardCore.escapeHtml(error.message)}</small>
            </div>
        `;
    }
}

async function loadLogsData() {
    // Error log is handled by WebSocket updates
    // Load diagnostics information
    const diagnosticsContainer = document.getElementById('diagnostics-info');
    if (!diagnosticsContainer) return;
    
    try {
        const diagnostics = await dashboardCore.fetchData('/api/diagnostics');
        
        if (!diagnostics.issues || diagnostics.issues.length === 0) {
            diagnosticsContainer.innerHTML = `
                <div class="recommendation">
                    <i class="fas fa-check-circle"></i>
                    <span>All systems operating normally!</span>
                </div>
            `;
            return;
        }
        
        const html = diagnostics.issues.map(issue => `
            <div class="error-item ${issue.severity || 'info'}">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px;">
                    <i class="fas fa-${issue.severity === 'critical' ? 'exclamation-circle' : 'exclamation-triangle'}"></i>
                    <strong>${dashboardCore.escapeHtml(issue.title)}</strong>
                </div>
                <p>${dashboardCore.escapeHtml(issue.description)}</p>
                ${issue.recommendation ? `<small><strong>Recommendation:</strong> ${dashboardCore.escapeHtml(issue.recommendation)}</small>` : ''}
            </div>
        `).join('');
        
        diagnosticsContainer.innerHTML = html;
        
    } catch (error) {
        diagnosticsContainer.innerHTML = `
            <div class="error-item">
                <strong>Failed to load diagnostics</strong><br>
                <small>${dashboardCore.escapeHtml(error.message)}</small>
            </div>
        `;
    }
}

// Export for global use
window.WebSocketManager = WebSocketManager;