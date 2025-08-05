"""
Built-in Trading Dashboard API
Integrated web dashboard for real-time trading monitoring
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPAuthorizationCredentials
from typing import Dict, Any
import json
from datetime import datetime
import asyncio

from ..dependencies import get_current_user, security
import httpx

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Dashboard HTML template as string (no external dependencies)
DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💹 Trading System Dashboard</title>
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
            <h1>💹 Trading System Dashboard</h1>
            <div>
                <span class="status-indicator" id="status-indicator"></span>
                <span id="system-status">Loading...</span>
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
        <button class="refresh-btn" onclick="logout()" style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); box-shadow: 0 8px 25px rgba(239, 68, 68, 0.3);">
            🚪 Logout
        </button>
    </div>
    
    <script>
        let dashboardData = null;
        let autoRefreshInterval = null;
        let autoRefreshEnabled = false;
        
        let authToken = localStorage.getItem('dashboardToken');
        
        async function loadDashboard() {
            try {
                if (!authToken) {
                    renderLogin();
                    return;
                }
                
                const response = await fetch('/dashboard/data', {
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    }
                });
                
                if (response.status === 401) {
                    // Token expired or invalid
                    localStorage.removeItem('dashboardToken');
                    authToken = null;
                    renderLogin();
                    return;
                }
                
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
        
        async function login() {
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            if (!email || !password) {
                alert('Please enter both email and password');
                return;
            }
            
            try {
                const response = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email, password })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    authToken = data.access_token;
                    localStorage.setItem('dashboardToken', authToken);
                    loadDashboard();
                } else {
                    const error = await response.json();
                    alert(`Login failed: ${error.detail || 'Invalid credentials'}`);
                }
            } catch (error) {
                alert(`Login error: ${error.message}`);
            }
        }
        
        function logout() {
            localStorage.removeItem('dashboardToken');
            authToken = null;
            renderLogin();
        }
        
        function renderLogin() {
            const content = document.getElementById('dashboard-content');
            const statusIndicator = document.getElementById('status-indicator');
            const systemStatus = document.getElementById('system-status');
            const lastUpdate = document.getElementById('last-update');
            
            statusIndicator.className = 'status-indicator warning';
            systemStatus.textContent = 'Authentication Required';
            lastUpdate.textContent = 'Please login to access dashboard';
            
            content.innerHTML = `
                <div class="card" style="grid-column: 1 / -1; max-width: 400px; margin: 0 auto;">
                    <div class="card-title">
                        <span class="icon">🔐</span>
                        Dashboard Login
                    </div>
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 5px; opacity: 0.9;">Email:</label>
                        <input type="email" id="email" placeholder="admin@system.com" 
                               style="width: 100%; padding: 10px; border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; background: rgba(255,255,255,0.1); color: white; margin-bottom: 15px;">
                    </div>
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 5px; opacity: 0.9;">Password:</label>
                        <input type="password" id="password" placeholder="Enter password"
                               style="width: 100%; padding: 10px; border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; background: rgba(255,255,255,0.1); color: white; margin-bottom: 15px;"
                               onkeypress="if(event.key==='Enter') login()">
                    </div>
                    <button onclick="login()" 
                            style="width: 100%; padding: 12px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer;">
                        🚀 Login to Dashboard
                    </button>
                    <div style="margin-top: 15px; font-size: 0.9rem; opacity: 0.8; text-align: center;">
                        <strong>Default Admin:</strong><br>
                        Email: admin@system.com<br>
                        Password: central-admin-password-change-in-production
                    </div>
                </div>
            `;
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
            const portfolio = dashboardData.portfolio || {};
            const trading = dashboardData.trading_status || {};
            
            content.innerHTML = `
                <!-- Live Trading Activity -->
                <div class="card" style="grid-column: 1 / -1; background: linear-gradient(135deg, rgba(34, 197, 94, 0.2) 0%, rgba(16, 185, 129, 0.2) 100%);">
                    <div class="card-title">
                        <span class="icon">📈</span>
                        Live Trading Activity
                        <div style="margin-left: auto; display: flex; gap: 10px;">
                            <span class="stat-value ${trading.is_running ? 'positive' : 'negative'}" style="font-size: 1rem;">
                                ${trading.is_running ? '🟢 ACTIVE' : '🔴 STOPPED'}
                            </span>
                        </div>
                    </div>
                    <div class="stat-grid">
                        <div class="stat">
                            <span class="stat-value positive">${trading.total_trades || 0}</span>
                            <span class="stat-label">Total Trades</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value ${portfolio.total_return >= 0 ? 'positive' : 'negative'}">
                                $${(portfolio.total_return || 0).toFixed(2)}
                            </span>
                            <span class="stat-label">Total P&L</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value ${portfolio.total_return_pct >= 0 ? 'positive' : 'negative'}">
                                ${((portfolio.total_return_pct || 0) * 100).toFixed(2)}%
                            </span>
                            <span class="stat-label">Return %</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value neutral">$${(trading.portfolio_value || 0).toFixed(2)}</span>
                            <span class="stat-label">Portfolio Value</span>
                        </div>
                    </div>
                    ${Object.keys(portfolio.positions || {}).length > 0 ? `
                        <div style="margin-top: 20px;">
                            <strong>🎯 Active Positions:</strong>
                            <div style="display: flex; gap: 15px; margin-top: 10px; flex-wrap: wrap;">
                                ${Object.entries(portfolio.positions || {}).map(([symbol, position]) => `
                                    <div style="background: rgba(255, 255, 255, 0.1); padding: 10px; border-radius: 8px; min-width: 150px;">
                                        <div style="font-weight: bold; font-size: 1.1rem;">${symbol}</div>
                                        <div style="font-size: 0.9rem; opacity: 0.9;">
                                            <div>Qty: ${(position.quantity || 0).toFixed(4)}</div>
                                            <div>Current: $${(position.current_price || 0).toFixed(2)}</div>
                                            <div class="${parseFloat(position.unrealized_pnl || 0) >= 0 ? 'positive' : 'negative'}">
                                                P&L: $${(position.unrealized_pnl || 0).toFixed(2)}
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : `
                        <div style="margin-top: 20px; padding: 15px; background: rgba(245, 158, 11, 0.2); border-radius: 8px;">
                            <strong>⏳ No Active Positions</strong><br>
                            Trading system is ${trading.is_running ? 'running and looking for opportunities' : 'stopped'}
                        </div>
                    `}
                </div>

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
                            <span class="stat-value ${parseFloat(portfolio.total_return_pct || 0) >= 0 ? 'positive' : 'negative'}">
                                ${((portfolio.total_return_pct || 0) * 100).toFixed(2)}%
                            </span>
                            <span class="stat-label">Total Return</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value neutral">${portfolio.total_trades || 0}</span>
                            <span class="stat-label">Total Trades</span>
                        </div>
                    </div>
                    <div class="performance-metrics">
                        <div class="metric-item">
                            <strong>P&L:</strong> 
                            <span class="${parseFloat(portfolio.total_return || 0) >= 0 ? 'positive' : 'negative'}">
                                $${(portfolio.total_return || 0).toFixed(2)}
                            </span>
                        </div>
                        <div class="metric-item">
                            <strong>Daily P&L:</strong> 
                            <span class="${parseFloat(portfolio.daily_pnl || 0) >= 0 ? 'positive' : 'negative'}">
                                $${(portfolio.daily_pnl || 0).toFixed(2)}
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
                            <span class="stat-value ${trading.is_running ? 'positive' : (trading.overall_health === 'rate_limited' ? 'neutral' : 'negative')}">
                                ${trading.is_running ? 'ACTIVE' : (trading.overall_health === 'rate_limited' ? 'RATE LIMITED' : 'STOPPED')}
                            </span>
                            <span class="stat-label">Trading Status</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value ${trading.overall_health === 'healthy' ? 'positive' : (trading.overall_health === 'rate_limited' ? 'neutral' : 'negative')}">
                                ${trading.overall_health === 'rate_limited' ? 'RATE LIMITED' : (trading.overall_health || 'unknown').toUpperCase()}
                            </span>
                            <span class="stat-label">System Health</span>
                        </div>
                    </div>
                    ${trading.overall_health === 'rate_limited' ? `
                        <div style="margin-top: 15px; padding: 15px; background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.5); border-radius: 8px;">
                            <strong>⏱️ Rate Limit Active:</strong><br>
                            Trading operations are temporarily restricted for security.<br>
                            <small>Limit resets in ~${Math.max(0, Math.ceil((300 - (Date.now() - new Date(trading.last_check).getTime())) / 1000 / 60))} minutes</small>
                        </div>
                    ` : ''}
                    <div style="margin-top: 20px; font-size: 0.95rem; opacity: 0.9;">
                        <strong>Portfolio ID:</strong> ${portfolio.portfolio_id || 'N/A'}<br>
                        <strong>Last Check:</strong> ${trading.last_check ? new Date(trading.last_check).toLocaleString() : 'N/A'}<br>
                        <strong>Trading:</strong> ${portfolio.is_trading ? '✅ Active' : '❌ Inactive'}<br>
                        <strong>Last Updated:</strong> ${portfolio.last_updated ? new Date(portfolio.last_updated).toLocaleString() : 'N/A'}
                    </div>
                </div>
                
                <!-- Orchestrator Clusters -->
                <div class="card">
                    <div class="card-title">
                        <span class="icon">🏗️</span>
                        Orchestrator Clusters
                    </div>
                    <div id="cluster-status">
                        ${renderClusterStatus(dashboardData.clusters)}
                    </div>
                </div>
                
                <!-- System Information -->
                <div class="card">
                    <div class="card-title">
                        <span class="icon">🔧</span>
                        System Information
                    </div>
                    <div style="font-size: 0.95rem; line-height: 1.6;">
                        <strong>API Endpoint:</strong> ${window.location.origin}<br>
                        <strong>Dashboard:</strong> Built-in Integrated Dashboard<br>
                        <strong>Version:</strong> v2.2.0 Production<br>
                        <strong>Architecture:</strong> Central Manager + Orchestrator Cluster<br>
                        <strong>Security:</strong> Role-based Authorization Active
                    </div>
                </div>
            `;
        }
        
        function renderClusterStatus(clusters) {
            if (!clusters || clusters.error) {
                return `<div class="error">Cluster data unavailable: ${clusters?.error || 'Unknown error'}</div>`;
            }
            
            const cluster = clusters.cluster || {};
            const communication = clusters.communication || {};
            const subscriptions = communication.subscriptions || {};
            const validatedClusters = communication.validated_clusters || {};
            
            // Count actually online clusters
            const onlineClusters = Object.keys(subscriptions).length;
            const totalValidated = Object.keys(validatedClusters).length;
            
            let clusterHtml = `
                <div class="stat-grid">
                    <div class="stat">
                        <span class="stat-value ${onlineClusters > 0 ? 'positive' : 'negative'}">${onlineClusters}</span>
                        <span class="stat-label">Online Clusters</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">${totalValidated}</span>
                        <span class="stat-label">Total Registered</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value ${communication.validation_timestamp ? 'positive' : 'neutral'}">${communication.validation_timestamp ? 'Validated' : 'No Validation'}</span>
                        <span class="stat-label">Health Status</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">${communication.message_stats?.sent || 0}</span>
                        <span class="stat-label">Messages Sent</span>
                    </div>
                </div>
                
                <div style="margin-top: 20px;">
                    <strong>Active Clusters (Validated):</strong>
                    <div style="margin-top: 10px;">
            `;
            
            if (Object.keys(subscriptions).length === 0) {
                clusterHtml += `
                    <div class="position-item" style="margin-bottom: 10px; background: rgba(239, 68, 68, 0.1);">
                        <div class="position-header">
                            <div class="symbol">No Active Clusters</div>
                            <div class="stat-value negative">Offline</div>
                        </div>
                        <div class="position-details">
                            <div><strong>Status:</strong> All clusters are offline or disconnected</div>
                        </div>
                    </div>
                `;
            } else {
                Object.keys(subscriptions).forEach(clusterName => {
                    const clusterNumber = clusterName.includes('cluster1') ? '1' : clusterName.includes('cluster2') ? '2' : 'Unknown';
                    const validation = validatedClusters[clusterName] || {};
                    const isHealthy = validation.health_check === true;
                    const statusClass = isHealthy ? 'positive' : 'negative';
                    const statusText = validation.actual_status || 'Unknown';
                    
                    clusterHtml += `
                        <div class="position-item" style="margin-bottom: 10px;">
                            <div class="position-header">
                                <div class="symbol">Cluster ${clusterNumber}</div>
                                <div class="stat-value ${statusClass}">${statusText.toUpperCase()}</div>
                            </div>
                            <div class="position-details">
                                <div><strong>Container:</strong> ${validation.container_status || 'Unknown'}</div>
                                <div><strong>Health Check:</strong> ${isHealthy ? '✅ Passed' : '❌ Failed'}</div>
                                <div><strong>Agents:</strong> ${subscriptions[clusterName].length || 0}</div>
                                <div><strong>Uptime:</strong> ${validation.uptime ? new Date(validation.uptime).toLocaleString() : 'N/A'}</div>
                            </div>
                        </div>
                    `;
                });
            }
            
            // Show offline clusters if any
            Object.keys(validatedClusters).forEach(clusterName => {
                if (!subscriptions[clusterName]) {
                    const validation = validatedClusters[clusterName] || {};
                    const clusterNumber = clusterName.includes('cluster1') ? '1' : clusterName.includes('cluster2') ? '2' : 'Unknown';
                    
                    clusterHtml += `
                        <div class="position-item" style="margin-bottom: 10px; background: rgba(239, 68, 68, 0.1);">
                            <div class="position-header">
                                <div class="symbol">Cluster ${clusterNumber} (Offline)</div>
                                <div class="stat-value negative">${validation.actual_status?.toUpperCase() || 'OFFLINE'}</div>
                            </div>
                            <div class="position-details">
                                <div><strong>Container:</strong> ${validation.container_status || 'Not Found'}</div>
                                <div><strong>Health Check:</strong> ❌ Failed</div>
                                <div><strong>Error:</strong> ${validation.error || 'Container not running'}</div>
                                <div><strong>Last Check:</strong> ${validation.last_validated ? new Date(validation.last_validated).toLocaleString() : 'N/A'}</div>
                            </div>
                        </div>
                    `;
                }
            });
            
            clusterHtml += `
                    </div>
                </div>
                
                <div style="margin-top: 20px; font-size: 0.9rem; opacity: 0.9;">
                    <strong>Communication Stats:</strong><br>
                    Messages: ${communication.message_stats?.sent || 0} sent, ${communication.message_stats?.received || 0} received, ${communication.message_stats?.failed || 0} failed<br>
                    <strong>Last Validation:</strong> ${communication.validation_timestamp ? new Date(communication.validation_timestamp).toLocaleString() : 'Never'}
                </div>
            `;
            
            return clusterHtml;
        }
        
        function renderError(message) {
            const content = document.getElementById('dashboard-content');
            content.innerHTML = `
                <div class="card">
                    <div class="card-title">
                        <span class="icon">❌</span>
                        Dashboard Error
                    </div>
                    <div class="error">
                        <strong>Error:</strong> ${message}<br><br>
                        <strong>Possible causes:</strong><br>
                        • Trading system rate limiting active<br>
                        • Authentication token expired<br>
                        • Trading service temporarily unavailable<br>
                        • Network connectivity issues
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
                autoRefreshInterval = setInterval(loadDashboard, 15000); // Refresh every 15 seconds
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

@router.get("/", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the dashboard HTML page"""
    return HTMLResponse(content=DASHBOARD_HTML)

