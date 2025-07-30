// Dashboard UI Utilities - Bassline Bot
// UI helpers, animations, and interactive components

class DashboardUI {
    constructor() {
        this.notifications = [];
        this.modals = new Map();
        this.tooltips = new Map();
        this.animations = {
            fadeIn: 'fadeIn 0.5s ease-in-out',
            slideUp: 'slideUp 0.3s ease-out',
            pulse: 'pulse 2s infinite',
            spin: 'spin 1s linear infinite'
        };
    }

    // Initialize UI components
    initialize() {
        this.setupTooltips();
        this.setupAnimations();
        this.setupKeyboardShortcuts();
        this.setupThemeToggle();
        console.log('Dashboard UI initialized');
    }

    // Setup tooltips for elements with data-tooltip attribute
    setupTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            this.addTooltip(element, element.dataset.tooltip);
        });
    }

    // Add tooltip to element
    addTooltip(element, text) {
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = text;
        tooltip.style.cssText = `
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            pointer-events: none;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s ease;
            white-space: nowrap;
        `;
        
        document.body.appendChild(tooltip);
        
        element.addEventListener('mouseenter', (e) => {
            const rect = element.getBoundingClientRect();
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
            tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
            tooltip.style.opacity = '1';
        });
        
        element.addEventListener('mouseleave', () => {
            tooltip.style.opacity = '0';
        });
        
        this.tooltips.set(element, tooltip);
    }

    // Setup CSS animations
    setupAnimations() {
        // Add CSS animations if not already present
        if (!document.getElementById('dashboard-animations')) {
            const style = document.createElement('style');
            style.id = 'dashboard-animations';
            style.textContent = `
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                @keyframes slideUp {
                    from { transform: translateY(100%); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    25% { transform: translateX(-5px); }
                    75% { transform: translateX(5px); }
                }
                
                @keyframes bounce {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-10px); }
                }
                
                .notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 12px;
                    padding: 16px 20px;
                    color: white;
                    font-size: 14px;
                    z-index: 10000;
                    min-width: 300px;
                    max-width: 500px;
                    animation: slideUp 0.3s ease-out;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                }
                
                .notification.success {
                    border-left: 4px solid #4CAF50;
                }
                
                .notification.error {
                    border-left: 4px solid #F44336;
                }
                
                .notification.warning {
                    border-left: 4px solid #FF9800;
                }
                
                .notification.info {
                    border-left: 4px solid #2196F3;
                }
                
                .notification-close {
                    position: absolute;
                    top: 8px;
                    right: 12px;
                    background: none;
                    border: none;
                    color: white;
                    font-size: 18px;
                    cursor: pointer;
                    opacity: 0.7;
                    transition: opacity 0.3s ease;
                }
                
                .notification-close:hover {
                    opacity: 1;
                }
                
                .loading-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.7);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 20000;
                    backdrop-filter: blur(5px);
                }
                
                .loading-spinner {
                    width: 50px;
                    height: 50px;
                    border: 4px solid rgba(255, 255, 255, 0.3);
                    border-top: 4px solid #4CAF50;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                
                .error-toast {
                    position: fixed;
                    bottom: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: linear-gradient(45deg, #F44336, #d32f2f);
                    color: white;
                    padding: 12px 20px;
                    border-radius: 25px;
                    font-size: 14px;
                    z-index: 10000;
                    animation: slideUp 0.3s ease-out;
                    box-shadow: 0 4px 15px rgba(244, 67, 54, 0.3);
                }
            `;
            document.head.appendChild(style);
        }
    }

    // Setup keyboard shortcuts
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + R: Refresh dashboard
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                this.refreshDashboard();
            }
            
            // Ctrl/Cmd + K: Focus search (if implemented)
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                // Focus search functionality
            }
            
            // Escape: Close modals
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
            
            // Number keys 1-5: Switch tabs
            if (e.key >= '1' && e.key <= '5' && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                const tabs = ['overview', 'servers', 'performance', 'system', 'logs'];
                const tabIndex = parseInt(e.key) - 1;
                if (tabs[tabIndex]) {
                    window.showTab(tabs[tabIndex]);
                }
            }
        });
    }

    // Setup theme toggle (if implemented)
    setupThemeToggle() {
        // Placeholder for theme switching functionality
        // Could implement dark/light theme toggle here
    }

    // Show notification
    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${this.escapeHtml(message)}</span>
            </div>
            <button class="notification-close">&times;</button>
        `;
        
        // Position notification
        const existingNotifications = document.querySelectorAll('.notification');
        const topOffset = 20 + (existingNotifications.length * 80);
        notification.style.top = topOffset + 'px';
        
        document.body.appendChild(notification);
        this.notifications.push(notification);
        
        // Close button functionality
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            this.removeNotification(notification);
        });
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                this.removeNotification(notification);
            }, duration);
        }
        
        return notification;
    }

    // Remove notification
    removeNotification(notification) {
        if (notification && notification.parentNode) {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
                
                const index = this.notifications.indexOf(notification);
                if (index > -1) {
                    this.notifications.splice(index, 1);
                }
                
                // Reposition remaining notifications
                this.repositionNotifications();
            }, 300);
        }
    }

    // Reposition notifications after removal
    repositionNotifications() {
        this.notifications.forEach((notification, index) => {
            if (notification.parentNode) {
                notification.style.top = (20 + (index * 80)) + 'px';
            }
        });
    }

    // Get icon for notification type
    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // Show loading overlay
    showLoading(message = 'Loading...') {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div style="text-align: center; color: white;">
                <div class="loading-spinner"></div>
                <div style="margin-top: 20px; font-size: 16px;">${this.escapeHtml(message)}</div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        return overlay;
    }

    // Hide loading overlay
    hideLoading(overlay) {
        if (overlay && overlay.parentNode) {
            overlay.style.opacity = '0';
            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
        }
    }

    // Create modal
    createModal(id, title, content, options = {}) {
        const modal = document.createElement('div');
        modal.id = id;
        modal.className = 'modal';
        modal.style.display = 'none';
        
        modal.innerHTML = `
            <div class="modal-content" style="max-width: ${options.maxWidth || '600px'};">
                <div class="modal-header">
                    <h3><i class="fas fa-${options.icon || 'info-circle'}"></i> ${this.escapeHtml(title)}</h3>
                    <span class="close" onclick="dashboardUI.closeModal('${id}')">&times;</span>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                ${options.actions ? `
                    <div class="modal-actions" style="padding: 20px; text-align: right; border-top: 1px solid rgba(255,255,255,0.1);">
                        ${options.actions}
                    </div>
                ` : ''}
            </div>
        `;
        
        document.body.appendChild(modal);
        this.modals.set(id, modal);
        
        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal(id);
            }
        });
        
        return modal;
    }

    // Show modal
    showModal(id) {
        const modal = this.modals.get(id);
        if (modal) {
            modal.style.display = 'flex';
            // Add fade-in animation
            modal.style.opacity = '0';
            setTimeout(() => {
                modal.style.opacity = '1';
            }, 10);
        }
    }

    // Close modal
    closeModal(id) {
        const modal = this.modals.get(id);
        if (modal) {
            modal.style.opacity = '0';
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
        }
    }

    // Close all modals
    closeAllModals() {
        this.modals.forEach((modal, id) => {
            this.closeModal(id);
        });
    }

    // Animate element
    animateElement(element, animation, duration = '0.5s') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        
        if (!element) return;
        
        element.style.animation = `${animation} ${duration}`;
        
        // Remove animation after completion
        setTimeout(() => {
            element.style.animation = '';
        }, parseFloat(duration) * 1000);
    }

    // Highlight element (useful for drawing attention)
    highlightElement(element, color = '#4CAF50') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        
        if (!element) return;
        
        const originalBackground = element.style.background;
        element.style.background = `linear-gradient(45deg, ${color}20, ${color}10)`;
        element.style.transition = 'background 0.3s ease';
        
        setTimeout(() => {
            element.style.background = originalBackground;
        }, 2000);
    }

    // Smooth scroll to element
    scrollToElement(element, offset = 0) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        
        if (!element) return;
        
        const elementTop = element.offsetTop - offset;
        window.scrollTo({
            top: elementTop,
            behavior: 'smooth'
        });
    }

    // Refresh dashboard
    refreshDashboard() {
        const loading = this.showLoading('Refreshing dashboard...');
        
        if (window.dashboardCore) {
            window.dashboardCore.refreshData().then(() => {
                this.hideLoading(loading);
                this.showNotification('Dashboard refreshed successfully', 'success', 3000);
            }).catch((error) => {
                this.hideLoading(loading);
                this.showNotification('Failed to refresh dashboard: ' + error.message, 'error', 5000);
            });
        } else {
            this.hideLoading(loading);
            this.showNotification('Dashboard core not initialized', 'error', 5000);
        }
    }

    // Format number with thousands separator
    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    }

    // Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Format duration
    formatDuration(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        
        const parts = [];
        if (h > 0) parts.push(`${h}h`);
        if (m > 0) parts.push(`${m}m`);
        if (s > 0 || parts.length === 0) parts.push(`${s}s`);
        
        return parts.join(' ');
    }

    // Escape HTML
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Copy text to clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showNotification('Copied to clipboard', 'success', 2000);
            return true;
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
            this.showNotification('Failed to copy to clipboard', 'error', 3000);
            return false;
        }
    }

    // Download data as JSON file
    downloadJSON(data, filename = 'dashboard-data.json') {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        URL.revokeObjectURL(url);
        this.showNotification(`Downloaded ${filename}`, 'success', 3000);
    }

    // Get system information for troubleshooting
    getSystemInfo() {
        return {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            screen: {
                width: screen.width,
                height: screen.height,
                colorDepth: screen.colorDepth
            },
            window: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            timestamp: new Date().toISOString()
        };
    }

    // Cleanup function
    destroy() {
        // Remove all notifications
        this.notifications.forEach(notification => {
            this.removeNotification(notification);
        });
        
        // Remove all modals
        this.modals.forEach((modal, id) => {
            modal.remove();
        });
        this.modals.clear();
        
        // Remove all tooltips
        this.tooltips.forEach((tooltip, element) => {
            tooltip.remove();
        });
        this.tooltips.clear();
        
        console.log('Dashboard UI cleaned up');
    }
}

// Initialize global UI instance
const dashboardUI = new DashboardUI();

// Make UI available globally
window.dashboardUI = dashboardUI;

// Initialize UI when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    dashboardUI.initialize();
});

// Export for module use
window.DashboardUI = DashboardUI;