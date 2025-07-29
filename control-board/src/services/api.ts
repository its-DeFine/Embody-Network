import axios from 'axios'
import { toast } from 'react-toastify'

export const api = axios.create({
  baseURL: '/',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          localStorage.removeItem('token')
          window.location.href = '/login'
          toast.error('Session expired. Please login again.')
          break
        case 403:
          toast.error('You do not have permission to perform this action.')
          break
        case 404:
          toast.error('Resource not found.')
          break
        case 500:
          toast.error('Server error. Please try again later.')
          break
        default:
          toast.error(error.response.data.message || 'An error occurred.')
      }
    } else if (error.request) {
      toast.error('Network error. Please check your connection.')
    } else {
      toast.error('An unexpected error occurred.')
    }
    return Promise.reject(error)
  }
)

// API methods
export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/api/v1/auth/login', { username, password }),
  
  getMe: () => api.get('/api/v1/auth/me'),
}

export const orchestratorAPI = {
  getAll: () => api.get('/gpu/orchestrators'),
  
  getStatus: () => api.get('/gpu/status'),
  
  getHealth: (id: string) => api.get(`/gpu/orchestrators/${id}/health`),
  
  allocateAgent: (agentId: string, orchestratorId: string) =>
    api.post('/gpu/agents/allocate', { agent_id: agentId, orchestrator_id: orchestratorId }),
  
  deallocateAgent: (agentId: string) =>
    api.delete(`/gpu/agents/${agentId}`),
  
  getPaymentStats: () => api.get('/gpu/payments/stats'),
}

export const agentAPI = {
  getAll: () => api.get('/api/v1/agents'),
  
  create: (data: any) => api.post('/api/v1/agents', data),
  
  get: (id: string) => api.get(`/api/v1/agents/${id}`),
  
  update: (id: string, data: any) => api.put(`/api/v1/agents/${id}`, data),
  
  delete: (id: string) => api.delete(`/api/v1/agents/${id}`),
  
  start: (id: string) => api.post(`/api/v1/agents/${id}/start`),
  
  stop: (id: string) => api.post(`/api/v1/agents/${id}/stop`),
  
  killSwitch: (id: string) => api.post(`/api/v1/agents/${id}/kill`),
}

export const systemAPI = {
  getMetrics: () => api.get('/api/v1/system/metrics'),
  
  getSwarmStatus: () => api.get('/api/v1/system/swarm/status'),
  
  getEvents: (limit = 100) => api.get(`/api/v1/system/events?limit=${limit}`),
  
  getLogs: (service: string, lines = 100) =>
    api.get(`/api/v1/system/logs/${service}?lines=${lines}`),
}