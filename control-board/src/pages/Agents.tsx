import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  Alert,
} from '@mui/material'
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Delete as DeleteIcon,
  PowerOff as PowerOffIcon,
  Memory as MemoryIcon,
  SmartToy as SmartToyIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { agentAPI } from '../services/api'
import { Agent, AgentDeployRequest } from '../types'
import { useWebSocket } from '../contexts/WebSocketContext'
import { toast } from 'react-toastify'
import { format } from 'date-fns'

const AGENT_TYPES = [
  { value: 'trading', label: 'Trading Agent' },
  { value: 'analysis', label: 'Analysis Agent' },
  { value: 'arbitrage', label: 'Arbitrage Agent' },
  { value: 'market_maker', label: 'Market Maker' },
  { value: 'risk_manager', label: 'Risk Manager' },
]

const GPU_MODELS = [
  { value: 'codellama:34b-instruct-q4_k_m', label: 'CodeLlama 34B (20GB)', vram: 20000 },
  { value: 'codellama:13b', label: 'CodeLlama 13B (8GB)', vram: 8000 },
  { value: 'llama2:13b', label: 'Llama 2 13B (8GB)', vram: 8000 },
  { value: 'mistral:7b-instruct', label: 'Mistral 7B (4GB)', vram: 4000 },
  { value: 'mixtral:8x7b', label: 'Mixtral 8x7B (25GB)', vram: 25000 },
]

const getStatusColor = (status: string) => {
  switch (status) {
    case 'running':
      return 'success'
    case 'stopped':
      return 'default'
    case 'error':
      return 'error'
    case 'deploying':
      return 'warning'
    default:
      return 'default'
  }
}

