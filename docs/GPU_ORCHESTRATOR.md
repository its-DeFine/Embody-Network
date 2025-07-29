# GPU Orchestrator Integration Guide

This guide explains how to deploy and manage GPU-enabled AutoGen agents using the integrated agent-net orchestrator system.

## Overview

The GPU orchestrator integration brings together:
- **agent-net**: Livepeer-based GPU orchestrator with payment system
- **Ollama**: Local LLM inference with GPU acceleration
- **AutoGen Platform**: Multi-agent orchestration and management

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Control Board │────▶│  Agent Manager  │────▶│ GPU Orchestrator│
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                         │
         ▼                       ▼                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Orchestrator    │────▶│     Ollama      │────▶│  GPU Agents     │
│    Adapter      │     │   (LLM Server)  │     │  (Containers)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Prerequisites

1. **NVIDIA GPU** with CUDA support
2. **NVIDIA Container Toolkit** installed
3. **Docker** with GPU support enabled
4. At least **24GB VRAM** for CodeLlama 34B model

### Installing NVIDIA Container Toolkit

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

## Quick Start

1. **Configure GPU environment**:
```bash
cp .env.gpu.example .env.gpu
# Edit .env.gpu with your settings
```

2. **Start GPU-enabled services**:
```bash
# Start core services first
docker-compose up -d rabbitmq redis

# Start GPU orchestrator stack
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

3. **Verify GPU detection**:
```bash
# Check orchestrator status
curl http://localhost:8002/status

# Check GPU metrics
curl http://localhost:8002/health
```

4. **Deploy a GPU agent**:
```bash
# Via API
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GPU Trading Analyst",
    "type": "analysis",
    "requires_gpu": true,
    "model": "codellama:34b-instruct-q4_k_m",
    "config": {
      "trading_pairs": ["BTC/USDT", "ETH/USDT"]
    }
  }'
```

## Configuration

### GPU Allocation Strategies

Set `GPU_ALLOCATION_STRATEGY` in `.env.gpu`:

- **least_loaded** (default): Assigns to GPU with lowest utilization
- **round_robin**: Distributes evenly across GPUs
- **temperature**: Prefers cooler GPUs to prevent thermal throttling

### Model Management

Models are automatically downloaded on first use. To preload models:

```bash
# Preload specific model
docker exec autogen-ollama ollama pull codellama:34b-instruct-q4_k_m

# List loaded models
docker exec autogen-ollama ollama list
```

### Resource Limits

Configure in `.env.gpu`:
- `MAX_AGENTS_PER_GPU`: Maximum agents per GPU (default: 5)
- `MAX_VRAM_UTILIZATION`: Maximum VRAM usage percentage (default: 90%)
- `GPU_MEMORY_RESERVE_MB`: Reserved VRAM for system (default: 2048MB)

## Agent Configuration

### GPU-Required Agent Example

```python
agent_config = {
    "name": "Advanced Market Analyzer",
    "type": "analysis",
    "requires_gpu": true,
    "model": "codellama:34b-instruct-q4_k_m",
    "gpu_requirement": {
        "min_vram_mb": 20000,
        "compute_capability": "7.0"
    },
    "autogen_config": {
        "system_message": "You are an expert market analyst...",
        "llm_config": {
            "model": "codellama:34b-instruct-q4_k_m",
            "api_base": "http://ollama:11434/v1",
            "api_type": "ollama"
        }
    }
}
```

### Supported Models

| Model | VRAM Required | Use Case |
|-------|--------------|----------|
| codellama:34b-instruct-q4_k_m | ~20GB | Complex code generation, analysis |
| codellama:13b | ~8GB | General coding tasks |
| llama2:13b | ~8GB | General purpose |
| mistral:7b-instruct | ~4GB | Fast inference, chat |
| mixtral:8x7b | ~25GB | Advanced reasoning |

## Monitoring

### GPU Metrics Dashboard

Access Grafana at http://localhost:3000 for:
- GPU utilization and temperature
- VRAM usage per model
- Agent allocation across GPUs
- Inference latency metrics

### CLI Monitoring

```bash
# GPU status
docker exec autogen-orchestrator-adapter curl localhost:8002/status

# Payment statistics
docker exec autogen-orchestrator-adapter curl localhost:8002/payments/stats

# Agent allocations
docker exec autogen-agent-manager curl localhost:8080/gpu/allocations
```

## Multi-GPU Setup

For multiple GPUs on one host:

1. Set GPU visibility in docker-compose:
```yaml
environment:
  - NVIDIA_VISIBLE_DEVICES=0,1  # Use GPU 0 and 1
```

2. Configure orchestrator for multi-GPU:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 2  # Number of GPUs
          capabilities: [gpu]
```

## Swarm Deployment

For multi-host GPU swarm:

1. **Initialize Swarm** (on manager):
```bash
docker swarm init
```

2. **Join GPU workers**:
```bash
# On each GPU node
docker swarm join --token <worker-token> <manager-ip>:2377
```

3. **Deploy stack**:
```bash
docker stack deploy -c docker-compose.swarm.yml -c docker-compose.gpu.yml autogen-gpu
```

## Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA driver
nvidia-smi

# Verify Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Check container GPU access
docker exec autogen-ollama nvidia-smi
```

### Model Loading Issues

```bash
# Check Ollama logs
docker logs autogen-ollama

# Manually load model
docker exec -it autogen-ollama ollama run codellama:34b-instruct-q4_k_m

# Check model storage
docker exec autogen-ollama ls -la /root/.ollama/models
```

### High VRAM Usage

```bash
# Unload unused models
docker exec autogen-ollama ollama rm <model-name>

# Restart Ollama to clear VRAM
docker-compose restart ollama
```

## Payment System

The GPU orchestrators use Livepeer's probabilistic micropayment system:

- **Face Value**: Amount paid when ticket wins
- **Win Probability**: Chance of ticket winning
- **Expected Value**: face_value × win_probability

Configure in `.env.gpu`:
```bash
PRICE_PER_UNIT=100000000000000  # Wei
TICKET_EV=29000000000000        # Expected value
MAX_FACE_VALUE=1000000000000000 # Max payout
```

## Security Considerations

1. **Isolate GPU nodes** on separate network segment
2. **Use secrets management** for orchestrator keys
3. **Implement rate limiting** for GPU agent creation
4. **Monitor GPU memory** to prevent OOM attacks
5. **Audit model usage** for compliance

## Best Practices

1. **Model Selection**:
   - Use quantized models (Q4_K_M) for better memory efficiency
   - Match model size to available VRAM
   - Prefer specialized models over general ones

2. **Resource Management**:
   - Set conservative VRAM limits
   - Implement agent timeouts
   - Use model caching effectively

3. **Performance**:
   - Batch inference requests when possible
   - Use streaming for long responses
   - Monitor inference latency

## API Reference

### Orchestrator Adapter Endpoints

- `GET /health` - Health check
- `GET /status` - Detailed orchestrator status
- `POST /agents/allocate` - Allocate agent to GPU
- `DELETE /agents/{agent_id}` - Deallocate agent
- `GET /payments/stats` - Payment statistics
- `POST /webhook/livepeer` - Payment webhook

### Agent Manager GPU Extensions

- `GET /api/v1/gpu/status` - GPU cluster status
- `GET /api/v1/gpu/models` - Available models
- `POST /api/v1/agents` - Create agent (auto-detects GPU need)

## Future Enhancements

- [ ] Multi-region GPU orchestrator federation
- [ ] Automatic model optimization based on usage
- [ ] GPU sharing between lightweight agents
- [ ] Integration with cloud GPU providers
- [ ] Advanced scheduling algorithms