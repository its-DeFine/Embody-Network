#!/usr/bin/env python3
"""
Generate AI-enhanced architecture diagram for the event-driven trading system.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch, Circle
import matplotlib.lines as mlines

# Create figure
fig, ax = plt.subplots(1, 1, figsize=(18, 14))
ax.set_xlim(0, 18)
ax.set_ylim(0, 14)
ax.axis('off')

# Title
ax.text(9, 13.5, 'AI-Powered Event-Driven Trading System', 
        fontsize=24, fontweight='bold', ha='center')
ax.text(9, 12.9, 'with AutoGen Multi-Agent Teams', 
        fontsize=18, ha='center', style='italic', color='#34495e')

# Define colors
color_event_loop = '#3498db'      # Blue
color_handlers = '#2ecc71'        # Green  
color_trading = '#e74c3c'         # Red
color_monitor = '#f39c12'         # Orange
color_config = '#9b59b6'          # Purple
color_api = '#1abc9c'             # Turquoise
color_ai = '#e91e63'              # AI Pink
color_autogen = '#ff5722'         # AutoGen Orange

# Event Loop (Center) - Smaller to make room
event_loop = FancyBboxPatch((7, 5.5), 4, 1.8,
                           boxstyle="round,pad=0.1",
                           facecolor=color_event_loop,
                           edgecolor='black',
                           linewidth=2,
                           alpha=0.9)
ax.add_patch(event_loop)
ax.text(9, 6.7, 'Event Loop', fontsize=14, fontweight='bold', 
        ha='center', va='center', color='white')
ax.text(9, 6.2, '• Dispatch events\n• Manage AI teams',
        fontsize=10, ha='center', va='center', color='white')

# AutoGen Market Analysis Team (Top Left)
autogen_market = FancyBboxPatch((0.5, 8), 5, 3.5,
                               boxstyle="round,pad=0.1",
                               facecolor=color_autogen,
                               edgecolor='black',
                               linewidth=2,
                               alpha=0.9)
ax.add_patch(autogen_market)
ax.text(3, 10.8, 'AutoGen Market Analysis Team', fontsize=13, fontweight='bold',
        ha='center', color='white')

# Individual agents in market team
agent_positions = [(1.5, 9.5), (2.5, 8.5), (3.5, 9.5), (4.5, 8.5)]
agent_names = ['Technical\nAnalyst', 'Fundamental\nAnalyst', 'Risk\nManager', 'Coordinator']
for pos, name in zip(agent_positions, agent_names):
    agent = Circle(pos, 0.5, facecolor='white', edgecolor=color_ai, linewidth=2)
    ax.add_patch(agent)
    ax.text(pos[0], pos[1], name, fontsize=8, ha='center', va='center')

# AutoGen Execution Team (Top Right)
autogen_exec = FancyBboxPatch((12.5, 8), 5, 3.5,
                             boxstyle="round,pad=0.1",
                             facecolor=color_autogen,
                             edgecolor='black',
                             linewidth=2,
                             alpha=0.9)
ax.add_patch(autogen_exec)
ax.text(15, 10.8, 'AutoGen Execution Team', fontsize=13, fontweight='bold',
        ha='center', color='white')

# Individual agents in execution team
exec_positions = [(13.5, 9.5), (14.5, 8.5), (15.5, 9.5), (16.5, 8.5)]
exec_names = ['Entry\nStrategist', 'Exit\nStrategist', 'Position\nSizer', 'Executor']
for pos, name in zip(exec_positions, exec_names):
    agent = Circle(pos, 0.5, facecolor='white', edgecolor=color_ai, linewidth=2)
    ax.add_patch(agent)
    ax.text(pos[0], pos[1], name, fontsize=8, ha='center', va='center')

# Configuration (Center Top)
config = FancyBboxPatch((7.5, 10), 3, 1.2,
                       boxstyle="round,pad=0.1",
                       facecolor=color_config,
                       alpha=0.9)
ax.add_patch(config)
ax.text(9, 10.6, 'AI Config', fontsize=12, fontweight='bold',
        ha='center', va='center', color='white')

# API Monitor (Left)
api_monitor = FancyBboxPatch((0.5, 4), 3, 2.5,
                            boxstyle="round,pad=0.1",
                            facecolor=color_monitor,
                            alpha=0.9)
ax.add_patch(api_monitor)
ax.text(2, 5.8, 'API Monitor', fontsize=12, fontweight='bold',
        ha='center', color='white')
ax.text(2, 5.2, '• Price feeds\n• Market data\n• AI triggers',
        fontsize=9, ha='center', va='center', color='white')

# AI Event Handlers (Right)
ai_handlers = FancyBboxPatch((14, 4), 3.5, 3,
                            boxstyle="round,pad=0.1",
                            facecolor=color_ai,
                            alpha=0.9)
ax.add_patch(ai_handlers)
ax.text(15.75, 6.5, 'AI Event Handlers', fontsize=12, fontweight='bold',
        ha='center', color='white')
ax.text(15.75, 5.8, '• AI Market Analysis\n• AI Signal Generation\n• AI Risk Monitor\n• Team Coordinator',
        fontsize=9, ha='center', va='center', color='white')

# Trading Engine (Bottom Right)
trading_engine = FancyBboxPatch((12, 0.5), 4, 2.5,
                               boxstyle="round,pad=0.1",
                               facecolor=color_trading,
                               alpha=0.9)
ax.add_patch(trading_engine)
ax.text(14, 2.3, 'Trading Engine', fontsize=12, fontweight='bold',
        ha='center', color='white')
ax.text(14, 1.7, '• Execute AI trades\n• Manage positions\n• Risk control\n• Performance tracking',
        fontsize=9, ha='center', va='center', color='white')

# Time Events (Bottom Left)
time_events = FancyBboxPatch((2, 0.5), 4, 1.5,
                            boxstyle="round,pad=0.1",
                            facecolor=color_api,
                            alpha=0.9)
ax.add_patch(time_events)
ax.text(4, 1.5, 'Time-Based Events', fontsize=11, fontweight='bold',
        ha='center', color='white')
ax.text(4, 1, 'AI analysis triggers',
        fontsize=9, ha='center', color='white')

# Arrows with labels
arrow_props = dict(arrowstyle='->', lw=2.5, color='black')
ai_arrow_props = dict(arrowstyle='->', lw=3, color=color_ai)

# Config to Event Loop
ax.annotate('', xy=(9, 7.3), xytext=(9, 10),
            arrowprops=arrow_props)

# AutoGen Teams to Event Loop
ax.annotate('', xy=(7.5, 6.5), xytext=(5.5, 9),
            arrowprops=dict(arrowstyle='->', lw=3, color=color_autogen,
                          connectionstyle="arc3,rad=0.3"))
ax.text(6, 7.5, 'Team\nAnalysis', fontsize=9, ha='center', color=color_autogen, fontweight='bold')

ax.annotate('', xy=(10.5, 6.5), xytext=(12.5, 9),
            arrowprops=dict(arrowstyle='->', lw=3, color=color_autogen,
                          connectionstyle="arc3,rad=-0.3"))
ax.text(11.5, 7.5, 'Team\nDecisions', fontsize=9, ha='center', color=color_autogen, fontweight='bold')

# API Monitor to Event Loop
ax.annotate('', xy=(7, 6), xytext=(3.5, 5.5),
            arrowprops=dict(arrowstyle='->', lw=2, color='black',
                          connectionstyle="arc3,rad=0.3"))

# Time Events to Event Loop
ax.annotate('', xy=(7, 5.5), xytext=(6, 2),
            arrowprops=arrow_props)

# Event Loop to AI Handlers
ax.annotate('', xy=(14, 5.5), xytext=(11, 6.3),
            arrowprops=ai_arrow_props)
ax.text(12.5, 6, 'AI events', fontsize=9, ha='center', color=color_ai, fontweight='bold')

# AI Handlers to Trading Engine
ax.annotate('', xy=(14, 3), xytext=(15, 4),
            arrowprops=ai_arrow_props)

# Trading Engine feedback to Event Loop
ax.annotate('', xy=(9, 5.5), xytext=(12, 2),
            arrowprops=dict(arrowstyle='->', lw=2, color='gray',
                          connectionstyle="arc3,rad=0.5", linestyle='dashed'))
ax.text(10, 3.5, 'feedback', fontsize=8, ha='center', color='gray', style='italic')

# AI Decision Flow Box
flow_box = FancyBboxPatch((6.5, 2.8), 5, 1.8,
                         boxstyle="round,pad=0.05",
                         facecolor='white',
                         edgecolor=color_ai,
                         linewidth=2,
                         linestyle='dashed',
                         alpha=0.7)
ax.add_patch(flow_box)
ax.text(9, 3.9, 'AI Decision Pipeline', fontsize=10, ha='center', fontweight='bold', color=color_ai)
ax.text(9, 3.4, 'Data → AutoGen Teams → Consensus → Signal → Trade',
        fontsize=9, ha='center', color=color_ai)

# Add example flow
ax.text(1, -0.8, 'Example AI Flow:', fontsize=12, fontweight='bold')
ax.text(1, -1.3, '1. Time trigger → Event Loop → AI Market Analysis Handler → AutoGen Market Team discusses → Team consensus',
        fontsize=10)
ax.text(1, -1.7, '2. Team signals opportunity → AI Signal Handler → AutoGen Execution Team → Position sizing → Execute trade',
        fontsize=10)
ax.text(1, -2.1, '3. AI Risk Monitor → Continuous position monitoring → Dynamic adjustments → Exit strategy',
        fontsize=10)

# Legend
legend_elements = [
    mlines.Line2D([0], [0], marker='s', color='w', markerfacecolor=color_event_loop, markersize=10, label='Core System'),
    mlines.Line2D([0], [0], marker='s', color='w', markerfacecolor=color_autogen, markersize=10, label='AutoGen Teams'),
    mlines.Line2D([0], [0], marker='s', color='w', markerfacecolor=color_ai, markersize=10, label='AI Components'),
    mlines.Line2D([0], [0], marker='s', color='w', markerfacecolor=color_trading, markersize=10, label='Execution'),
]
ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))

plt.tight_layout()
plt.savefig('/home/geo/operation/event-driven-trader/architecture_ai.png', dpi=300, bbox_inches='tight')
plt.savefig('/home/geo/operation/event-driven-trader/architecture_ai.svg', format='svg', bbox_inches='tight')
print("AI architecture diagram saved as architecture_ai.png and architecture_ai.svg")