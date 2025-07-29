import React, { useState, useEffect } from 'react'
import { useQuery } from 'react-query'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import {
  Memory as MemoryIcon,
  Thermostat as ThermostatIcon,
  Speed as SpeedIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material'
import { orchestratorAPI } from '../services/api'
import { GPUOrchestrator } from '../types'
import { useWebSocket } from '../contexts/WebSocketContext'
import { format } from 'date-fns'

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'online':
      return <CheckCircleIcon color="success" />
    case 'offline':
      return <ErrorIcon color="error" />
    case 'busy':
      return <WarningIcon color="warning" />
    default:
      return null
  }
}

const getTemperatureColor = (temp: number) => {
  if (temp < 60) return 'success'
  if (temp < 75) return 'warning'
  return 'error'
}

const GPUOrchestrators: React.FC = () => {
  const [selectedOrchestrator, setSelectedOrchestrator] = useState<GPUOrchestrator | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const { subscribe, unsubscribe } = useWebSocket()

  const { data: orchestrators, refetch } = useQuery<GPUOrchestrator[]>(
    'orchestrators',
    async () => {
      const response = await orchestratorAPI.getAll()
      return response.data
    },
    { refetchInterval: 30000 }
  )

  useEffect(() => {
    const handleHealthUpdate = (data: any) => {
      refetch()
    }

    subscribe('orchestrator.health_update', handleHealthUpdate)
    
    return () => {
      unsubscribe('orchestrator.health_update', handleHealthUpdate)
    }
  }, [subscribe, unsubscribe, refetch])

  const handleShowDetails = (orchestrator: GPUOrchestrator) => {
    setSelectedOrchestrator(orchestrator)
    setDetailsOpen(true)
  }

  const handleCloseDetails = () => {
    setDetailsOpen(false)
    setSelectedOrchestrator(null)
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">GPU Orchestrators</Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => refetch()}
        >
          Refresh
        </Button>
      </Box>

      <Grid container spacing={3}>
        {orchestrators?.map((orchestrator) => (
          <Grid item xs={12} md={6} lg={4} key={orchestrator.id}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getStatusIcon(orchestrator.status)}
                    <Typography variant="h6">{orchestrator.hostname}</Typography>
                  </Box>
                  <IconButton size="small" onClick={() => handleShowDetails(orchestrator)}>
                    <InfoIcon />
                  </IconButton>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="textSecondary" gutterBottom>
                    GPU: {orchestrator.gpu.name}
                  </Typography>
                  <Chip
                    label={`Compute ${orchestrator.gpu.compute_capability}`}
                    size="small"
                    variant="outlined"
                  />
                </Box>

                {/* GPU Memory */}
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <MemoryIcon fontSize="small" />
                      <Typography variant="body2">Memory</Typography>
                    </Box>
                    <Typography variant="body2">
                      {Math.round(orchestrator.gpu.memory_used / 1024)}GB / {Math.round(orchestrator.gpu.memory_total / 1024)}GB
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(orchestrator.gpu.memory_used / orchestrator.gpu.memory_total) * 100}
                    sx={{ height: 6, borderRadius: 3 }}
                  />
                </Box>

                {/* GPU Utilization */}
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <SpeedIcon fontSize="small" />
                      <Typography variant="body2">Utilization</Typography>
                    </Box>
                    <Typography variant="body2">{orchestrator.gpu.utilization}%</Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={orchestrator.gpu.utilization}
                    color="secondary"
                    sx={{ height: 6, borderRadius: 3 }}
                  />
                </Box>

                {/* Temperature */}
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <ThermostatIcon fontSize="small" />
                    <Typography variant="body2">Temperature</Typography>
                    <Chip
                      label={`${orchestrator.gpu.temperature}°C`}
                      size="small"
                      color={getTemperatureColor(orchestrator.gpu.temperature) as any}
                      sx={{ ml: 'auto' }}
                    />
                  </Box>
                </Box>

                {/* Agents and Models */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="textSecondary">
                    {orchestrator.agents_running} agents running
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {orchestrator.models_loaded.length} models loaded
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Orchestrator Details Dialog */}
      <Dialog open={detailsOpen} onClose={handleCloseDetails} maxWidth="md" fullWidth>
        <DialogTitle>
          Orchestrator Details: {selectedOrchestrator?.hostname}
        </DialogTitle>
        <DialogContent>
          {selectedOrchestrator && (
            <Box sx={{ mt: 2 }}>
              {/* GPU Information */}
              <Typography variant="h6" gutterBottom>GPU Information</Typography>
              <TableContainer component={Paper} sx={{ mb: 3 }}>
                <Table>
                  <TableBody>
                    <TableRow>
                      <TableCell>Model</TableCell>
                      <TableCell>{selectedOrchestrator.gpu.name}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Compute Capability</TableCell>
                      <TableCell>{selectedOrchestrator.gpu.compute_capability}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Total Memory</TableCell>
                      <TableCell>{Math.round(selectedOrchestrator.gpu.memory_total / 1024)}GB</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Free Memory</TableCell>
                      <TableCell>{Math.round(selectedOrchestrator.gpu.memory_free / 1024)}GB</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Temperature</TableCell>
                      <TableCell>{selectedOrchestrator.gpu.temperature}°C</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Utilization</TableCell>
                      <TableCell>{selectedOrchestrator.gpu.utilization}%</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>

              {/* Loaded Models */}
              <Typography variant="h6" gutterBottom>Loaded Models</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 3 }}>
                {selectedOrchestrator.models_loaded.map((model) => (
                  <Chip key={model} label={model} color="primary" />
                ))}
              </Box>

              {/* Payment Statistics */}
              {selectedOrchestrator.payment_stats && (
                <>
                  <Typography variant="h6" gutterBottom>Payment Statistics</Typography>
                  <TableContainer component={Paper}>
                    <Table>
                      <TableBody>
                        <TableRow>
                          <TableCell>Total Tickets</TableCell>
                          <TableCell>{selectedOrchestrator.payment_stats.total_tickets}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Winning Tickets</TableCell>
                          <TableCell>{selectedOrchestrator.payment_stats.winning_tickets}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Total Value</TableCell>
                          <TableCell>{selectedOrchestrator.payment_stats.total_value}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Expected Value</TableCell>
                          <TableCell>{selectedOrchestrator.payment_stats.expected_value}</TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </TableContainer>
                </>
              )}

              <Typography variant="body2" color="textSecondary" sx={{ mt: 3 }}>
                Last health check: {format(new Date(selectedOrchestrator.last_health_check), 'PPpp')}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDetails}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default GPUOrchestrators