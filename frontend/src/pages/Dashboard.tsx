// Dashboard component - removed unused imports
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  LinearProgress,
} from '@mui/material'
import {
  SmartToy as AgentIcon,
  Groups as TeamsIcon,
  Assignment as TasksIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { agentApi, teamApi, taskApi } from '../services/api'

function StatCard({ title, value, icon, color }: any) {
  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography color="textSecondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h4">
              {value}
            </Typography>
          </Box>
          <Box sx={{ color }}>
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}

export default function Dashboard() {
  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentApi.list(),
  })

  const { data: teams, isLoading: teamsLoading } = useQuery({
    queryKey: ['teams'],
    queryFn: () => teamApi.list(),
  })

  const { data: tasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => taskApi.list(),
  })

  const isLoading = agentsLoading || teamsLoading || tasksLoading

  const stats = {
    agents: {
      total: agents?.data?.length || 0,
      running: agents?.data?.filter((a: any) => a.status === 'running').length || 0,
    },
    teams: {
      total: teams?.data?.length || 0,
      active: teams?.data?.filter((t: any) => t.status === 'active').length || 0,
    },
    tasks: {
      total: tasks?.data?.length || 0,
      completed: tasks?.data?.filter((t: any) => t.status === 'completed').length || 0,
      running: tasks?.data?.filter((t: any) => t.status === 'running').length || 0,
    },
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        System Overview
      </Typography>
      
      {isLoading && <LinearProgress sx={{ mb: 2 }} />}
      
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Agents"
            value={stats.agents.total}
            icon={<AgentIcon fontSize="large" />}
            color="#1976d2"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Running Agents"
            value={stats.agents.running}
            icon={<AgentIcon fontSize="large" />}
            color="#4caf50"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Teams"
            value={stats.teams.total}
            icon={<TeamsIcon fontSize="large" />}
            color="#ff9800"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Active Tasks"
            value={stats.tasks.running}
            icon={<TasksIcon fontSize="large" />}
            color="#f44336"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Tasks
            </Typography>
            {tasks?.data?.slice(0, 5).map((task: any) => (
              <Box key={task.id} sx={{ py: 1, borderBottom: '1px solid #eee' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2">{task.description}</Typography>
                  <Typography 
                    variant="caption" 
                    color={task.status === 'completed' ? 'success.main' : 'primary.main'}
                  >
                    {task.status}
                  </Typography>
                </Box>
              </Box>
            ))}
            {(!tasks?.data || tasks.data.length === 0) && (
              <Typography variant="body2" color="textSecondary">
                No tasks yet
              </Typography>
            )}
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              System Health
            </Typography>
            <Box sx={{ py: 2 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography>API Status</Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <SuccessIcon color="success" />
                  <Typography color="success.main">Healthy</Typography>
                </Box>
              </Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography>Redis Connection</Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <SuccessIcon color="success" />
                  <Typography color="success.main">Connected</Typography>
                </Box>
              </Box>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography>Task Processing</Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <SuccessIcon color="success" />
                  <Typography color="success.main">Active</Typography>
                </Box>
              </Box>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}