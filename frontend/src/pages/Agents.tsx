import { useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
  Grid,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
} from '@mui/material'
import {
  Add as AddIcon,
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentApi } from '../services/api'
import toast from 'react-hot-toast'

const agentTypes = ['trading', 'analysis', 'risk', 'portfolio']

export default function Agents() {
  const [open, setOpen] = useState(false)
  const [newAgent, setNewAgent] = useState({
    name: '',
    agent_type: 'trading',
    config: {},
  })
  
  const queryClient = useQueryClient()
  
  const { data: agents, isLoading, refetch } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: agentApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast.success('Agent created successfully')
      setOpen(false)
      setNewAgent({ name: '', agent_type: 'trading', config: {} })
    },
    onError: () => {
      toast.error('Failed to create agent')
    },
  })

  const startMutation = useMutation({
    mutationFn: agentApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast.success('Agent started')
    },
    onError: () => {
      toast.error('Failed to start agent')
    },
  })

  const stopMutation = useMutation({
    mutationFn: agentApi.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast.success('Agent stopped')
    },
    onError: () => {
      toast.error('Failed to stop agent')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: agentApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast.success('Agent deleted')
    },
    onError: () => {
      toast.error('Failed to delete agent')
    },
  })

  const handleCreate = () => {
    createMutation.mutate(newAgent)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'success'
      case 'stopped': return 'default'
      case 'error': return 'error'
      default: return 'default'
    }
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Agents</Typography>
        <Box>
          <IconButton onClick={() => refetch()} title="Refresh">
            <RefreshIcon />
          </IconButton>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpen(true)}
          >
            New Agent
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {agents?.data?.map((agent: any) => (
          <Grid item xs={12} md={6} lg={4} key={agent.id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                  <Typography variant="h6">{agent.name}</Typography>
                  <Chip 
                    label={agent.status} 
                    color={getStatusColor(agent.status)} 
                    size="small"
                  />
                </Box>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  Type: {agent.type}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Created: {new Date(agent.created_at).toLocaleString()}
                </Typography>
              </CardContent>
              <CardActions>
                {agent.status === 'stopped' ? (
                  <IconButton 
                    color="primary" 
                    onClick={() => startMutation.mutate(agent.id)}
                    title="Start"
                  >
                    <StartIcon />
                  </IconButton>
                ) : (
                  <IconButton 
                    color="warning" 
                    onClick={() => stopMutation.mutate(agent.id)}
                    title="Stop"
                  >
                    <StopIcon />
                  </IconButton>
                )}
                <IconButton 
                  color="error" 
                  onClick={() => deleteMutation.mutate(agent.id)}
                  title="Delete"
                >
                  <DeleteIcon />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {(!agents?.data || agents.data.length === 0) && !isLoading && (
        <Box textAlign="center" py={5}>
          <Typography variant="h6" color="textSecondary">
            No agents created yet
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpen(true)}
            sx={{ mt: 2 }}
          >
            Create Your First Agent
          </Button>
        </Box>
      )}

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Agent</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Agent Name"
            fullWidth
            variant="outlined"
            value={newAgent.name}
            onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          <FormControl fullWidth>
            <InputLabel>Agent Type</InputLabel>
            <Select
              value={newAgent.agent_type}
              label="Agent Type"
              onChange={(e) => setNewAgent({ ...newAgent, agent_type: e.target.value })}
            >
              {agentTypes.map((type) => (
                <MenuItem key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained" disabled={!newAgent.name}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}