@router.get("/data")
async def dashboard_data(
    current_user: dict = Depends(get_current_user),
    authorization: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get dashboard data JSON (requires authentication)"""
    try:
        # Use the user's current token for internal API calls
        headers = {"Authorization": f"Bearer {authorization.credentials}"}
        
        # Make internal API calls to get trading data
        async with httpx.AsyncClient() as client:
            try:
                # Get trading status
                trading_response = await client.get("http://localhost:8000/api/v1/trading/status", headers=headers, timeout=5.0)
                if trading_response.status_code == 200:
                    trading_data = trading_response.json()
                elif trading_response.status_code == 429:
                    # Rate limited - use default stopped state
                    trading_data = {
                        "is_running": False,
                        "overall_health": "rate_limited",
                        "last_check": datetime.now().isoformat(),
                        "portfolio_value": 0,
                        "total_trades": 0,
                        "message": "Rate limited - trading temporarily restricted"
                    }
                else:
                    trading_data = {"is_running": False, "overall_health": "error"}
                
                # Get portfolio data
                portfolio_response = await client.get("http://localhost:8000/api/v1/trading/portfolio", headers=headers, timeout=5.0)  
                if portfolio_response.status_code == 200:
                    portfolio_data = portfolio_response.json()
                
                # Get cluster data
                cluster_response = await client.get("http://localhost:8000/api/v1/cluster/status", headers=headers, timeout=5.0)
                if cluster_response.status_code == 200:
                    cluster_data = cluster_response.json()
                else:
                    cluster_data = {"error": "Cluster API unavailable"}
                
                if portfolio_response.status_code == 429:
                    # Rate limited - show basic portfolio structure
                    portfolio_data = {
                        "portfolio_id": "system-portfolio",
                        "initial_capital": 1000,
                        "current_value": 1000,
                        "available_cash": 1000,
                        "positions": {},
                        "performance": {
                            "total_return": 0,
                            "total_return_pct": 0,
                            "daily_pnl": 0,
                            "total_trades": 0
                        },
                        "is_trading": False,
                        "last_updated": datetime.now().isoformat(),
                        "status": "rate_limited"
                    }
                else:
                    portfolio_data = {"error": "Portfolio API unavailable"}
                
                # Extract nested data from API responses
                trading_info = trading_data.get("data", {}) if trading_data.get("status") == "success" else {}
                portfolio_info = portfolio_data.get("data", {}) if portfolio_data.get("status") == "success" else portfolio_data
                
                dashboard_data = {
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "portfolio": {
                        "portfolio_id": portfolio_info.get("portfolio_id"),
                        "initial_capital": portfolio_info.get("initial_capital", 1000),
                        "current_value": portfolio_info.get("current_value", 0),
                        "available_cash": portfolio_info.get("available_cash", 0),
                        "positions": portfolio_info.get("positions", {}),
                        "total_return": portfolio_info.get("performance", {}).get("total_return", 0),
                        "total_return_pct": portfolio_info.get("performance", {}).get("total_return_pct", 0),
                        "daily_pnl": portfolio_info.get("performance", {}).get("daily_pnl", 0),
                        "total_trades": portfolio_info.get("performance", {}).get("total_trades", 0),
                        "is_trading": portfolio_info.get("is_trading", False),
                        "last_updated": portfolio_info.get("last_updated")
                    },
                    "trading_status": {
                        "is_running": trading_info.get("is_running", False),
                        "overall_health": trading_info.get("overall_health", "unknown"),
                        "last_check": trading_info.get("last_check"),
                        "portfolio_value": trading_info.get("portfolio_value", 0),
                        "total_trades": trading_info.get("total_trades", 0)
                    },
                    "clusters": cluster_data
                }
                
                return dashboard_data
                
            except Exception as api_error:
                # Handle API errors gracefully (including rate limits)
                error_message = str(api_error)
                
                # Check if it's a rate limit error
                if "429" in error_message or "rate limit" in error_message.lower():
                    error_type = "rate_limited"
                else:
                    error_type = "api_error"
                
                # Return error state but still show what we can
                return {
                    "timestamp": datetime.now().isoformat(),
                    "status": "error", 
                    "error": error_message,
                    "error_type": error_type,
                    "portfolio": {
                        "initial_capital": 1000.0,
                        "current_value": 0,
                        "available_cash": 0,
                        "positions": {},
                        "total_return": 0,
                        "total_return_pct": 0,
                        "daily_pnl": 0,
                        "total_trades": 0,
                        "is_trading": False
                    },
                    "trading_status": {
                        "is_running": False,
                        "overall_health": "error",
                        "last_check": datetime.now().isoformat()
                    }
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard data error: {str(e)}")

