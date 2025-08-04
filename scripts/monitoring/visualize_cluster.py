#!/usr/bin/env python3
"""
Cluster Topology Visualizer
Shows a visual representation of the distributed container cluster
"""

import asyncio
import aiohttp
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.tree import Tree
from rich import box
import time

# Configuration
CENTRAL_MANAGER_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@trading.system"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default-admin-password-change-in-production-32chars!")

console = Console()


async def authenticate():
    """Get authentication token"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{CENTRAL_MANAGER_URL}/api/v1/auth/login",
            json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["access_token"]
            return None


async def get_cluster_data(token):
    """Fetch cluster data"""
    headers = {"Authorization": f"Bearer {token}"}
    
    async with aiohttp.ClientSession() as session:
        # Get cluster status
        status_resp = await session.get(
            f"{CENTRAL_MANAGER_URL}/api/v1/cluster/status",
            headers=headers
        )
        status_data = await status_resp.json() if status_resp.status == 200 else {}
        
        # Get distribution
        dist_resp = await session.get(
            f"{CENTRAL_MANAGER_URL}/api/v1/cluster/metrics/distribution",
            headers=headers
        )
        dist_data = await dist_resp.json() if dist_resp.status == 200 else {}
        
        return status_data, dist_data


def create_cluster_tree(dist_data):
    """Create a tree visualization of the cluster"""
    tree = Tree("🌐 [bold blue]AutoGen Distributed Cluster[/bold blue]")
    
    # Add central manager
    cm = tree.add("📡 [bold green]Central Manager[/bold green]")
    cm.add("[dim]Port: 8000[/dim]")
    cm.add(f"[dim]Status: Operational[/dim]")
    
    # Add containers
    containers = dist_data.get("distribution", {})
    if containers:
        container_branch = tree.add(f"📦 [bold yellow]Containers ({len(containers)})[/bold yellow]")
        
        for container_id, info in containers.items():
            name = info.get("container_name", container_id)
            agent_count = info.get("agent_count", 0)
            health = info.get("health_score", 0)
            
            # Choose icon based on health
            if health >= 80:
                health_icon = "🟢"
            elif health >= 50:
                health_icon = "🟡"
            else:
                health_icon = "🔴"
            
            container = container_branch.add(
                f"{health_icon} [bold]{name}[/bold] ({agent_count} agents)"
            )
            
            # Add container details
            container.add(f"[dim]ID: {container_id[:12]}...[/dim]")
            container.add(f"[dim]Health: {health}%[/dim]")
            
            # Add resources
            resources = info.get("resources", {})
            if resources:
                res_node = container.add("📊 Resources")
                res_node.add(f"CPU: {resources.get('cpu_usage_percent', 0):.1f}%")
                res_node.add(f"Memory: {resources.get('memory_percent', 0):.1f}%")
            
            # Add agents
            agents = info.get("agents", [])
            if agents:
                agent_node = container.add(f"🤖 Agents ({len(agents)})")
                for agent in agents[:5]:  # Show first 5
                    agent_node.add(f"[dim]{agent}[/dim]")
                if len(agents) > 5:
                    agent_node.add(f"[dim]... and {len(agents) - 5} more[/dim]")
    
    return tree


def create_stats_table(status_data, dist_data):
    """Create statistics table"""
    table = Table(title="📊 Cluster Statistics", box=box.ROUNDED)
    
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    
    # Cluster stats
    cluster = status_data.get("cluster", {})
    table.add_row("Registered Containers", str(cluster.get("registered_containers", 0)))
    table.add_row("Active Containers", str(cluster.get("active_containers", 0)))
    table.add_row("Total Agents", str(dist_data.get("total_agents", 0)))
    
    # Discovery stats
    discovery = status_data.get("discovery", {})
    table.add_row("Discovery Running", "✅" if discovery.get("is_running") else "❌")
    table.add_row("Last Scan", discovery.get("last_scan_time", "Never"))
    
    # Communication stats
    comm = status_data.get("communication", {})
    if comm:
        messages = comm.get("message_stats", {})
        table.add_row("Messages Sent", str(messages.get("sent", 0)))
        table.add_row("Messages Routed", str(messages.get("routed", 0)))
    
    return table


def create_deployment_panel(dist_data):
    """Create deployment strategies panel"""
    content = "[bold]Available Strategies:[/bold]\n\n"
    
    strategies = [
        ("🔄 Round Robin", "Distribute agents evenly"),
        ("📊 Least Loaded", "Place on least busy container"),
        ("🎯 Capability Match", "Match agent requirements"),
        ("⚡ Resource Optimal", "Best resource fit"),
        ("🔗 Affinity Based", "Keep related agents together")
    ]
    
    for icon_name, desc in strategies:
        content += f"{icon_name}\n[dim]{desc}[/dim]\n\n"
    
    return Panel(content, title="🚀 Deployment Strategies", border_style="blue")


async def monitor_cluster():
    """Monitor cluster in real-time"""
    token = await authenticate()
    if not token:
        console.print("[red]❌ Authentication failed[/red]")
        return
    
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=4)
    )
    
    layout["main"].split_row(
        Layout(name="tree", ratio=2),
        Layout(name="right")
    )
    
    layout["right"].split_column(
        Layout(name="stats"),
        Layout(name="strategies")
    )
    
    with Live(layout, refresh_per_second=0.5, console=console) as live:
        while True:
            try:
                # Get latest data
                status_data, dist_data = await get_cluster_data(token)
                
                # Update header
                header_text = Panel(
                    f"[bold blue]AutoGen Distributed Cluster Monitor[/bold blue]\n"
                    f"[dim]Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
                    style="blue"
                )
                layout["header"].update(header_text)
                
                # Update main tree
                tree = create_cluster_tree(dist_data)
                layout["tree"].update(Panel(tree, title="🌍 Cluster Topology", border_style="green"))
                
                # Update stats
                stats_table = create_stats_table(status_data, dist_data)
                layout["stats"].update(stats_table)
                
                # Update strategies
                strategies = create_deployment_panel(dist_data)
                layout["strategies"].update(strategies)
                
                # Update footer
                footer_text = Panel(
                    "[dim]Press Ctrl+C to exit | Updates every 5 seconds[/dim]",
                    style="dim"
                )
                layout["footer"].update(footer_text)
                
                # Wait before next update
                await asyncio.sleep(5)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                await asyncio.sleep(5)


def main():
    """Main entry point"""
    console.print("[bold green]🚀 Starting Cluster Monitor...[/bold green]")
    try:
        asyncio.run(monitor_cluster())
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Monitor stopped[/yellow]")


if __name__ == "__main__":
    main()