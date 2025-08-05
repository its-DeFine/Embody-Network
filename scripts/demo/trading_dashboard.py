#!/usr/bin/env python3
"""
Real-Time Trading Dashboard
Creates a comprehensive web dashboard for monitoring trading system performance
"""
import requests
import json
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import os

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@system.com"
ADMIN_PASSWORD = "central-admin-password-change-in-production"

class TradingDashboardServer:
    def __init__(self):
        self.token = None
        self.dashboard_data = {}
        
    def get_auth_token(self):
        """Get authentication token"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                print(f"✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def make_authenticated_request(self, endpoint):
        """Make authenticated API request"""
        if not self.token:
            if not self.get_auth_token():
                return {"error": "Authentication failed"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            
            if response.status_code == 401:  # Token expired
                if self.get_auth_token():  # Get new token
                    headers["Authorization"] = f"Bearer {self.token}"
                    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    def collect_dashboard_data(self):
        """Collect all dashboard data"""
        print("📊 Collecting dashboard data...")
        
        # System health
        health_data = self.make_authenticated_request("/health")
        
        # Trading status  
        trading_status = self.make_authenticated_request("/api/v1/trading/status")
        
        # Portfolio data
        portfolio_data = self.make_authenticated_request("/api/v1/trading/portfolio")
        
        # Market data
        try:
            market_status = requests.get(f"{BASE_URL}/api/v1/market/status", timeout=5)
            market_data = market_status.json() if market_status.status_code == 200 else {"error": "Market API unavailable"}
        except:
            market_data = {"error": "Market API unavailable"}
        
        # Compile dashboard data
        self.dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "health": health_data,
                "trading_status": trading_status,
                "api_url": BASE_URL
            },
            "portfolio": portfolio_data,
            "market": market_data,
            "status": "success" if all(not isinstance(d, dict) or "error" not in d 
                                     for d in [health_data, trading_status, portfolio_data]) else "error"
        }
        
        # Save to JSON file for web dashboard
        with open('trading_dashboard_data.json', 'w') as f:
            json.dump(self.dashboard_data, f, indent=2)
        
        print(f"✅ Dashboard data updated: {datetime.now().strftime('%H:%M:%S')}")
        return self.dashboard_data
    
    def generate_html_dashboard(self):
        """Generate the HTML dashboard file"""
        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💹 Real-Time Trading Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .dashboard {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 25px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .header h1 {
            font-size: 3rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-indicator.healthy { background: #10b981; }
        .status-indicator.error { background: #ef4444; }
        .status-indicator.warning { background: #f59e0b; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(15px);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.2);
        }
        
        .card-title {
            display: flex;
            align-items: center;
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 25px;
            color: #fff;
        }
        
        .card-title .icon {
            font-size: 2rem;
            margin-right: 12px;
        }
        
        .portfolio-overview {
            grid-column: 1 / -1;
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.2) 100%);
        }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        
        .stat {
            text-align: center;
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: background 0.3s ease;
        }
        
        .stat:hover {
            background: rgba(255, 255, 255, 0.15);
        }
        
        .stat-value {
            font-size: 2.2rem;
            font-weight: bold;
            display: block;
            margin-bottom: 8px;
        }
        
        .stat-value.positive { color: #10b981; }
        .stat-value.negative { color: #ef4444; }
        .stat-value.neutral { color: #6b7280; }
        
        .stat-label {
            font-size: 1rem;
            opacity: 0.9;
            font-weight: 500;
        }
        
        .positions-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .position-item {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        
        .position-item:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateX(5px);
        }
        
        .position-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .symbol {
            font-weight: 700;
            font-size: 1.3rem;
            color: #60a5fa;
        }
        
        .position-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 10px;
            font-size: 0.9rem;
            opacity: 0.9;
        }
        
        .performance-metrics {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        
        .metric-item {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        
        .refresh-controls {
            position: fixed;
            bottom: 30px;
            right: 30px;
            display: flex;
            gap: 10px;
        }
        
        .refresh-btn, .auto-refresh-btn {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border: none;
            padding: 15px 20px;
            border-radius: 50px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3);
            transition: all 0.3s ease;
        }
        
        .auto-refresh-btn.active {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            box-shadow: 0 8px 25px rgba(245, 158, 11, 0.3);
        }
        
        .refresh-btn:hover, .auto-refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 35px rgba(16, 185, 129, 0.4);
        }
        
        .error {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.5);
            color: #fecaca;
            padding: 20px;
            border-radius: 12px;
            margin-top: 20px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2rem;
            opacity: 0.8;
        }
        
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 2.2rem; }
            .stat-grid { grid-template-columns: repeat(2, 1fr); }
            .position-details { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>💹 Real-Time Trading Dashboard</h1>
            <div>
                <span class="status-indicator" id="status-indicator"></span>
                <span id="system-status">Connecting...</span>
                <br>
                <small id="last-update">Loading...</small>
            </div>
        </div>
        
        <div class="grid" id="dashboard-content">
            <div class="loading">
                <div class="card-title">
                    <span class="icon">⏳</span>
                    Loading Trading Data...
                </div>
            </div>
        </div>
    </div>
    
    <div class="refresh-controls">
        <button class="auto-refresh-btn" id="auto-refresh-btn" onclick="toggleAutoRefresh()">
            🔄 Auto: OFF
        </button>
        <button class="refresh-btn" onclick="loadDashboard()">
            📊 Refresh
        </button>
    </div>
    
    <script>
        let dashboardData = null;
        let autoRefreshInterval = null;
        let autoRefreshEnabled = false;
        
        async function loadDashboard() {
            try {
                const response = await fetch('trading_dashboard_data.json');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                dashboardData = await response.json();
                renderDashboard();
            } catch (error) {
                console.error('Error loading dashboard data:', error);
                renderError(error.message);
            }
        }
        
        function renderDashboard() {
            if (!dashboardData) return;
            
            // Update header
            const statusIndicator = document.getElementById('status-indicator');
            const systemStatus = document.getElementById('system-status');
            const lastUpdate = document.getElementById('last-update');
            
            if (dashboardData.status === 'success') {
                statusIndicator.className = 'status-indicator healthy';
                systemStatus.textContent = 'System Healthy';
            } else {
                statusIndicator.className = 'status-indicator error';
                systemStatus.textContent = 'System Error';
            }
            
            lastUpdate.textContent = `Last Updated: ${new Date(dashboardData.timestamp).toLocaleString()}`;
            
            // Render main content
            const content = document.getElementById('dashboard-content');
            const portfolio = dashboardData.portfolio?.data || {};
            const trading = dashboardData.system?.trading_status?.data || {};
            
            content.innerHTML = `
                <!-- Portfolio Overview -->
                <div class="card portfolio-overview">
                    <div class="card-title">
                        <span class="icon">💰</span>
                        Portfolio Overview
                    </div>
                    <div class="stat-grid">
                        <div class="stat">
                            <span class="stat-value ${parseFloat(portfolio.current_value || 0) >= parseFloat(portfolio.initial_capital || 0) ? 'positive' : 'negative'}">
                                $${(portfolio.current_value || 0).toFixed(2)}
                            </span>
                            <span class="stat-label">Current Value</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value neutral">$${(portfolio.available_cash || 0).toFixed(2)}</span>
                            <span class="stat-label">Available Cash</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value ${parseFloat(portfolio.performance?.total_return || 0) >= 0 ? 'positive' : 'negative'}">
                                ${((portfolio.performance?.total_return_pct || 0) * 100).toFixed(2)}%
                            </span>
                            <span class="stat-label">Total Return</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value neutral">${portfolio.performance?.total_trades || 0}</span>
                            <span class="stat-label">Total Trades</span>
                        </div>
                    </div>
                    <div class="performance-metrics">
                        <div class="metric-item">
                            <strong>P&L:</strong> 
                            <span class="${parseFloat(portfolio.performance?.total_return || 0) >= 0 ? 'positive' : 'negative'}">
                                $${(portfolio.performance?.total_return || 0).toFixed(2)}
                            </span>
                        </div>
                        <div class="metric-item">
                            <strong>Daily P&L:</strong> 
                            <span class="${parseFloat(portfolio.performance?.daily_pnl || 0) >= 0 ? 'positive' : 'negative'}">
                                $${(portfolio.performance?.daily_pnl || 0).toFixed(2)}
                            </span>
                        </div>
                    </div>
                </div>
                
                <!-- Current Positions -->
                <div class="card">
                    <div class="card-title">
                        <span class="icon">📊</span>
                        Current Positions
                    </div>
                    <div class="positions-list">
                        ${Object.entries(portfolio.positions || {}).map(([symbol, position]) => `
                            <div class="position-item">
                                <div class="position-header">
                                    <div class="symbol">${symbol}</div>
                                    <div class="stat-value ${parseFloat(position.unrealized_pnl || 0) >= 0 ? 'positive' : 'negative'}">
                                        $${(position.market_value || 0).toFixed(2)}
                                    </div>
                                </div>
                                <div class="position-details">
                                    <div><strong>Quantity:</strong> ${(position.quantity || 0).toFixed(4)}</div>
                                    <div><strong>Avg Price:</strong> $${(position.average_price || 0).toFixed(2)}</div>
                                    <div><strong>Current:</strong> $${(position.current_price || 0).toFixed(2)}</div>
                                    <div><strong>P&L:</strong> 
                                        <span class="${parseFloat(position.unrealized_pnl || 0) >= 0 ? 'positive' : 'negative'}">
                                            $${(position.unrealized_pnl || 0).toFixed(2)}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                        ${Object.keys(portfolio.positions || {}).length === 0 ? 
                            '<div class="position-item">No positions currently held</div>' : ''}
                    </div>
                </div>
                
                <!-- Trading Status -->
                <div class="card">
                    <div class="card-title">
                        <span class="icon">⚡</span>
                        Trading Status
                    </div>
                    <div class="stat-grid">
                        <div class="stat">
                            <span class="stat-value ${trading.is_running ? 'positive' : 'negative'}">
                                ${trading.is_running ? 'ACTIVE' : 'STOPPED'}
                            </span>
                            <span class="stat-label">Trading Status</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value ${trading.overall_health === 'healthy' ? 'positive' : 'negative'}">
                                ${(trading.overall_health || 'unknown').toUpperCase()}
                            </span>
                            <span class="stat-label">System Health</span>
                        </div>
                    </div>
                    <div style="margin-top: 20px; font-size: 0.95rem; opacity: 0.9;">
                        <strong>Portfolio ID:</strong> ${portfolio.portfolio_id || 'N/A'}<br>
                        <strong>Last Check:</strong> ${trading.last_check ? new Date(trading.last_check).toLocaleString() : 'N/A'}<br>
                        <strong>Trading:</strong> ${portfolio.is_trading ? '✅ Active' : '❌ Inactive'}<br>
                        <strong>Last Updated:</strong> ${portfolio.last_updated ? new Date(portfolio.last_updated).toLocaleString() : 'N/A'}
                    </div>
                </div>
                
                <!-- System Information -->
                <div class="card">
                    <div class="card-title">
                        <span class="icon">🔧</span>
                        System Information
                    </div>
                    <div style="font-size: 0.95rem; line-height: 1.6;">
                        <strong>API Endpoint:</strong> ${dashboardData.system.api_url}<br>
                        <strong>System Health:</strong> 
                        <span class="${dashboardData.system.health.status === 'healthy' ? 'positive' : 'negative'}">
                            ${dashboardData.system.health.status || 'unknown'}
                        </span><br>
                        <strong>Version:</strong> ${dashboardData.system.health.version || 'N/A'}<br>
                        <strong>Market Data:</strong> ${dashboardData.market.error ? 'Unavailable' : 'Available'}
                    </div>
                </div>
            `;
        }
        
        function renderError(message) {
            const content = document.getElementById('dashboard-content');
            content.innerHTML = `
                <div class="card">
                    <div class="card-title">
                        <span class="icon">❌</span>
                        Error Loading Dashboard
                    </div>
                    <div class="error">
                        <strong>Error:</strong> ${message}<br><br>
                        <strong>Solutions:</strong><br>
                        • Make sure trading_dashboard_data.json exists<br>
                        • Run the trading dashboard Python script<br>
                        • Check that the trading system is running<br>
                        • Verify API connectivity to localhost:8000
                    </div>
                </div>
            `;
        }
        
        function toggleAutoRefresh() {
            const btn = document.getElementById('auto-refresh-btn');
            
            if (autoRefreshEnabled) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
                autoRefreshEnabled = false;
                btn.textContent = '🔄 Auto: OFF';
                btn.classList.remove('active');
            } else {
                autoRefreshInterval = setInterval(loadDashboard, 10000); // Refresh every 10 seconds
                autoRefreshEnabled = true;
                btn.textContent = '🔄 Auto: ON';
                btn.classList.add('active');
            }
        }
        
        // Load dashboard on page load
        document.addEventListener('DOMContentLoaded', loadDashboard);
    </script>
</body>
</html>'''
        
        with open('trading_dashboard.html', 'w') as f:
            f.write(html_content)
        
        print("✅ HTML dashboard generated: trading_dashboard.html")
    
    def start_data_collection(self):
        """Start continuous data collection"""
        def collection_loop():
            while True:
                try:
                    self.collect_dashboard_data()
                    time.sleep(10)  # Update every 10 seconds
                except Exception as e:
                    print(f"❌ Data collection error: {e}")
                    time.sleep(30)  # Wait longer on error
        
        collection_thread = threading.Thread(target=collection_loop, daemon=True)
        collection_thread.start()
        print("✅ Background data collection started")
    
    def start_web_server(self, port=8080):
        """Start web server for dashboard"""
        class DashboardHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=os.getcwd(), **kwargs)
        
        def server_loop():
            try:
                server = HTTPServer(('localhost', port), DashboardHandler)
                print(f"✅ Dashboard server started at http://localhost:{port}/trading_dashboard.html")
                server.serve_forever()
            except Exception as e:
                print(f"❌ Web server error: {e}")
        
        server_thread = threading.Thread(target=server_loop, daemon=True)
        server_thread.start()

def main():
    print("🚀 Starting Real-Time Trading Dashboard")
    print("="*50)
    
    dashboard = TradingDashboardServer()
    
    # Generate HTML dashboard
    dashboard.generate_html_dashboard()
    
    # Start background data collection
    dashboard.start_data_collection()
    
    # Start web server
    dashboard.start_web_server(port=8080)
    
    print("\n🎯 Dashboard Ready!")
    print("📊 Open: http://localhost:8080/trading_dashboard.html")
    print("⚡ Auto-refreshing every 10 seconds")
    print("🔄 Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down dashboard...")
        print("Thanks for using the Trading Dashboard!")

if __name__ == "__main__":
    main()