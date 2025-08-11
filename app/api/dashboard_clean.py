"""
VTuber Dashboard API
Clean dashboard for VTuber agent management
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any
import json
from datetime import datetime

from ..dependencies import get_current_user
from .._version import get_version, get_version_info

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# VTuber dashboard HTML template
VTUBER_DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎭 VTuber Management Dashboard</title>
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
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .card-title {
            font-size: 1.1rem;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .stat-item {
            text-align: center;
            padding: 10px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }
        
        .stat-value {
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9rem;
            opacity: 0.8;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin: 2px;
        }
        
        .status-online { background: rgba(72, 187, 120, 0.3); }
        .status-offline { background: rgba(245, 101, 101, 0.3); }
        .status-idle { background: rgba(237, 137, 54, 0.3); }
        
        .agent-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .agent-item {
            padding: 10px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .refresh-info {
            text-align: center;
            opacity: 0.7;
            font-size: 0.9rem;
            margin-top: 20px;
        }
        
        .error-message {
            background: rgba(245, 101, 101, 0.2);
            padding: 10px;
            border-radius: 8px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🎭 VTuber Agent Management</h1>
            <p style="opacity: 0.8;">Real-Time Agent & Stream Monitoring</p>
            <p style="opacity: 0.6; font-size: 0.9rem;">Version: <span id="app-version">loading...</span></p>
        </div>
        
        <div id="dashboard-content">
            <div style="text-align: center; padding: 50px;">
                <div style="font-size: 2rem;">⏳</div>
                <p>Loading dashboard data...</p>
            </div>
        </div>
        
        <div class="refresh-info">
            Dashboard refreshes every 5 seconds
        </div>
    </div>
    
    <script>
        async function loadDashboard() {
            try {
                // Load version info
                fetch('/api/v1/version').then(r => r.json()).then(v => {
                    document.getElementById('app-version').textContent = v.version;
                }).catch(() => {});
                
                // Load system status
                const systemResponse = await fetch('/api/v1/embodiment/agents');
                const agents = systemResponse.ok ? await systemResponse.json() : [];
                
                const dashboardData = {
                    agents: agents,
                    stats: {
                        total_agents: agents.length,
                        online_agents: agents.filter(a => a.status === 'online').length,
                        active_sessions: 0,
                        stream_status: 'ready'
                    },
                    timestamp: new Date().toISOString()
                };
                
                updateDashboard(dashboardData);
            } catch (error) {
                console.error('Dashboard error:', error);
                document.getElementById('dashboard-content').innerHTML = `
                    <div class="error-message">
                        Failed to load dashboard data: ${error.message}
                    </div>
                `;
            }
        }
        
        function updateDashboard(data) {
            const content = document.getElementById('dashboard-content');
            const stats = data.stats || {};
            const agents = data.agents || [];
            
            content.innerHTML = `
                <div class="grid">
                    <!-- System Overview -->
                    <div class="card">
                        <div class="card-title">📊 System Overview</div>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-value">${stats.total_agents || 0}</div>
                                <div class="stat-label">Total Agents</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${stats.online_agents || 0}</div>
                                <div class="stat-label">Online</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${stats.active_sessions || 0}</div>
                                <div class="stat-label">Active Sessions</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${stats.stream_status || 'N/A'}</div>
                                <div class="stat-label">Stream Status</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Agent Status -->
                    <div class="card">
                        <div class="card-title">🎭 Agent Status</div>
                        <div class="agent-list">
                            ${renderAgents(agents)}
                        </div>
                    </div>
                </div>
                
                <div class="grid">
                    <!-- Stream Info -->
                    <div class="card">
                        <div class="card-title">📺 Stream Information</div>
                        <div style="padding: 10px;">
                            <p>RTMP: rtmp://localhost:1935/live</p>
                            <p>HLS: http://localhost:8085/hls/stream.m3u8</p>
                            <p>Status: <span class="status-badge status-online">Ready</span></p>
                        </div>
                    </div>
                    
                    <!-- Recent Activity -->
                    <div class="card">
                        <div class="card-title">📝 Recent Activity</div>
                        <div style="padding: 10px; opacity: 0.8;">
                            <p>No recent activity</p>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function renderAgents(agents) {
            if (!agents || agents.length === 0) {
                return '<p style="text-align: center; opacity: 0.7;">No agents registered</p>';
            }
            
            return agents.map(agent => `
                <div class="agent-item">
                    <div>
                        <strong>${agent.name || agent.agent_id}</strong>
                        <br>
                        <small style="opacity: 0.7;">${agent.agent_id}</small>
                    </div>
                    <span class="status-badge status-${agent.status || 'offline'}">
                        ${agent.status || 'offline'}
                    </span>
                </div>
            `).join('');
        }
        
        // Initial load
        loadDashboard();
        
        // Refresh every 5 seconds
        setInterval(loadDashboard, 5000);
    </script>
</body>
</html>'''

@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Get the VTuber management dashboard"""
    return HTMLResponse(content=VTUBER_DASHBOARD_HTML)

@router.get("/api/status")
async def get_dashboard_status(user: Dict = Depends(get_current_user)):
    """Get dashboard status data"""
    return {
        "status": "operational",
        "mode": "vtuber",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "agents": True,
            "streaming": True,
            "orchestration": True
        }
    }

@router.get("/api/agents-summary")
async def get_agents_summary(user: Dict = Depends(get_current_user)):
    """Get summary of agents for dashboard"""
    # This would connect to the embodiment registry in production
    return {
        "total": 0,
        "online": 0,
        "agents": [],
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/api/version")
async def get_version_endpoint():
    """Get application version information"""
    return get_version_info()