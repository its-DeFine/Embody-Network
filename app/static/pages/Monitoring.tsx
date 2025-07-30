import React, { useState } from 'react'
import { useQuery } from 'react-query'
import {
  Box,
  Typography,
  Paper,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from '@mui/material'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { systemAPI } from '../services/api'
import { format } from 'date-fns'

const TIME_RANGES = [
  { value: '1h', label: 'Last Hour' },
  { value: '6h', label: 'Last 6 Hours' },
  { value: '24h', label: 'Last 24 Hours' },
  { value: '7d', label: 'Last 7 Days' },
]

const SERVICES = [
  { value: 'all', label: 'All Services' },
  { value: 'core-engine', label: 'Core Engine' },
  { value: 'agent-manager', label: 'Agent Manager' },
  { value: 'api-gateway', label: 'API Gateway' },
  { value: 'orchestrator-adapter', label: 'GPU Orchestrator' },
]

// Mock data for demonstration
const generateMockMetrics = (points: number) => {
  const now = Date.now()
  const interval = 60000 // 1 minute
  
  return Array.from({ length: points }, (_, i) => ({
    timestamp: format(new Date(now - (points - i - 1) * interval), 'HH:mm'),
    cpu: Math.random() * 40 + 30,
    memory: Math.random() * 30 + 50,
    gpu: Math.random() * 50 + 25,
    requests: Math.floor(Math.random() * 100),
  }))
}

const Monitoring: React.FC = () => {
  const [timeRange, setTimeRange] = useState('1h')
  const [selectedService, setSelectedService] = useState('all')
  
  const { data: metrics } = useQuery(
    ['metrics', timeRange],
    async () => {
      // In production, this would fetch real metrics
      return generateMockMetrics(60)
    },
    { refetchInterval: 60000 }
  )

  const { data: events } = useQuery(
    'events',
    async () => {
      const response = await systemAPI.getEvents(50)
      return response.data
    },
    { refetchInterval: 30000 }
  )

  const getEventColor = (type: string) => {
    if (type.includes('error') || type.includes('failed')) return 'error'
    if (type.includes('warning') || type.includes('alert')) return 'warning'
    if (type.includes('success') || type.includes('completed')) return 'success'
    return 'default'
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Monitoring</Typography>
        
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Service</InputLabel>
            <Select
              value={selectedService}
              label="Service"
              onChange={(e) => setSelectedService(e.target.value)}
            >
              {SERVICES.map((service) => (
                <MenuItem key={service.value} value={service.value}>
                  {service.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              label="Time Range"
              onChange={(e) => setTimeRange(e.target.value)}
            >
              {TIME_RANGES.map((range) => (
                <MenuItem key={range.value} value={range.value}>
                  {range.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Resource Usage Chart */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Resource Usage
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={metrics}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="cpu"
                  stroke="#8884d8"
                  name="CPU %"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="memory"
                  stroke="#82ca9d"
                  name="Memory %"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="gpu"
                  stroke="#ffc658"
                  name="GPU %"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Request Rate Chart */}
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Request Rate
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={metrics}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="requests"
                  stroke="#00b4d8"
                  fill="#00b4d8"
                  fillOpacity={0.6}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* System Health Cards */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Uptime
              </Typography>
              <Typography variant="h4">99.9%</Typography>
              <Typography variant="body2" color="textSecondary">
                Last 30 days
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Response Time
              </Typography>
              <Typography variant="h4">45ms</Typography>
              <Typography variant="body2" color="textSecondary">
                Average
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Error Rate
              </Typography>
              <Typography variant="h4" color="error">
                0.1%
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Last hour
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Alerts
              </Typography>
              <Typography variant="h4" color="warning.main">
                2
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Non-critical
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Events */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Events
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Time</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Source</TableCell>
                    <TableCell>Message</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {events?.slice(0, 10).map((event: any, index: number) => (
                    <TableRow key={index}>
                      <TableCell>
                        {format(new Date(event.timestamp), 'HH:mm:ss')}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={event.type}
                          size="small"
                          color={getEventColor(event.type) as any}
                        />
                      </TableCell>
                      <TableCell>{event.source}</TableCell>
                      <TableCell>{event.message || JSON.stringify(event.data)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Monitoring