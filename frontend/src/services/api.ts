import axios from 'axios'

export const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const agentApi = {
  list: () => api.get('/api/v1/agents'),
  create: (data: any) => api.post('/api/v1/agents', data),
  get: (id: string) => api.get(`/api/v1/agents/${id}`),
  start: (id: string) => api.post(`/api/v1/agents/${id}/start`),
  stop: (id: string) => api.post(`/api/v1/agents/${id}/stop`),
  delete: (id: string) => api.delete(`/api/v1/agents/${id}`),
}

export const teamApi = {
  list: () => api.get('/api/v1/teams'),
  create: (data: any) => api.post('/api/v1/teams', data),
  get: (id: string) => api.get(`/api/v1/teams/${id}`),
  coordinate: (id: string, task: any) => api.post(`/api/v1/teams/${id}/coordinate`, task),
  delete: (id: string) => api.delete(`/api/v1/teams/${id}`),
}

export const taskApi = {
  list: () => api.get('/api/v1/tasks'),
  create: (data: any) => api.post('/api/v1/tasks', data),
  get: (id: string) => api.get(`/api/v1/tasks/${id}`),
  cancel: (id: string) => api.post(`/api/v1/tasks/${id}/cancel`),
}