# Orchestrator System Container Hierarchy

## 🎯 **Simple 2-Container Architecture**

The orchestrator platform has exactly **2 container types**:

### Level 1: Central Manager (Your Infrastructure)
### Level 2: Orchestrator Clusters (Customer Infrastructure)

That's it! No additional containers needed.

## 🏗️ **Complete Container Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                   YOUR INFRASTRUCTURE                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Central Manager + Redis                         │ │
│  │                  (Port 8000 + 6379)                         │ │
│  └─────────────────────────┬───────────────────────────────────┘ │
└──────────────────────────────┼──────────────────────────────────────┘
                               │ Internet/Network
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│  CUSTOMER 1          │ │  CUSTOMER 2          │ │  CUSTOMER N          │
│  ┌────────────────┐  │ │  ┌────────────────┐  │ │  ┌────────────────┐  │
│  │ Orchestrator   │  │ │  │ Orchestrator   │  │ │  │ Orchestrator   │  │
│  │ Agent          │  │ │  │ Agent          │  │ │  │ Agent          │  │
│  │ (Port 8001)    │  │ │  │ (Port 8001)    │  │ │  │ (Port 8001)    │  │
│  └────────────────┘  │ │  └────────────────┘  │ │  └────────────────┘  │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘
```

## 📦 **Container Deployment Details**

### Your Infrastructure Deployment
```bash
# Deploy Central Manager + Redis
docker-compose -f docker-compose.central-manager.yml up -d
```

**Containers Created**:
- `central-manager` - Orchestrator coordination hub
- `central-redis` - Shared state for all orchestrator clusters

### Customer Infrastructure Deployment  
```bash
# Customer deploys orchestrator cluster
export CENTRAL_MANAGER_HOST=your-ip
export ORCHESTRATOR_ID=customer1
docker-compose -f docker-compose.orchestrator-cluster.yml up -d
```

**Containers Created**:
- `orchestrator-cluster-customer1` - Agent cluster (connects to your central manager)

## 🤖 **Agent Management (No Additional Containers)**

### How Agents Work
- **Agents run INSIDE orchestrator containers**
- **Central Manager deploys agents via API calls**
- **No separate containers for individual agents**

### Agent Deployment Flow
```bash
# You deploy agent to customer cluster
curl -X POST http://localhost:8000/api/v1/cluster/agents/deploy \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "agent_type": "trading_agent",
    "preferred_container": "orchestrator-cluster-customer1"
  }'
```

**What happens**:
1. Central Manager receives deployment request
2. Selects customer's orchestrator container
3. Sends deployment command to orchestrator agent
4. Orchestrator agent launches trading agent **internally**
5. Trading agent runs inside orchestrator container

### Multiple Agents in Same Container
```
📦 orchestrator-cluster-customer1
├── 🤖 trading-agent-001 (momentum strategy)
├── 🤖 trading-agent-002 (arbitrage strategy)
├── 📊 analysis-agent-001 (technical analysis)
├── 🛡️ risk-agent-001 (position monitoring)
└── 🔧 custom-agent-001 (customer specific)
```

All run inside the same orchestrator container, managed by your central manager.

## 🔄 **Complete System Flow**

### 1. Initial Setup
```bash
# Step 1: You deploy central hub
docker-compose -f docker-compose.central-manager.yml up -d

# Step 2: Customer deploys orchestrator cluster
docker-compose -f docker-compose.orchestrator-cluster.yml up -d
# → Automatically registers with your central manager
```

### 2. Agent Management
```bash
# Step 3: You deploy agents to customer clusters
curl -X POST http://localhost:8000/api/v1/cluster/agents/deploy \
  -d '{"agent_type": "trading_agent", "orchestrator_id": "customer1"}'
# → Agent runs inside customer's orchestrator container
```

### 3. Monitoring & Control
```bash
# Monitor all orchestrator clusters
curl http://localhost:8000/api/v1/cluster/containers

# Check specific customer cluster
curl http://customer-ip:8001/health

# View agents in customer cluster
curl http://customer-ip:8001/agents
```

## 🎯 **Resource Management**

### Container Resource Allocation

**Your Infrastructure**:
```yaml
# Central Manager resources
central-manager:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 4G
      reservations:
        cpus: '2'
        memory: 2G

# Redis resources  
redis:
  command: >
    redis-server
    --maxmemory 4gb
    --maxmemory-policy allkeys-lru
```

**Customer Infrastructure**:
```yaml
# Orchestrator container resources (shared among all agents)
orchestrator-agent:
  deploy:
    resources:
      limits:
        cpus: '4'      # Shared by all agents in container
        memory: 4G     # Shared by all agents in container
```

### Agent Resource Consumption
- **Trading Agent**: ~0.5 CPU, 256MB RAM
- **Analysis Agent**: ~1 CPU, 512MB RAM  
- **Risk Agent**: ~0.25 CPU, 128MB RAM
- **Custom Agent**: Varies by implementation

**Example**: 4 CPU / 4GB orchestrator container can run:
- 6 trading agents + 2 analysis agents + 4 risk agents

## 🔍 **System Monitoring**

### Container Health Monitoring
```bash
# Check your central manager
curl http://localhost:8000/health

# Check customer orchestrator clusters
curl http://customer1-ip:8001/health
curl http://customer2-ip:8001/health
```

### Agent Monitoring  
```bash
# View all agents across all orchestrator clusters
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/cluster/agents

# View agents in specific orchestrator cluster
curl http://customer1-ip:8001/agents
```

### Resource Monitoring
```bash
# Monitor container resources
docker stats central-manager central-redis
docker stats orchestrator-cluster-customer1

# Monitor agent resource usage within containers
curl http://customer1-ip:8001/metrics
```

## ✅ **Container Deployment Matrix**

| Component | Container Name | Infrastructure | Connects To | Purpose |
|-----------|----------------|----------------|-------------|---------|
| **Central Manager** | `central-manager` | Yours | - | Orchestrator coordination |
| **Redis** | `central-redis` | Yours | - | Shared state storage |
| **Orchestrator Agent** | `orchestrator-cluster-{ID}` | Customer | Your Central Manager + Redis | Agent cluster manager |

### Dependencies
- **Central Manager**: No dependencies (root component)
- **Redis**: No dependencies (shared storage)
- **Orchestrator Agent**: Depends on Central Manager + Redis

## 🎯 **Key Insights**

### Why This Architecture Works
1. **Minimal Infrastructure**: Only 2 container types needed
2. **Scalable**: Unlimited orchestrator clusters can connect
3. **Efficient**: Multiple agents share orchestrator container resources
4. **Manageable**: Central coordination with distributed execution
5. **Secure**: Customer controls infrastructure, you control orchestration

### Production Benefits
- **Low maintenance**: Few containers to manage
- **High scalability**: Easy to add orchestrator clusters
- **Cost effective**: Efficient resource utilization
- **Network efficient**: Minimal cross-network communication
- **Fault tolerant**: Orchestrator clusters operate independently

**Simple, scalable, production-ready orchestrator architecture.** 🚀