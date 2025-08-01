import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../services/api'
import toast from 'react-hot-toast'

interface AuthContextType {
  isAuthenticated: boolean
  token: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [isAuthenticated, setIsAuthenticated] = useState(!!token)

  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    }
  }, [token])

  const login = async (username: string, password: string) => {
    try {
      const response = await api.post('/api/v1/auth/login', { email: username, password })
      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      setToken(access_token)
      setIsAuthenticated(true)
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      toast.success('Login successful!')
    } catch (error) {
      toast.error('Login failed. Please check your credentials.')
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setIsAuthenticated(false)
    delete api.defaults.headers.common['Authorization']
    toast.success('Logged out successfully')
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}