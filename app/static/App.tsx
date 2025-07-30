import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Box } from '@mui/material'

import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import GPUOrchestrators from './pages/GPUOrchestrators'
import Agents from './pages/Agents'
import Monitoring from './pages/Monitoring'
import Settings from './pages/Settings'
import Login from './pages/Login'
import { useAuth } from './contexts/AuthContext'

const App: React.FC = () => {
  const { isAuthenticated } = useAuth()

  if (!isAuthenticated) {
    return <Login />
  }

  return (
    <Layout>
      <Box sx={{ p: 3 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/gpu-orchestrators" element={<GPUOrchestrators />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Box>
    </Layout>
  )
}

export default App