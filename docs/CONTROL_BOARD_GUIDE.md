# Control Board User Guide

The Control Board is a React-based web interface for managing and monitoring the AutoGen platform.

## Accessing the Control Board

Open your browser and navigate to:
```
http://localhost:3001
```

## Features

### 1. Dashboard
The main dashboard provides an overview of:
- Active agents count
- Running tasks
- System health status
- Recent activity

### 2. Agents Management
Navigate to the Agents tab to:
- View all deployed agents
- Create new agents
- Monitor agent status
- Configure agent settings
- Delete agents

#### Creating an Agent
1. Click "New Agent" button
2. Fill in the form:
   - Agent Name
   - Agent Type (Trading, Analysis, Risk Management, Portfolio)
   - Configuration parameters
   - AutoGen settings
3. Click "Deploy"

### 3. GPU Orchestrator Management
The GPU Orchestrators tab allows you to:
- View available GPU resources
- Monitor GPU utilization
- Deploy GPU-enabled agents
- Manage GPU allocation

### 4. Monitoring
Real-time monitoring of:
- System metrics
- Agent performance
- Task execution status
- Resource utilization

### 5. Settings
Configure platform settings:
- API endpoints
- Authentication
- Resource limits
- Notification preferences

## Navigation

The left sidebar provides quick access to:
- 🏠 Dashboard
- 🤖 Agents
- 🎮 GPU Orchestrators
- 📊 Monitoring
- ⚙️ Settings

## Agent States

Agents can be in the following states:
- 🟢 **Running**: Agent is active and processing tasks
- 🟡 **Pending**: Agent is being deployed
- 🔵 **Idle**: Agent is running but not processing tasks
- 🔴 **Error**: Agent encountered an error
- ⚫ **Stopped**: Agent is intentionally stopped

## Task Management

### Creating Tasks
1. Select an agent
2. Click "New Task"
3. Choose task type
4. Configure task parameters
5. Submit task

### Monitoring Tasks
Tasks display:
- Task ID
- Status (Pending, Running, Completed, Failed)
- Execution time
- Results summary

## GPU Features

### GPU Agent Deployment
1. Navigate to GPU Orchestrators
2. Select available GPU
3. Click "Deploy Agent"
4. Choose GPU-optimized agent type
5. Configure GPU requirements

### GPU Monitoring
View real-time:
- GPU utilization percentage
- Memory usage
- Temperature
- Running processes

## Best Practices

1. **Regular Monitoring**: Check the dashboard daily for system health
2. **Resource Management**: Monitor resource usage to optimize performance
3. **Agent Lifecycle**: Properly stop agents when not in use
4. **Task Cleanup**: Archive completed tasks regularly
5. **GPU Efficiency**: Use GPU resources only for compute-intensive tasks

## Troubleshooting

### Common Issues

1. **Cannot Access Control Board**
   - Verify Docker containers are running: `docker ps`
   - Check if port 3001 is available
   - Clear browser cache

2. **Agent Creation Fails**
   - Check Docker logs: `docker logs control-board`
   - Verify agent manager is running
   - Check resource availability

3. **No GPU Resources Shown**
   - Ensure GPU orchestrator is running
   - Verify GPU drivers are installed
   - Check orchestrator configuration

### Debug Mode

Enable debug mode for detailed logging:
1. Go to Settings
2. Enable "Debug Mode"
3. Check browser console for detailed logs

## Keyboard Shortcuts

- `Ctrl/Cmd + K`: Quick search
- `Ctrl/Cmd + N`: New agent
- `Ctrl/Cmd + R`: Refresh data
- `Esc`: Close modals

## API Integration

The Control Board communicates with:
- API Gateway (port 8000)
- WebSocket for real-time updates
- OpenBB Adapter (port 8003)

## Security

- All actions require authentication
- Session timeout after 30 minutes of inactivity
- Admin actions are logged for audit

## Mobile Access

The Control Board is responsive and can be accessed on mobile devices with limited functionality:
- View dashboard
- Monitor agents
- Check task status

## Updates

The Control Board auto-refreshes data every:
- Dashboard: 5 seconds
- Agents list: 10 seconds
- GPU status: 3 seconds
- Tasks: Real-time via WebSocket

## Support

For issues or feature requests:
1. Check the troubleshooting section
2. Review Docker logs
3. Submit an issue on GitHub