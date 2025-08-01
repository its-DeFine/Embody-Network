# Frontend Guide - AutoGen Control Board

The AutoGen Control Board provides a web-based interface for managing AI agents, teams, and tasks.

## 🔐 Authentication

### Login
1. Navigate to http://localhost:8000
2. Enter credentials:
   - Username: `admin`
   - Password: Your `ADMIN_PASSWORD` from `.env`

### Session Management
- Sessions expire after 24 hours
- Token stored in browser localStorage
- Automatic redirect to login on expiration

## 📊 Dashboard

The dashboard provides real-time system overview:

### Metrics Cards
- **Total Agents**: All registered agents
- **Running Agents**: Currently active agents
- **Teams**: Agent team count
- **Active Tasks**: Tasks being processed

### Recent Tasks
- Shows last 5 tasks with status
- Click for detailed view

### System Health
- API status indicator
- Redis connection status
- Task processing status

## 🤖 Agents Management

### Creating Agents
1. Click "New Agent" button
2. Enter agent details:
   - **Name**: Descriptive agent name
   - **Type**: Select from:
     - `trading` - Financial trading agent
     - `analysis` - Data analysis agent
     - `risk` - Risk assessment agent
     - `portfolio` - Portfolio management agent
3. Click "Create"

### Agent Actions
- **Start**: Activate a stopped agent
- **Stop**: Deactivate a running agent
- **Delete**: Remove agent permanently

### Agent States
- 🟢 **Running**: Agent is active
- ⚪ **Stopped**: Agent is inactive
- 🔴 **Error**: Agent encountered issues

## 👥 Teams Management

### Creating Teams
1. Click "New Team" button
2. Fill team details:
   - **Name**: Team identifier
   - **Description**: Team purpose
   - **Agents**: Select multiple agents
3. Click "Create"

### Coordinating Teams
1. Click send icon on team card
2. Enter task objective
3. Click "Send Task"

The team will coordinate agents to complete the objective.

## 📋 Tasks Monitoring

### Task List Features
- **Auto-refresh**: Updates every 5 seconds
- **Status filtering**: Sort by status
- **Details view**: Click info icon

### Task States
- 🟡 **Pending**: Queued for processing
- 🔵 **Running**: Currently executing
- 🟢 **Completed**: Successfully finished
- 🔴 **Failed**: Encountered error
- ⚪ **Cancelled**: Manually stopped

### Task Actions
- **View Details**: See full task information
- **Cancel**: Stop running/pending tasks

### Task Details
- Task ID and type
- Full description
- Creation/completion timestamps
- Result data (JSON format)
- Error messages (if failed)

## 🎨 UI Features

### Navigation
- Sidebar menu for quick access
- Current page highlighting
- Logout button in header

### Responsive Design
- Works on desktop and tablet
- Mobile-optimized layouts
- Touch-friendly controls

### Real-time Updates
- Live task status updates
- Auto-refreshing dashboards
- WebSocket notifications (planned)

## ⚡ Performance Tips

1. **Pagination**: Large lists are paginated
2. **Caching**: Data cached for 30 seconds
3. **Batch Operations**: Group similar actions

## 🐛 Troubleshooting

### Common Issues

**Can't see agents/teams/tasks**
- Check API connection
- Verify authentication
- Refresh the page

**Actions not working**
- Check browser console for errors
- Verify backend is running
- Check Redis connection

**UI not updating**
- Hard refresh (Ctrl+F5)
- Clear browser cache
- Check WebSocket connection

## 🔧 Developer Tools

### Browser Console
```javascript
// Check auth token
localStorage.getItem('token')

// Force data refresh
window.location.reload()
```

### API Testing
Use browser DevTools Network tab to:
- Monitor API calls
- Check response data
- Debug errors

## 📱 Keyboard Shortcuts

- `Ctrl + R`: Refresh current view
- `Esc`: Close dialogs
- `Enter`: Submit forms

## 🎯 Best Practices

1. **Regular Monitoring**: Check dashboard daily
2. **Task Cleanup**: Cancel stuck tasks
3. **Agent Management**: Stop unused agents
4. **Team Organization**: Group related agents

## 🔮 Upcoming Features

- Real-time notifications
- Task scheduling
- Agent performance metrics
- Advanced filtering
- Export capabilities