import React, { useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Switch,
  FormControlLabel,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
} from '@mui/material'
import {
  Save as SaveIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material'
import { toast } from 'react-toastify'

const Settings: React.FC = () => {
  const [settings, setSettings] = useState({
    gpu: {
      allocationStrategy: 'least_loaded',
      maxAgentsPerGPU: 5,
      maxVRAMUtilization: 90,
      enableGPUDeployment: true,
      memoryReserveMB: 2048,
    },
    system: {
      enableMonitoring: true,
      metricsInterval: 30,
      logLevel: 'info',
      maxLogSize: 100,
      enableWebSockets: true,
    },
    trading: {
      enableDualMode: true,
      defaultMode: 'comparison',
      maxOrderSize: 10000,
      enableRiskLimits: true,
      stopLossPercentage: 5,
    },
    orchestrators: [] as Array<{url: string; secret: string}>,
    apiKeys: [] as Array<{exchange: string; key: string; secret: string}>,
  })

  const [newOrchestrator, setNewOrchestrator] = useState({
    url: '',
    secret: '',
  })

  // const [newApiKey, setNewApiKey] = useState({
  //   exchange: '',
  //   key: '',
  //   secret: '',
  // })

  const handleSaveSettings = () => {
    // In production, this would save to backend
    toast.success('Settings saved successfully')
  }

  const handleAddOrchestrator = () => {
    if (newOrchestrator.url && newOrchestrator.secret) {
      setSettings({
        ...settings,
        orchestrators: [...settings.orchestrators, newOrchestrator],
      })
      setNewOrchestrator({ url: '', secret: '' })
      toast.success('Orchestrator added')
    }
  }

  // const handleAddApiKey = () => {
  //   if (newApiKey.exchange && newApiKey.key && newApiKey.secret) {
  //     setSettings({
  //       ...settings,
  //       apiKeys: [...settings.apiKeys, newApiKey],
  //     })
  //     setNewApiKey({ exchange: '', key: '', secret: '' })
  //     toast.success('API key added')
  //   }
  // }

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Settings
      </Typography>

      <Grid container spacing={3}>
        {/* GPU Settings */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              GPU Configuration
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
              <FormControl fullWidth>
                <InputLabel>Allocation Strategy</InputLabel>
                <Select
                  value={settings.gpu.allocationStrategy}
                  label="Allocation Strategy"
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      gpu: { ...settings.gpu, allocationStrategy: e.target.value },
                    })
                  }
                >
                  <MenuItem value="least_loaded">Least Loaded</MenuItem>
                  <MenuItem value="round_robin">Round Robin</MenuItem>
                  <MenuItem value="temperature">Temperature Based</MenuItem>
                </Select>
              </FormControl>

              <TextField
                label="Max Agents per GPU"
                type="number"
                fullWidth
                value={settings.gpu.maxAgentsPerGPU}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    gpu: { ...settings.gpu, maxAgentsPerGPU: parseInt(e.target.value) },
                  })
                }
              />

              <TextField
                label="Max VRAM Utilization (%)"
                type="number"
                fullWidth
                value={settings.gpu.maxVRAMUtilization}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    gpu: { ...settings.gpu, maxVRAMUtilization: parseInt(e.target.value) },
                  })
                }
              />

              <TextField
                label="Memory Reserve (MB)"
                type="number"
                fullWidth
                value={settings.gpu.memoryReserveMB}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    gpu: { ...settings.gpu, memoryReserveMB: parseInt(e.target.value) },
                  })
                }
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={settings.gpu.enableGPUDeployment}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        gpu: { ...settings.gpu, enableGPUDeployment: e.target.checked },
                      })
                    }
                  />
                }
                label="Enable GPU Deployment"
              />
            </Box>
          </Paper>
        </Grid>

        {/* System Settings */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              System Configuration
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
              <FormControl fullWidth>
                <InputLabel>Log Level</InputLabel>
                <Select
                  value={settings.system.logLevel}
                  label="Log Level"
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      system: { ...settings.system, logLevel: e.target.value },
                    })
                  }
                >
                  <MenuItem value="debug">Debug</MenuItem>
                  <MenuItem value="info">Info</MenuItem>
                  <MenuItem value="warning">Warning</MenuItem>
                  <MenuItem value="error">Error</MenuItem>
                </Select>
              </FormControl>

              <TextField
                label="Metrics Interval (seconds)"
                type="number"
                fullWidth
                value={settings.system.metricsInterval}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    system: { ...settings.system, metricsInterval: parseInt(e.target.value) },
                  })
                }
              />

              <TextField
                label="Max Log Size (MB)"
                type="number"
                fullWidth
                value={settings.system.maxLogSize}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    system: { ...settings.system, maxLogSize: parseInt(e.target.value) },
                  })
                }
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={settings.system.enableMonitoring}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        system: { ...settings.system, enableMonitoring: e.target.checked },
                      })
                    }
                  />
                }
                label="Enable Monitoring"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={settings.system.enableWebSockets}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        system: { ...settings.system, enableWebSockets: e.target.checked },
                      })
                    }
                  />
                }
                label="Enable WebSockets"
              />
            </Box>
          </Paper>
        </Grid>

        {/* Trading Settings */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Trading Configuration
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.trading.enableDualMode}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        trading: { ...settings.trading, enableDualMode: e.target.checked },
                      })
                    }
                  />
                }
                label="Enable Dual Mode Trading"
              />

              <FormControl fullWidth>
                <InputLabel>Default Trading Mode</InputLabel>
                <Select
                  value={settings.trading.defaultMode}
                  label="Default Trading Mode"
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      trading: { ...settings.trading, defaultMode: e.target.value },
                    })
                  }
                >
                  <MenuItem value="comparison">Comparison</MenuItem>
                  <MenuItem value="hybrid">Hybrid</MenuItem>
                  <MenuItem value="shadow">Shadow</MenuItem>
                  <MenuItem value="real_only">Real Only</MenuItem>
                  <MenuItem value="simulated_only">Simulated Only</MenuItem>
                </Select>
              </FormControl>

              <TextField
                label="Max Order Size (USD)"
                type="number"
                fullWidth
                value={settings.trading.maxOrderSize}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    trading: { ...settings.trading, maxOrderSize: parseInt(e.target.value) },
                  })
                }
              />

              <TextField
                label="Stop Loss (%)"
                type="number"
                fullWidth
                value={settings.trading.stopLossPercentage}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    trading: { ...settings.trading, stopLossPercentage: parseInt(e.target.value) },
                  })
                }
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={settings.trading.enableRiskLimits}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        trading: { ...settings.trading, enableRiskLimits: e.target.checked },
                      })
                    }
                  />
                }
                label="Enable Risk Limits"
              />
            </Box>
          </Paper>
        </Grid>

        {/* Orchestrator Management */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              GPU Orchestrators
            </Typography>
            
            <Alert severity="info" sx={{ mb: 2 }}>
              Add additional GPU orchestrator nodes to scale your swarm
            </Alert>

            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <TextField
                label="Orchestrator URL"
                size="small"
                fullWidth
                value={newOrchestrator.url}
                onChange={(e) =>
                  setNewOrchestrator({ ...newOrchestrator, url: e.target.value })
                }
                placeholder="https://gpu-node-2.example.com:9995"
              />
              <TextField
                label="Secret"
                size="small"
                type="password"
                fullWidth
                value={newOrchestrator.secret}
                onChange={(e) =>
                  setNewOrchestrator({ ...newOrchestrator, secret: e.target.value })
                }
              />
              <IconButton color="primary" onClick={handleAddOrchestrator}>
                <AddIcon />
              </IconButton>
            </Box>

            <List>
              {settings.orchestrators.map((orch: any, index) => (
                <ListItem key={index}>
                  <ListItemText
                    primary={orch.url}
                    secondary="Active"
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={() => {
                        setSettings({
                          ...settings,
                          orchestrators: settings.orchestrators.filter((_, i) => i !== index),
                        })
                      }}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>

        {/* Save Button */}
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
            <Button variant="outlined">
              Reset to Defaults
            </Button>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSaveSettings}
            >
              Save Settings
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Settings