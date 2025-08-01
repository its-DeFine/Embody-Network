import { useState } from 'react'
import {
  Box,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  Cancel as CancelIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { taskApi } from '../services/api'
import toast from 'react-hot-toast'
import { format } from 'date-fns'

export default function Tasks() {
  const [selectedTask, setSelectedTask] = useState<any>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  
  const queryClient = useQueryClient()
  
  const { data: tasks, isLoading, refetch } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => taskApi.list(),
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  })

  const cancelMutation = useMutation({
    mutationFn: taskApi.cancel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      toast.success('Task cancelled')
    },
    onError: () => {
      toast.error('Failed to cancel task')
    },
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success'
      case 'running': return 'primary'
      case 'failed': return 'error'
      case 'cancelled': return 'default'
      case 'pending': return 'warning'
      default: return 'default'
    }
  }

  const handleViewDetails = async (task: any) => {
    try {
      const response = await taskApi.get(task.id)
      setSelectedTask(response.data)
      setDetailsOpen(true)
    } catch (error) {
      toast.error('Failed to load task details')
    }
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Tasks</Typography>
        <IconButton onClick={() => refetch()} title="Refresh">
          <RefreshIcon />
        </IconButton>
      </Box>

      {isLoading && <LinearProgress sx={{ mb: 2 }} />}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Task ID</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tasks?.data?.map((task: any) => (
              <TableRow key={task.id}>
                <TableCell>{task.id.slice(0, 8)}</TableCell>
                <TableCell>{task.type}</TableCell>
                <TableCell>{task.description}</TableCell>
                <TableCell>
                  <Chip 
                    label={task.status} 
                    color={getStatusColor(task.status)} 
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {format(new Date(task.created_at), 'MMM dd, HH:mm')}
                </TableCell>
                <TableCell>
                  <IconButton 
                    size="small" 
                    onClick={() => handleViewDetails(task)}
                    title="View Details"
                  >
                    <InfoIcon />
                  </IconButton>
                  {(task.status === 'running' || task.status === 'pending') && (
                    <IconButton 
                      size="small" 
                      color="error"
                      onClick={() => cancelMutation.mutate(task.id)}
                      title="Cancel Task"
                    >
                      <CancelIcon />
                    </IconButton>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {(!tasks?.data || tasks.data.length === 0) && !isLoading && (
        <Box textAlign="center" py={5}>
          <Typography variant="h6" color="textSecondary">
            No tasks yet
          </Typography>
          <Typography variant="body2" color="textSecondary" mt={1}>
            Tasks will appear here when agents start processing
          </Typography>
        </Box>
      )}

      {/* Task Details Dialog */}
      <Dialog open={detailsOpen} onClose={() => setDetailsOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Task Details</DialogTitle>
        <DialogContent>
          {selectedTask && (
            <Box>
              <Typography variant="body2" gutterBottom>
                <strong>ID:</strong> {selectedTask.id}
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Type:</strong> {selectedTask.type}
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Status:</strong> <Chip 
                  label={selectedTask.status} 
                  color={getStatusColor(selectedTask.status)} 
                  size="small"
                />
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Description:</strong> {selectedTask.description}
              </Typography>
              <Typography variant="body2" gutterBottom>
                <strong>Created:</strong> {format(new Date(selectedTask.created_at), 'PPpp')}
              </Typography>
              {selectedTask.completed_at && (
                <Typography variant="body2" gutterBottom>
                  <strong>Completed:</strong> {format(new Date(selectedTask.completed_at), 'PPpp')}
                </Typography>
              )}
              {selectedTask.result && (
                <>
                  <Typography variant="body2" gutterBottom mt={2}>
                    <strong>Result:</strong>
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(selectedTask.result, null, 2)}
                    </pre>
                  </Paper>
                </>
              )}
              {selectedTask.error && (
                <>
                  <Typography variant="body2" gutterBottom mt={2} color="error">
                    <strong>Error:</strong>
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, bgcolor: 'error.50' }}>
                    <Typography variant="body2" color="error">
                      {selectedTask.error}
                    </Typography>
                  </Paper>
                </>
              )}
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