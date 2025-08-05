"""
Clean Trading Dashboard API
Simple, accurate dashboard showing only real data
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from typing import Dict, Any
import json
from datetime import datetime
import asyncio

from ..dependencies import get_current_user, security
import httpx

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Simple dashboard HTML template
CLEAN_DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 Clean Trading Dashboard</title>
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
            max-width: 1400px;
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
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-indicator.healthy { color: #10b981; }
        .status-indicator.warning { color: #f59e0b; }
        .status-indicator.error { color: #ef4444; }
        
        .content-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        .card-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #f8fafc;
        }
        
        .card-title .icon {
            font-size: 1.5rem;
        }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat {
            text-align: center;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .stat-value {
            display: block;
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        .stat-value.positive { color: #10b981; }
        .stat-value.negative { color: #ef4444; }
        .stat-value.neutral { color: #6b7280; }
        
        .stat-label {
            font-size: 0.875rem;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            background: rgba(75, 85, 99, 0.1);
            border-radius: 16px;
            border: 2px dashed rgba(156, 163, 175, 0.3);
            margin-top: 20px;
        }
        
        .empty-state .icon {
            font-size: 4rem;
            margin-bottom: 20px;
            opacity: 0.5;
        }
        
        .empty-state .title {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 10px;
            color: rgba(156, 163, 175, 0.9);
        }
        
        .empty-state .description {
            opacity: 0.7;
            font-size: 1rem;
        }
        
        .error-message {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #fecaca;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
        
        .refresh-btn {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .refresh-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🎯 Trading System Dashboard</h1>
            <p style="opacity: 0.8;">Real-Time Trading & Cluster Management</p>
        </div>
        
        <div class="status-bar">
            <div class="status-indicator healthy" id="system-status">
                <span>🟢</span>
                <span>System Online</span>
            </div>
            <div>
                <span id="last-update">Loading...</span>
                <button class="refresh-btn" onclick="loadDashboard()" style="margin-left: 15px;">🔄 Refresh</button>
            </div>
        </div>
        
        <div class="content-grid" id="dashboard-content">
            <!-- Dashboard content will be loaded here -->
        </div>
    </div>
    
    <script>
        let dashboardData = {};
        
        // Load dashboard data and render
        async function loadDashboard() {
            try {
                document.getElementById('last-update').textContent = 'Loading...';
                
                // Load system data
                const systemResponse = await fetch('/api/v1/trading/status');
                const systemData = systemResponse.ok ? await systemResponse.json() : { error: 'System unavailable' };
                
                // Load cluster data
                const clusterResponse = await fetch('/dashboard/api/cluster-status');
                const clusterData = clusterResponse.ok ? await clusterResponse.json() : { error: 'Cluster unavailable' };
                
                // Load portfolio data from public endpoint
                const portfolioResponse = await fetch('/dashboard/api/portfolio-status');
                const portfolioData = portfolioResponse.ok ? await portfolioResponse.json() : { error: 'Portfolio unavailable' };
                
                // Debug logging
                console.log('System data:', systemData);
                console.log('Portfolio data:', portfolioData);
                console.log('Cluster data:', clusterData);
                
                // Extract data from responses
                const systemInfo = systemData.data || systemData;
                // Portfolio data comes directly from public endpoint, no wrapper
                
                dashboardData = {
                    system: systemInfo,
                    clusters: clusterData,
                    portfolio: portfolioData,
                    timestamp: new Date().toISOString()
                };
                
                console.log('Dashboard data:', dashboardData);
                
                renderDashboard();
                document.getElementById('last-update').textContent = `Updated: ${new Date().toLocaleTimeString()}`;
                
            } catch (error) {
                console.error('Dashboard load error:', error);
                renderError(error.message);
                document.getElementById('last-update').textContent = `Error: ${new Date().toLocaleTimeString()}`;
            }
        }
        
        function renderDashboard() {
            const content = document.getElementById('dashboard-content');
            const system = dashboardData.system || {};
            const clusters = dashboardData.clusters || {};
            const portfolio = dashboardData.portfolio || {};
            
            content.innerHTML = `
                <!-- System Status -->
                <div class="card">
                    <div class="card-title">
                        <span class="icon">⚡</span>
                        System Status
                    </div>
                    ${renderSystemStatus(system)}
                </div>
                
                <!-- Active Clusters -->
                <div class="card">
                    <div class="card-title">
                        <span class="icon">🏗️</span>
                        Orchestrator Clusters
                    </div>
                    ${renderClusters(clusters)}
                </div>
                
                <!-- Trading Activity -->
                <div class="card">
                    <div class="card-title">
                        <span class="icon">📈</span>
                        Trading Activity
                    </div>
                    ${renderTradingActivity(system, portfolio)}
                </div>
                
                <!-- Portfolio Status -->
                <div class="card">
                    <div class="card-title">
                        <span class="icon">💼</span>
                        Portfolio Status
                    </div>
                    ${renderPortfolio(portfolio)}
                </div>
            `;
        }
        
        function renderSystemStatus(system) {
            const isHealthy = system.is_running && system.overall_health === 'healthy';
            
            return `
                <div class="stat-grid">
                    <div class="stat">
                        <span class="stat-value ${isHealthy ? 'positive' : 'negative'}">
                            ${isHealthy ? 'Online' : 'Offline'}
                        </span>
                        <span class="stat-label">Status</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">${system.total_trades || 0}</span>
                        <span class="stat-label">Total Trades</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">$${(system.portfolio_value || 0).toFixed(2)}</span>
                        <span class="stat-label">Portfolio Value</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">${system.last_check ? new Date(system.last_check).toLocaleTimeString() : 'N/A'}</span>
                        <span class="stat-label">Last Check</span>
                    </div>
                </div>
            `;
        }
        
        function renderClusters(clusters) {
            const communication = clusters.communication || {};
            const subscriptions = communication.subscriptions || {};
            const validatedClusters = communication.validated_clusters || {};
            const databaseClusters = clusters.database_clusters || {};
            
            // Count database clusters (these are actually registered and active)
            const dbClusterCount = Object.keys(databaseClusters).length;
            
            // Count only actually online clusters from validation
            const onlineClusters = Object.values(validatedClusters).filter(
                cluster => cluster && cluster.actual_status === 'online'
            ).length;
            
            // Use database clusters as primary source
            const activeCount = dbClusterCount > 0 ? dbClusterCount : onlineClusters;
            
            let html = `
                <div class="stat-grid">
                    <div class="stat">
                        <span class="stat-value ${activeCount > 0 ? 'positive' : 'negative'}">${activeCount}</span>
                        <span class="stat-label">Active</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">0</span>
                        <span class="stat-label">Pending</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">0</span>
                        <span class="stat-label">Failed</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">${dbClusterCount}</span>
                        <span class="stat-label">Registered</span>
                    </div>
                </div>
            `;
            
            if (dbClusterCount === 0 && onlineClusters === 0) {
                html += `
                    <div class="empty-state">
                        <div class="icon">🏗️</div>
                        <div class="title">No Active Clusters</div>
                        <div class="description">Connect orchestrator clusters to manage trading operations</div>
                    </div>
                `;
            } else {
                // Show database clusters first
                if (dbClusterCount > 0) {
                    html += '<div style="margin-top: 20px;"><strong>Registered Clusters (Database):</strong><br><br>';
                    Object.entries(databaseClusters).forEach(([containerId, cluster]) => {
                        const lastHeartbeat = cluster.last_heartbeat ? new Date(cluster.last_heartbeat) : null;
                        const heartbeatAge = lastHeartbeat ? ((new Date() - lastHeartbeat) / 1000).toFixed(0) : 'Never';
                        const isRecent = heartbeatAge !== 'Never' && parseInt(heartbeatAge) < 120; // Within 2 minutes
                        
                        html += `
                            <div style="background: rgba(34, 197, 94, 0.1); padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <strong>${isRecent ? '🟢' : '🟡'} ${cluster.cluster_name}</strong>
                                    <span class="stat-value ${isRecent ? 'positive' : 'warning'}" style="font-size: 0.9rem;">
                                        ${isRecent ? 'ACTIVE' : 'STALE'}
                                    </span>
                                </div>
                                <div style="font-size: 0.85rem; opacity: 0.8;">
                                    Type: ${cluster.agent_type} • 
                                    Host: ${cluster.host_address}:${cluster.api_port} • 
                                    Last HB: ${heartbeatAge}s ago
                                </div>
                                <div style="font-size: 0.8rem; opacity: 0.6; margin-top: 4px;">
                                    ID: ${cluster.container_id}
                                </div>
                            </div>
                        `;
                    });
                    html += '</div>';
                }
                
                // Also show validated clusters if different
                if (onlineClusters > 0 && dbClusterCount === 0) {
                    html += '<div style="margin-top: 20px;"><strong>Detected Clusters (Not in DB):</strong><br><br>';
                    Object.entries(validatedClusters).forEach(([name, cluster]) => {
                        if (cluster && cluster.actual_status === 'online') {
                            html += `
                                <div style="background: rgba(251, 146, 60, 0.1); padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <strong>⚠️ ${name}</strong>
                                        <span class="stat-value warning" style="font-size: 0.9rem;">NOT REGISTERED</span>
                                    </div>
                                    <div style="font-size: 0.85rem; opacity: 0.8;">
                                        Health: ${cluster.health_check ? '✅ Healthy' : '⚠️ Checking'} • 
                                        Container: ${cluster.container_status || 'Running'}
                                    </div>
                                </div>
                            `;
                        }
                    });
                    html += '</div>';
                }
            }
            
            return html;
        }
        
        function renderTradingActivity(system, portfolio) {
            const isActive = system.is_running === true;
            const positions = portfolio.positions || {};
            const positionCount = Object.keys(positions).length;
            const recentTrades = portfolio.recent_trades || [];
            
            let html = `
                <div class="stat-grid">
                    <div class="stat">
                        <span class="stat-value ${isActive ? 'positive' : 'negative'}">
                            ${isActive ? 'Active' : 'Stopped'}
                        </span>
                        <span class="stat-label">Trading Status</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">${positionCount}</span>
                        <span class="stat-label">Open Positions</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">${recentTrades.length}</span>
                        <span class="stat-label">Recent Trades</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">$${(portfolio.cash_balance || 0).toFixed(2)}</span>
                        <span class="stat-label">Cash Balance</span>
                    </div>
                </div>
            `;
            
            // Show recent trades
            if (recentTrades.length > 0) {
                html += '<div style="margin-top: 20px;"><strong>Recent Trades:</strong><br><br>';
                recentTrades.slice(0, 5).forEach(trade => {
                    const tradeTime = new Date(trade.executed_at).toLocaleTimeString();
                    const clusterInfo = trade.cluster_name || trade.agent_id || 'Manual';
                    html += `
                        <div style="background: rgba(59, 130, 246, 0.1); padding: 10px; border-radius: 6px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <strong>${trade.side.toUpperCase()} ${trade.symbol}</strong>
                                <span>${tradeTime}</span>
                            </div>
                            <div style="font-size: 0.85rem; opacity: 0.8;">
                                ${trade.quantity} shares @ $${trade.price.toFixed(2)} = $${trade.total_value.toFixed(2)}
                            </div>
                            <div style="font-size: 0.8rem; opacity: 0.6; margin-top: 2px;">
                                Cluster: ${clusterInfo}
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
            } else if (positionCount === 0) {
                html += `
                    <div class="empty-state">
                        <div class="icon">📈</div>
                        <div class="title">No Trading Activity</div>
                        <div class="description">Start trading to see live activity and positions here</div>
                    </div>
                `;
            }
            
            return html;
        }
        
        function renderPortfolio(portfolio) {
            if (portfolio.error) {
                return `<div class="error-message">Portfolio data unavailable: ${portfolio.error}</div>`;
            }
            
            const totalValue = portfolio.total_value || 0;
            const totalPnl = portfolio.total_pnl || 0;
            const totalPnlPct = portfolio.total_pnl_percent || 0;
            const positions = portfolio.positions || {};
            
            let html = `
                <div class="stat-grid">
                    <div class="stat">
                        <span class="stat-value neutral">$${totalValue.toFixed(2)}</span>
                        <span class="stat-label">Total Value</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value ${totalPnl >= 0 ? 'positive' : 'negative'}">$${totalPnl.toFixed(2)}</span>
                        <span class="stat-label">Total P&L</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value ${totalPnlPct >= 0 ? 'positive' : 'negative'}">${totalPnlPct.toFixed(2)}%</span>
                        <span class="stat-label">Return %</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value neutral">$${(portfolio.positions_value || 0).toFixed(2)}</span>
                        <span class="stat-label">Positions Value</span>
                    </div>
                </div>
            `;
            
            // Show positions
            const positionEntries = Object.entries(positions);
            if (positionEntries.length > 0) {
                html += '<div style="margin-top: 20px;"><strong>Current Positions:</strong><br><br>';
                positionEntries.forEach(([symbol, pos]) => {
                    const pnl = pos.unrealized_pnl || 0;
                    const pnlPct = pos.unrealized_pnl_percent || 0;
                    html += `
                        <div style="background: rgba(34, 197, 94, 0.1); padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                <strong>${symbol}</strong>
                                <span class="stat-value ${pnl >= 0 ? 'positive' : 'negative'}" style="font-size: 0.9rem;">
                                    ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)} (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%)
                                </span>
                            </div>
                            <div style="font-size: 0.85rem; opacity: 0.8;">
                                ${pos.quantity} shares @ $${pos.average_price.toFixed(2)} avg
                                ${pos.current_price ? ` • Current: $${pos.current_price.toFixed(2)}` : ''}
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
            }
            
            return html;
        }
        
        function renderError(message) {
            const content = document.getElementById('dashboard-content');
            content.innerHTML = `
                <div class="card" style="grid-column: 1 / -1;">
                    <div class="error-message">
                        <strong>⚠️ Dashboard Error:</strong> ${message}
                    </div>
                </div>
            `;
        }
        
        // Initialize dashboard
        loadDashboard();
        
        // Auto-refresh every 30 seconds
        setInterval(loadDashboard, 30000);
    </script>
</body>
</html>'''

@router.get("", response_class=HTMLResponse)
async def get_clean_dashboard():
    """Serve the clean dashboard interface"""
    return HTMLResponse(content=CLEAN_DASHBOARD_HTML)

@router.get("/", response_class=HTMLResponse)
async def get_clean_dashboard_root():
    """Serve the clean dashboard interface"""
    return HTMLResponse(content=CLEAN_DASHBOARD_HTML)

@router.get("/api/portfolio-status")
async def get_public_portfolio_status():
    """Public portfolio status endpoint for dashboard (no auth required)"""
    try:
        from ..db_models import get_db, get_portfolio_status, Trade
        
        # Get database session
        for db in get_db():
            portfolio_data = get_portfolio_status(db)
            
            # Calculate actual cash balance from trades
            trades = db.query(Trade).all()
            starting_cash = 100000.0
            cash_spent = sum(t.total_value for t in trades if t.side == 'buy')
            cash_received = sum(t.total_value for t in trades if t.side == 'sell')
            cash_balance = starting_cash - cash_spent + cash_received
            
            positions_value = portfolio_data.get('total_value', 0)
            total_value = cash_balance + positions_value
            
            # Calculate real P&L
            total_pnl = total_value - starting_cash  # Real P&L is total value minus starting capital
            total_pnl_percent = (total_pnl / starting_cash * 100) if starting_cash > 0 else 0
            
            result = {
                "total_value": total_value,
                "cash_balance": cash_balance,
                "positions": portfolio_data.get('positions', {}),
                "positions_value": positions_value,
                "total_pnl": total_pnl,
                "total_pnl_percent": total_pnl_percent,
                "recent_trades": portfolio_data.get('recent_trades', [])
            }
            break
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting public portfolio status: {e}")
        return {"error": str(e)}

@router.get("/api/cluster-status")
async def get_public_cluster_status():
    """Public cluster status endpoint for dashboard (no auth required)"""
    try:
        # Import here to avoid circular imports
        from ..core.orchestration.container_registry import container_registry
        from ..infrastructure.messaging.container_hub import container_hub
        from ..db_models import get_db, get_active_clusters
        import json
        
        # Get communication hub statistics (this shows connected clusters)
        hub_stats = await container_hub.get_hub_statistics()
        
        # Get basic cluster info without validation to avoid auth issues
        cluster_status = await container_registry.get_cluster_status()
        
        # Get active clusters from database
        db_clusters = {}
        try:
            # Get database session
            for db in get_db():
                active_clusters = get_active_clusters(db)
                for cluster in active_clusters:
                    db_clusters[cluster.container_id] = {
                        "container_id": cluster.container_id,
                        "cluster_name": cluster.cluster_name,
                        "agent_id": cluster.agent_id,
                        "agent_type": cluster.agent_type,
                        "host_address": cluster.host_address,
                        "api_port": cluster.api_port,
                        "is_active": cluster.is_active,
                        "last_heartbeat": cluster.last_heartbeat.isoformat() if cluster.last_heartbeat else None,
                        "registered_at": cluster.registered_at.isoformat() if cluster.registered_at else None,
                        "capabilities": json.loads(cluster.capabilities) if cluster.capabilities else {},
                        "resources": json.loads(cluster.resources) if cluster.resources else {}
                    }
                break  # Exit after first db session
        except Exception as db_error:
            logger.warning(f"Could not fetch database clusters: {db_error}")
        
        # Merge database clusters with hub stats
        if db_clusters:
            hub_stats["database_clusters"] = db_clusters
            # Update subscriptions to reflect database state
            hub_stats["active_clusters_count"] = len(db_clusters)
        
        # Simple response for dashboard
        return {
            "status": "success",
            "communication": hub_stats,
            "cluster": cluster_status,
            "database_clusters": db_clusters,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting public cluster status: {e}")
        return {
            "status": "error", 
            "error": str(e),
            "communication": {"subscriptions": {}, "validated_clusters": {}},
            "cluster": {},
            "database_clusters": {},
            "timestamp": datetime.utcnow().isoformat()
        }