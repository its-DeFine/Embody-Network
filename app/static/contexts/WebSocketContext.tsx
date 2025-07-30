import React, { createContext, useContext, useEffect, useState } from 'react'
import { io, Socket } from 'socket.io-client'
import { toast } from 'react-toastify'
import { WebSocketMessage } from '../types'
import { useAuth } from './AuthContext'

interface WebSocketContextType {
  socket: Socket | null
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  subscribe: (event: string, callback: (data: any) => void) => void
  unsubscribe: (event: string, callback: (data: any) => void) => void
  emit: (event: string, data: any) => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, isAuthenticated } = useAuth()
  const [socket, setSocket] = useState<Socket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  useEffect(() => {
    if (isAuthenticated && token) {
      const newSocket = io('/', {
        auth: { token },
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      })

      newSocket.on('connect', () => {
        setIsConnected(true)
        toast.success('Connected to server')
      })

      newSocket.on('disconnect', () => {
        setIsConnected(false)
        toast.error('Disconnected from server')
      })

      newSocket.on('error', (error) => {
        console.error('WebSocket error:', error)
        toast.error('Connection error')
      })

      // Listen for system events
      newSocket.on('system.alert', (data) => {
        toast.warning(data.message)
      })

      newSocket.on('orchestrator.health_update', (data) => {
        setLastMessage({
          type: 'orchestrator.health_update',
          data,
          timestamp: new Date().toISOString(),
        })
      })

      newSocket.on('agent.status_update', (data) => {
        setLastMessage({
          type: 'agent.status_update',
          data,
          timestamp: new Date().toISOString(),
        })
      })

      setSocket(newSocket)

      return () => {
        newSocket.close()
      }
    }
  }, [isAuthenticated, token])

  const subscribe = (event: string, callback: (data: any) => void) => {
    if (socket) {
      socket.on(event, callback)
    }
  }

  const unsubscribe = (event: string, callback: (data: any) => void) => {
    if (socket) {
      socket.off(event, callback)
    }
  }

  const emit = (event: string, data: any) => {
    if (socket && isConnected) {
      socket.emit(event, data)
    }
  }

  return (
    <WebSocketContext.Provider
      value={{
        socket,
        isConnected,
        lastMessage,
        subscribe,
        unsubscribe,
        emit,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}