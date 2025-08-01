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
  Chip,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
} from '@mui/material'
import {
  Add as AddIcon,
  Send as SendIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Group as GroupIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { teamApi, agentApi } from '../services/api'
import toast from 'react-hot-toast'

export default function Teams() {
  const [openCreate, setOpenCreate] = useState(false)
  const [openCoordinate, setOpenCoordinate] = useState(false)
  const [selectedTeam, setSelectedTeam] = useState<any>(null)
  const [newTeam, setNewTeam] = useState({
    name: '',
    description: '',
    agent_ids: [] as string[],
  })
  const [task, setTask] = useState({
    objective: '',
    context: {},
  })
  
  const queryClient = useQueryClient()
  
  const { data: teams, isLoading, refetch } = useQuery({
    queryKey: ['teams'],
    queryFn: () => teamApi.list(),
  })

  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: teamApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      toast.success('Team created successfully')
      setOpenCreate(false)
      setNewTeam({ name: '', description: '', agent_ids: [] })
    },
    onError: () => {
      toast.error('Failed to create team')
    },
  })

  const coordinateMutation = useMutation({
    mutationFn: ({ id, task }: any) => teamApi.coordinate(id, task),
    onSuccess: () => {
      toast.success('Task sent to team')
      setOpenCoordinate(false)
      setTask({ objective: '', context: {} })
    },
    onError: () => {
      toast.error('Failed to coordinate team')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: teamApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      toast.success('Team deleted')
    },
    onError: () => {
      toast.error('Failed to delete team')
    },
  })

  const handleCreate = () => {
    createMutation.mutate(newTeam)
  }

  const handleCoordinate = () => {
    if (selectedTeam) {
      coordinateMutation.mutate({ id: selectedTeam.id, task })
    }
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Teams</Typography>
        <Box>
          <IconButton onClick={() => refetch()} title="Refresh">
            <RefreshIcon />
          </IconButton>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenCreate(true)}
          >
            New Team
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {teams?.data?.map((team: any) => (
          <Grid item xs={12} md={6} lg={4} key={team.id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                  <Typography variant="h6">{team.name}</Typography>
                  <GroupIcon color="primary" />
                </Box>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  {team.description || 'No description'}
                </Typography>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  Agents: {team.agent_ids?.length || 0}
                </Typography>
                {team.agent_ids?.length > 0 && (
                  <Box mt={1}>
                    {team.agent_ids.map((id: string) => (
                      <Chip 
                        key={id} 
                        label={id.slice(0, 8)} 
                        size="small" 
                        sx={{ mr: 0.5, mb: 0.5 }}
                      />
                    ))}
                  </Box>
                )}
              </CardContent>
              <CardActions>
                <IconButton 
                  color="primary" 
                  onClick={() => {
                    setSelectedTeam(team)
                    setOpenCoordinate(true)
                  }}
                  title="Coordinate Task"
                >
                  <SendIcon />
                </IconButton>
                <IconButton 
                  color="error" 
                  onClick={() => deleteMutation.mutate(team.id)}
                  title="Delete"
                >
                  <DeleteIcon />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {(!teams?.data || teams.data.length === 0) && !isLoading && (
        <Box textAlign="center" py={5}>
          <Typography variant="h6" color="textSecondary">
            No teams created yet
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenCreate(true)}
            sx={{ mt: 2 }}
          >
            Create Your First Team
          </Button>
        </Box>
      )}

      {/* Create Team Dialog */}
      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Team</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Team Name"
            fullWidth
            variant="outlined"
            value={newTeam.name}
            onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            variant="outlined"
            multiline
            rows={2}
            value={newTeam.description}
            onChange={(e) => setNewTeam({ ...newTeam, description: e.target.value })}
            sx={{ mb: 2 }}
          />
          <FormControl fullWidth>
            <InputLabel>Select Agents</InputLabel>
            <Select
              multiple
              value={newTeam.agent_ids}
              onChange={(e) => setNewTeam({ ...newTeam, agent_ids: e.target.value as string[] })}
              input={<OutlinedInput label="Select Agents" />}
            >
              {agents?.data?.map((agent: any) => (
                <MenuItem key={agent.id} value={agent.id}>
                  {agent.name} ({agent.type})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreate(false)}>Cancel</Button>
          <Button 
            onClick={handleCreate} 
            variant="contained" 
            disabled={!newTeam.name || newTeam.agent_ids.length === 0}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Coordinate Task Dialog */}
      <Dialog open={openCoordinate} onClose={() => setOpenCoordinate(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Coordinate Team Task</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary" gutterBottom>
            Team: {selectedTeam?.name}
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="Task Objective"
            fullWidth
            variant="outlined"
            multiline
            rows={4}
            value={task.objective}
            onChange={(e) => setTask({ ...task, objective: e.target.value })}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCoordinate(false)}>Cancel</Button>
          <Button 
            onClick={handleCoordinate} 
            variant="contained" 
            disabled={!task.objective}
          >
            Send Task
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}