// Dashboard Charts - Bassline Bot
// Manages Chart.js instances for data visualization

class DashboardCharts {
    constructor() {
        this.charts = new Map();
        this.chartColors = {
            primary: '#4CAF50',
            secondary: '#2196F3',
            accent: '#9C27B0',
            warning: '#FF9800',
            danger: '#F44336',
            info: '#00BCD4',
            success: '#8BC34A'
        };
        this.gradients = {};
    }

    // Initialize all charts
    async initialize() {
        try {
            console.log('Initializing dashboard charts...');
            
            // Wait a moment for DOM to be ready
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Initialize individual charts
            await this.initializeUsageChart();
            await this.initializeServerChart();
            await this.initializePerformanceChart();
            await this.initializeDatabaseChart();
            
            console.log('Dashboard charts initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize charts:', error);
        }
    }

    // Create gradients for charts
    createGradients(ctx) {
        if (!this.gradients[ctx.canvas.id]) {
            this.gradients[ctx.canvas.id] = {};
            
            // Primary gradient
            const primaryGradient = ctx.createLinearGradient(0, 0, 0, 400);
            primaryGradient.addColorStop(0, 'rgba(76, 175, 80, 0.8)');
            primaryGradient.addColorStop(1, 'rgba(76, 175, 80, 0.1)');
            this.gradients[ctx.canvas.id].primary = primaryGradient;
            
            // Secondary gradient
            const secondaryGradient = ctx.createLinearGradient(0, 0, 0, 400);
            secondaryGradient.addColorStop(0, 'rgba(33, 150, 243, 0.8)');
            secondaryGradient.addColorStop(1, 'rgba(33, 150, 243, 0.1)');
            this.gradients[ctx.canvas.id].secondary = secondaryGradient;
            
            // Warning gradient
            const warningGradient = ctx.createLinearGradient(0, 0, 0, 400);
            warningGradient.addColorStop(0, 'rgba(255, 152, 0, 0.8)');
            warningGradient.addColorStop(1, 'rgba(255, 152, 0, 0.1)');
            this.gradients[ctx.canvas.id].warning = warningGradient;
        }
        
        return this.gradients[ctx.canvas.id];
    }

