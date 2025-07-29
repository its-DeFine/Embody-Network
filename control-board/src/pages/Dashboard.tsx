import React, { useEffect } from 'react'
import { useQuery } from 'react-query'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Paper,
  Chip,
} from '@mui/material'
import {
  Memory as MemoryIcon,
  SmartToy as SmartToyIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  TrendingUp as TrendingUpIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material'
import { systemAPI, orchestratorAPI } from '../services/api'
import { SwarmStatus } from '../types'
import { useWebSocket } from '../contexts/WebSocketContext'
import { format } from 'date-fns'

interface StatCardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  color: string
  subtitle?: string
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, subtitle }) => (
  <Card>
    <CardContent>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography color="textSecondary" gutterBottom variant="body2">
            {title}
          </Typography>
          <Typography variant="h4" component="div" sx={{ mb: 1 }}>
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="body2" color="textSecondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            backgroundColor: `${color}.light`,
            borderRadius: 2,
            p: 1.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {React.cloneElement(icon as React.ReactElement, {
            sx: { color: `${color}.main`, fontSize: 30 },
          })}
        </Box>
      </Box>
    </CardContent>
  </Card>
)

const Dashboard: React.FC = () => {
  const { lastMessage, subscribe, unsubscribe } = useWebSocket()
  
  const { data: swarmStatus, refetch: refetchSwarm } = useQuery<SwarmStatus>(
    'swarmStatus',
    async () => {
      const response = await systemAPI.getSwarmStatus()
      return response.data
    },
    { refetchInterval: 10000 }
  )

  const { data: metrics } = useQuery(
    'systemMetrics',
    async () => {
      const response = await systemAPI.getMetrics()
      return response.data
    },
    { refetchInterval: 5000 }
  )

  const { data: paymentStats } = useQuery(
    'paymentStats',
    async () => {
      const response = await orchestratorAPI.getPaymentStats()
      return response.data
    },
    { refetchInterval: 30000 }
  )

  useEffect(() => {
    const handleHealthUpdate = () => {
      refetchSwarm()
    }

    subscribe('orchestrator.health_update', handleHealthUpdate)
    subscribe('agent.status_update', handleHealthUpdate)

    return () => {
      unsubscribe('orchestrator.health_update', handleHealthUpdate)
      unsubscribe('agent.status_update', handleHealthUpdate)
    }
  }, [subscribe, unsubscribe, refetchSwarm])

  const gpuUtilization = swarmStatus
    ? Math.round((swarmStatus.used_gpu_memory / swarmStatus.total_gpu_memory) * 100)
    : 0

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* GPU Orchestrators */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="GPU Orchestrators"
            value={swarmStatus?.online_orchestrators || 0}
            subtitle={`of ${swarmStatus?.total_orchestrators || 0} total`}
            icon={<MemoryIcon />}
            color="primary"
          />
        </Grid>

        {/* Running Agents */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Running Agents"
            value={swarmStatus?.running_agents || 0}
            subtitle={`${swarmStatus?.gpu_agents || 0} GPU, ${swarmStatus?.cpu_agents || 0} CPU`}
            icon={<SmartToyIcon />}
            color="success"
          />
        </Grid>

        {/* GPU Memory Usage */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="GPU Memory Usage"
            value={`${gpuUtilization}%`}
            subtitle={`${Math.round((swarmStatus?.used_gpu_memory || 0) / 1024)}GB used`}
            icon={<StorageIcon />}
            color="warning"
          />
        </Grid>

        {/* Payment Stats */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Payments Today"
            value={paymentStats?.total_tickets || 0}
            subtitle={`${paymentStats?.winning_tickets || 0} winning tickets`}
            icon={<TrendingUpIcon />}
            color="secondary"
          />
        </Grid>

        {/* GPU Utilization Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              System Resources
            </Typography>
            
            <Box sx={{ mt: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">CPU Usage</Typography>
                <Typography variant="body2">{metrics?.cpu_usage || 0}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={metrics?.cpu_usage || 0}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>

            <Box sx={{ mt: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Memory Usage</Typography>
                <Typography variant="body2">{metrics?.memory_usage || 0}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={metrics?.memory_usage || 0}
                sx={{ height: 8, borderRadius: 4 }}
                color="secondary"
              />
            </Box>

            <Box sx={{ mt: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">GPU Memory</Typography>
                <Typography variant="body2">{gpuUtilization}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={gpuUtilization}
                sx={{ height: 8, borderRadius: 4 }}
                color="warning"
              />
            </Box>

            <Box sx={{ mt: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Disk Usage</Typography>
                <Typography variant="body2">{metrics?.disk_usage || 0}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={metrics?.disk_usage || 0}
                sx={{ height: 8, borderRadius: 4 }}
                color="error"
              />
            </Box>
          </Paper>
        </Grid>

        {/* Recent Events */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Recent Events
            </Typography>
            
            <Box sx={{ mt: 2 }}>
              {lastMessage && (
                <Box sx={{ mb: 2 }}>
                  <Chip
                    icon={
                      lastMessage.type.includes('error') ? (
                        <ErrorIcon />
                      ) : (
                        <CheckCircleIcon />
                      )
                    }
                    label={lastMessage.type}
                    color={lastMessage.type.includes('error') ? 'error' : 'success'}
                    size="small"
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="body2" color="textSecondary">
                    {format(new Date(lastMessage.timestamp), 'HH:mm:ss')}
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        {/* Models Loaded */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Loaded Models
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
              {swarmStatus?.models_loaded?.map((model) => (
                <Chip
                  key={model}
                  label={model}
                  color="primary"
                  variant="outlined"
                />
              ))}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Dashboard