const Agents: React.FC = () => {
  const queryClient = useQueryClient()
  const { subscribe, unsubscribe } = useWebSocket()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  
  // Form state
  const [formData, setFormData] = useState<AgentDeployRequest>({
    name: '',
    type: 'trading',
    requires_gpu: false,
    model: '',
    config: {},
  })

  const { data: agents, refetch } = useQuery<Agent[]>(
    'agents',
    async () => {
      const response = await agentAPI.getAll()
      return response.data
    },
    { refetchInterval: 10000 }
  )

  const createMutation = useMutation(
    (data: AgentDeployRequest) => agentAPI.create(data),
    {
      onSuccess: () => {
        toast.success('Agent created successfully')
        queryClient.invalidateQueries('agents')
        setCreateDialogOpen(false)
        resetForm()
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.message || 'Failed to create agent')
      },
    }
  )

  const startMutation = useMutation(
    (id: string) => agentAPI.start(id),
    {
      onSuccess: () => {
        toast.success('Agent started')
        queryClient.invalidateQueries('agents')
      },
    }
  )

  const stopMutation = useMutation(
    (id: string) => agentAPI.stop(id),
    {
      onSuccess: () => {
        toast.success('Agent stopped')
        queryClient.invalidateQueries('agents')
      },
    }
  )

  const killMutation = useMutation(
    (id: string) => agentAPI.killSwitch(id),
    {
      onSuccess: () => {
        toast.success('Kill switch activated')
        queryClient.invalidateQueries('agents')
      },
    }
  )

  const deleteMutation = useMutation(
    (id: string) => agentAPI.delete(id),
    {
      onSuccess: () => {
        toast.success('Agent deleted')
        queryClient.invalidateQueries('agents')
      },
    }
  )

  useEffect(() => {
    const handleAgentUpdate = () => {
      refetch()
    }

    subscribe('agent.status_update', handleAgentUpdate)
    
    return () => {
      unsubscribe('agent.status_update', handleAgentUpdate)
    }
  }, [subscribe, unsubscribe, refetch])

  const resetForm = () => {
    setFormData({
      name: '',
      type: 'trading',
      requires_gpu: false,
      model: '',
      config: {},
    })
  }

  const handleCreateAgent = () => {
    createMutation.mutate(formData)
  }

  const handleShowDetails = (agent: Agent) => {
    setSelectedAgent(agent)
    setDetailsOpen(true)
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Agents</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Deploy Agent
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Runtime</TableCell>
              <TableCell>Model</TableCell>
              <TableCell>Orchestrator</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {agents?.map((agent) => (
              <TableRow key={agent.id}>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {agent.gpu_enabled ? <MemoryIcon color="primary" /> : <SmartToyIcon />}
                    <Typography>{agent.name}</Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip label={agent.type} size="small" />
                </TableCell>
                <TableCell>
                  <Chip
                    label={agent.status}
                    size="small"
                    color={getStatusColor(agent.status) as any}
                  />
                </TableCell>
                <TableCell>
                  {agent.gpu_enabled ? 'GPU' : 'CPU'}
                </TableCell>
                <TableCell>
                  {agent.model || '-'}
                </TableCell>
                <TableCell>
                  {agent.orchestrator_id || '-'}
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="Details">
                    <IconButton size="small" onClick={() => handleShowDetails(agent)}>
                      <InfoIcon />
                    </IconButton>
                  </Tooltip>
                  
                  {agent.status === 'stopped' && (
                    <Tooltip title="Start">
                      <IconButton
                        size="small"
                        color="success"
                        onClick={() => startMutation.mutate(agent.id)}
                      >
                        <PlayIcon />
                      </IconButton>
                    </Tooltip>
                  )}
                  
                  {agent.status === 'running' && (
                    <Tooltip title="Stop">
                      <IconButton
                        size="small"
                        color="warning"
                        onClick={() => stopMutation.mutate(agent.id)}
                      >
                        <StopIcon />
                      </IconButton>
                    </Tooltip>
                  )}
                  
                  <Tooltip title="Kill Switch">
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => {
                        if (window.confirm('Activate kill switch for this agent?')) {
                          killMutation.mutate(agent.id)
                        }
                      }}
                    >
                      <PowerOffIcon />
                    </IconButton>
                  </Tooltip>
                  
                  <Tooltip title="Delete">
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => {
                        if (window.confirm('Delete this agent?')) {
                          deleteMutation.mutate(agent.id)
                        }
                      }}
                      disabled={agent.status === 'running'}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Create Agent Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Deploy New Agent</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Agent Name"
              fullWidth
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
            
            <FormControl fullWidth>
              <InputLabel>Agent Type</InputLabel>
              <Select
                value={formData.type}
                label="Agent Type"
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              >
                {AGENT_TYPES.map((type) => (
                  <MenuItem key={type.value} value={type.value}>
                    {type.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControlLabel
              control={
                <Switch
                  checked={formData.requires_gpu}
                  onChange={(e) => setFormData({ ...formData, requires_gpu: e.target.checked })}
                />
              }
              label="Requires GPU"
            />
            
            {formData.requires_gpu && (
              <FormControl fullWidth>
                <InputLabel>Model</InputLabel>
                <Select
                  value={formData.model}
                  label="Model"
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                >
                  {GPU_MODELS.map((model) => (
                    <MenuItem key={model.value} value={model.value}>
                      {model.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            
            <Alert severity="info">
              {formData.requires_gpu
                ? 'Agent will be deployed to a GPU orchestrator with Ollama support.'
                : 'Agent will be deployed to CPU using standard AutoGen configuration.'}
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateAgent}
            variant="contained"
            disabled={!formData.name || createMutation.isLoading}
          >
            Deploy
          </Button>
        </DialogActions>
      </Dialog>

      {/* Agent Details Dialog */}
      <Dialog open={detailsOpen} onClose={() => setDetailsOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Agent Details: {selectedAgent?.name}</DialogTitle>
        <DialogContent>
          {selectedAgent && (
            <Box sx={{ mt: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">ID</Typography>
                  <Typography>{selectedAgent.id}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">Type</Typography>
                  <Typography>{selectedAgent.type}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">Status</Typography>
                  <Chip
                    label={selectedAgent.status}
                    color={getStatusColor(selectedAgent.status) as any}
                  />
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">Runtime</Typography>
                  <Typography>{selectedAgent.gpu_enabled ? 'GPU' : 'CPU'}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">Created</Typography>
                  <Typography>{format(new Date(selectedAgent.created_at), 'PPpp')}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">Last Heartbeat</Typography>
                  <Typography>
                    {selectedAgent.last_heartbeat
                      ? format(new Date(selectedAgent.last_heartbeat), 'PPpp')
                      : '-'}
                  </Typography>
                </Grid>
              </Grid>
              
              {selectedAgent.metadata?.gpu_allocation && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" gutterBottom>GPU Allocation</Typography>
                  <Paper sx={{ p: 2 }}>
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography variant="body2" color="textSecondary">Orchestrator</Typography>
                        <Typography>{selectedAgent.metadata.gpu_allocation.orchestrator_id}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2" color="textSecondary">Model</Typography>
                        <Typography>{selectedAgent.metadata.gpu_allocation.model}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2" color="textSecondary">VRAM Allocated</Typography>
                        <Typography>
                          {Math.round(selectedAgent.metadata.gpu_allocation.vram_allocated / 1024)}GB
                        </Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                </Box>
              )}
              
              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>Configuration</Typography>
                <Paper sx={{ p: 2 }}>
                  <pre style={{ margin: 0, overflow: 'auto' }}>
                    {JSON.stringify(selectedAgent.config, null, 2)}
                  </pre>
                </Paper>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Agents