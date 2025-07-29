export interface GPUOrchestrator {
  id: string
  hostname: string
  status: 'online' | 'offline' | 'busy'
  gpu: {
    name: string
    memory_total: number
    memory_used: number
    memory_free: number
    temperature: number
    utilization: number
    compute_capability: string
  }
  models_loaded: string[]
  agents_running: number
  last_health_check: string
  payment_stats?: {
    total_tickets: number
    winning_tickets: number
    total_value: string
    expected_value: string
  }
}

export interface Agent {
  id: string
  name: string
  type: string
  status: 'running' | 'stopped' | 'error' | 'deploying'
  orchestrator_id?: string
  gpu_enabled: boolean
  model?: string
  created_at: string
  last_heartbeat?: string
  config: Record<string, any>
  metadata?: {
    gpu_allocation?: {
      orchestrator_id: string
      model: string
      vram_allocated: number
    }
  }
}

export interface SystemMetrics {
  timestamp: string
  cpu_usage: number
  memory_usage: number
  gpu_usage?: number
  gpu_memory?: number
  network_io: {
    bytes_sent: number
    bytes_recv: number
  }
  disk_usage: number
}

export interface SwarmStatus {
  total_orchestrators: number
  online_orchestrators: number
  total_agents: number
  running_agents: number
  gpu_agents: number
  cpu_agents: number
  total_gpu_memory: number
  used_gpu_memory: number
  models_loaded: string[]
}

export interface AgentDeployRequest {
  name: string
  type: string
  requires_gpu: boolean
  model?: string
  config: Record<string, any>
}

export interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
}