    // Default chart options
    getDefaultOptions(title) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        color: '#ffffff',
                        usePointStyle: true,
                        padding: 20
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#ffffff'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#ffffff'
                    }
                }
            }
        };
    }

    // Initialize usage chart (24h command activity)
    async initializeUsageChart() {
        const canvas = document.getElementById('usageChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const gradients = this.createGradients(ctx);

        try {
            // Fetch usage data
            const data = await this.fetchChartData('/api/usage/24h');
            
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels || this.generateHourLabels(),
                    datasets: [{
                        label: 'Commands',
                        data: data.commands || new Array(24).fill(0),
                        backgroundColor: gradients.primary,
                        borderColor: this.chartColors.primary,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'Music Commands',
                        data: data.music_commands || new Array(24).fill(0),
                        backgroundColor: gradients.secondary,
                        borderColor: this.chartColors.secondary,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    ...this.getDefaultOptions('Command Usage (24h)'),
                    scales: {
                        ...this.getDefaultOptions().scales,
                        y: {
                            ...this.getDefaultOptions().scales.y,
                            title: {
                                display: true,
                                text: 'Commands per Hour',
                                color: '#ffffff'
                            }
                        }
                    }
                }
            });

            this.charts.set('usage', chart);
            
        } catch (error) {
            console.error('Failed to initialize usage chart:', error);
            this.showChartError(canvas, 'Failed to load usage data');
        }
    }

    // Initialize server distribution chart
    async initializeServerChart() {
        const canvas = document.getElementById('serverChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        try {
            // Fetch server data
            const data = await this.fetchChartData('/api/guilds/distribution');
            
            const chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.labels || ['Small (< 100)', 'Medium (100-1000)', 'Large (> 1000)'],
                    datasets: [{
                        data: data.values || [0, 0, 0],
                        backgroundColor: [
                            this.chartColors.primary,
                            this.chartColors.secondary,
                            this.chartColors.accent
                        ],
                        borderColor: [
                            this.chartColors.primary,
                            this.chartColors.secondary,
                            this.chartColors.accent
                        ],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                color: '#ffffff',
                                usePointStyle: true,
                                padding: 20
                            }
                        }
                    }
                }
            });

            this.charts.set('server', chart);
            
        } catch (error) {
            console.error('Failed to initialize server chart:', error);
            this.showChartError(canvas, 'Failed to load server data');
        }
    }

    // Initialize performance trends chart
    async initializePerformanceChart() {
        const canvas = document.getElementById('performanceChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const gradients = this.createGradients(ctx);

        try {
            // Fetch performance data
            const data = await this.fetchChartData('/api/performance/trends');
            
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels || this.generateTimeLabels(30), // Last 30 data points
                    datasets: [{
                        label: 'Response Time (ms)',
                        data: data.response_times || new Array(30).fill(0),
                        backgroundColor: gradients.warning,
                        borderColor: this.chartColors.warning,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    }, {
                        label: 'CPU Usage (%)',
                        data: data.cpu_usage || new Array(30).fill(0),
                        backgroundColor: gradients.secondary,
                        borderColor: this.chartColors.secondary,
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                color: '#ffffff',
                                usePointStyle: true,
                                padding: 20
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#ffffff'
                            }
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#ffffff'
                            },
                            title: {
                                display: true,
                                text: 'Response Time (ms)',
                                color: '#ffffff'
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            beginAtZero: true,
                            max: 100,
                            grid: {
                                drawOnChartArea: false,
                            },
                            ticks: {
                                color: '#ffffff'
                            },
                            title: {
                                display: true,
                                text: 'CPU Usage (%)',
                                color: '#ffffff'
                            }
                        }
                    }
                }
            });

            this.charts.set('performance', chart);
            
        } catch (error) {
            console.error('Failed to initialize performance chart:', error);
            this.showChartError(canvas, 'Failed to load performance data');
        }
    }

    // Initialize database chart
    async initializeDatabaseChart() {
        const canvas = document.getElementById('databaseChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        try {
            // Fetch database data
            const data = await this.fetchChartData('/api/database/stats');
            
            const chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels || ['Guilds', 'Users', 'Playlists', 'Songs', 'Usage Logs'],
                    datasets: [{
                        label: 'Record Count',
                        data: data.values || [0, 0, 0, 0, 0],
                        backgroundColor: [
                            this.chartColors.primary,
                            this.chartColors.secondary,
                            this.chartColors.accent,
                            this.chartColors.info,
                            this.chartColors.warning
                        ],
                        borderColor: [
                            this.chartColors.primary,
                            this.chartColors.secondary,
                            this.chartColors.accent,
                            this.chartColors.info,
                            this.chartColors.warning
                        ],
                        borderWidth: 2,
                        borderRadius: 5
                    }]
                },
                options: {
                    ...this.getDefaultOptions('Database Statistics'),
                    scales: {
                        ...this.getDefaultOptions().scales,
                        y: {
                            ...this.getDefaultOptions().scales.y,
                            title: {
                                display: true,
                                text: 'Number of Records',
                                color: '#ffffff'
                            }
                        }
                    }
                }
            });

            this.charts.set('database', chart);
            
        } catch (error) {
            console.error('Failed to initialize database chart:', error);
            this.showChartError(canvas, 'Failed to load database data');
        }
    }

    // Fetch chart data from API
    async fetchChartData(endpoint) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Failed to fetch chart data from ${endpoint}:`, error);
            // Return empty data structure
            return {
                labels: [],
                values: [],
                commands: [],
                music_commands: [],
                response_times: [],
                cpu_usage: []
            };
        }
    }

    // Update charts with new data
    updateCharts(newData) {
        try {
            // Update usage chart if new command data is available
            if (newData.commands_24h && this.charts.has('usage')) {
                this.updateUsageChart(newData.commands_24h);
            }

            // Update server chart if server distribution data is available
            if (newData.server_distribution && this.charts.has('server')) {
                this.updateServerChart(newData.server_distribution);
            }

            // Update performance chart if performance data is available
            if (newData.performance && this.charts.has('performance')) {
                this.updatePerformanceChart(newData.performance);
            }

        } catch (error) {
            console.error('Failed to update charts:', error);
        }
    }

    // Update usage chart data
    updateUsageChart(data) {
        const chart = this.charts.get('usage');
        if (!chart) return;

        chart.data.labels = data.labels || chart.data.labels;
        chart.data.datasets[0].data = data.commands || chart.data.datasets[0].data;
        chart.data.datasets[1].data = data.music_commands || chart.data.datasets[1].data;
        
        chart.update('none'); // Update without animation for real-time feel
    }

    // Update server chart data
    updateServerChart(data) {
        const chart = this.charts.get('server');
        if (!chart) return;

        chart.data.labels = data.labels || chart.data.labels;
        chart.data.datasets[0].data = data.values || chart.data.datasets[0].data;
        
        chart.update('none');
    }

    // Update performance chart data
    updatePerformanceChart(data) {
        const chart = this.charts.get('performance');
        if (!chart) return;

        // Add new data point and remove oldest if we have more than 30 points
        if (data.response_time !== undefined) {
            chart.data.datasets[0].data.push(data.response_time);
            if (chart.data.datasets[0].data.length > 30) {
                chart.data.datasets[0].data.shift();
            }
        }

        if (data.cpu_usage !== undefined) {
            chart.data.datasets[1].data.push(data.cpu_usage);
            if (chart.data.datasets[1].data.length > 30) {
                chart.data.datasets[1].data.shift();
            }
        }

        // Update labels
        if (chart.data.labels.length > 30) {
            chart.data.labels.shift();
        }
        chart.data.labels.push(new Date().toLocaleTimeString());
        
        chart.update('none');
    }

    // Show error message on chart canvas
    showChartError(canvas, message) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        ctx.fillText('⚠️ Chart Error', canvas.width / 2, canvas.height / 2 - 20);
        ctx.font = '14px Arial';
        ctx.fillStyle = '#cccccc';
        ctx.fillText(message, canvas.width / 2, canvas.height / 2 + 10);
    }

    // Generate hour labels for 24h chart
    generateHourLabels() {
        const labels = [];
        const now = new Date();
        
        for (let i = 23; i >= 0; i--) {
            const time = new Date(now.getTime() - (i * 60 * 60 * 1000));
            labels.push(time.getHours().toString().padStart(2, '0') + ':00');
        }
        
        return labels;
    }

    // Generate time labels for performance chart
    generateTimeLabels(count) {
        const labels = [];
        const now = new Date();
        const interval = 60000; // 1 minute intervals
        
        for (let i = count - 1; i >= 0; i--) {
            const time = new Date(now.getTime() - (i * interval));
            labels.push(time.toLocaleTimeString());
        }
        
        return labels;
    }

    // Resize all charts (useful for responsive design)
    resizeCharts() {
        this.charts.forEach(chart => {
            chart.resize();
        });
    }

    // Destroy all charts
    destroy() {
        this.charts.forEach(chart => {
            chart.destroy();
        });
        this.charts.clear();
        this.gradients = {};
    }

    // Get chart by name
    getChart(name) {
        return this.charts.get(name);
    }

    // Add new chart
    addChart(name, chart) {
        this.charts.set(name, chart);
    }

    // Remove chart
    removeChart(name) {
        const chart = this.charts.get(name);
        if (chart) {
            chart.destroy();
            this.charts.delete(name);
        }
    }

    // Update chart colors (for theme switching if implemented)
    updateChartColors(newColors) {
        this.chartColors = { ...this.chartColors, ...newColors };
        
        // Update existing charts with new colors
        this.charts.forEach((chart, name) => {
            this.updateChartColor(chart, name);
        });
    }

    // Update individual chart colors
    updateChartColor(chart, chartName) {
        switch (chartName) {
            case 'usage':
                chart.data.datasets[0].borderColor = this.chartColors.primary;
                chart.data.datasets[1].borderColor = this.chartColors.secondary;
                break;
            case 'server':
                chart.data.datasets[0].backgroundColor = [
                    this.chartColors.primary,
                    this.chartColors.secondary,
                    this.chartColors.accent
                ];
                break;
            case 'performance':
                chart.data.datasets[0].borderColor = this.chartColors.warning;
                chart.data.datasets[1].borderColor = this.chartColors.secondary;
                break;
            case 'database':
                chart.data.datasets[0].backgroundColor = [
                    this.chartColors.primary,
                    this.chartColors.secondary,
                    this.chartColors.accent,
                    this.chartColors.info,
                    this.chartColors.warning
                ];
                break;
        }
        
        chart.update();
    }

    // Get chart statistics
    getChartStats() {
        const stats = {
            totalCharts: this.charts.size,
            chartNames: Array.from(this.charts.keys()),
            chartsInitialized: 0
        };
        
        this.charts.forEach(chart => {
            if (chart.data && chart.data.datasets) {
                stats.chartsInitialized++;
            }
        });
        
        return stats;
    }
}

// Music activity chart (specialized chart for music statistics)
class MusicActivityChart {
    constructor(canvasId) {
        this.canvasId = canvasId;
        this.chart = null;
        this.data = {
            hourly: new Array(24).fill(0),
            daily: new Array(7).fill(0),
            genres: {},
            topSongs: []
        };
    }

    async initialize() {
        const canvas = document.getElementById(this.canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        try {
            // Fetch music activity data
            const response = await fetch('/api/music/activity');
            const data = await response.json();
            
            this.updateData(data);
            
            this.chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: this.generateHourLabels(),
                    datasets: [{
                        label: 'Songs Played',
                        data: this.data.hourly,
                        backgroundColor: 'rgba(156, 39, 176, 0.2)',
                        borderColor: '#9C27B0',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#ffffff'
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#ffffff'
                            }
                        }
                    }
                }
            });
            
        } catch (error) {
            console.error('Failed to initialize music activity chart:', error);
        }
    }

    updateData(newData) {
        if (newData.hourly) this.data.hourly = newData.hourly;
        if (newData.daily) this.data.daily = newData.daily;
        if (newData.genres) this.data.genres = newData.genres;
        if (newData.topSongs) this.data.topSongs = newData.topSongs;
        
        if (this.chart) {
            this.chart.data.datasets[0].data = this.data.hourly;
            this.chart.update('none');
        }
    }

    generateHourLabels() {
        const labels = [];
        const now = new Date();
        
        for (let i = 23; i >= 0; i--) {
            const time = new Date(now.getTime() - (i * 60 * 60 * 1000));
            labels.push(time.getHours().toString().padStart(2, '0') + ':00');
        }
        
        return labels;
    }

    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }
}

// Initialize charts when dashboard loads
let dashboardCharts = null;
let musicActivityChart = null;

// Function to initialize all charts
async function initializeAllCharts() {
    try {
        dashboardCharts = new DashboardCharts();
        await dashboardCharts.initialize();
        
        // Initialize music activity chart
        musicActivityChart = new MusicActivityChart('musicActivityChart');
        await musicActivityChart.initialize();
        
        // Make charts available globally
        window.dashboardCharts = dashboardCharts;
        window.musicActivityChart = musicActivityChart;
        
        console.log('All charts initialized successfully');
        
    } catch (error) {
        console.error('Failed to initialize charts:', error);
    }
}

// Handle window resize
window.addEventListener('resize', () => {
    if (dashboardCharts) {
        dashboardCharts.resizeCharts();
    }
});

// Handle chart updates from WebSocket
function handleChartUpdate(data) {
    if (dashboardCharts) {
        dashboardCharts.updateCharts(data);
    }
    
    if (musicActivityChart && data.music_activity) {
        musicActivityChart.updateData(data.music_activity);
    }
}

// Export classes for global use
window.DashboardCharts = DashboardCharts;
window.MusicActivityChart = MusicActivityChart;
window.initializeAllCharts = initializeAllCharts;
window.handleChartUpdate = handleChartUpdate;