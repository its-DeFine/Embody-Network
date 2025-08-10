# VTuber Autonomy Platform
*Enhanced Embodied Multi-Agent System*

## Overview
A comprehensive platform for managing virtual embodied agents (VTubers) with advanced AI capabilities, real-time streaming, and dynamic character management.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Redis 6.0+
- 8GB RAM minimum

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd operation

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration

# Start Redis
redis-server

# Launch Central Manager
docker-compose -f docker-compose.manager.debug.yml up -d

# Launch VTuber Services
cd autonomy
docker-compose -f docker-compose.yml up -d

# Access Dashboard
python3 -m http.server 8081
# Open http://localhost:8081/vtuber-dashboard-v3.html
```

## Architecture

### System Components
- **Central Manager**: Authentication, agent registry, command routing
- **NeuroSync S1**: Avatar control and speech synthesis
- **AutoGen Multi-Agent**: Cognitive processing and decision making
- **SCB Gateway**: Message routing and event handling
- **RTMP Streaming**: Audio/video streaming server

### Agent Types
1. **Orchestrators**: Workflow coordination systems
2. **Character Agents**: AI personalities (Luna, Diana, Sophia)
3. **Infrastructure**: Core service containers

## Features
- ✅ Dynamic agent creation and management
- ✅ Real-time character switching
- ✅ Text-to-speech with streaming output
- ✅ Web-based management dashboard
- ✅ JWT-based authentication
- ✅ Redis-backed state management
- ✅ Docker containerization
- ✅ RTMP/HLS streaming support

## Documentation
- [Production Setup Guide](docs/PRODUCTION_SETUP.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Documentation](docs/API.md)

## Key Files
- `agent_manager_v2.py` - Advanced agent management with categorization
- `vtuber-dashboard-v3.html` - Web management interface
- `app/api/embodiment.py` - Core API endpoints
- `docker-compose.yml` - Service orchestration

## Security Notes
- Never commit `.env` files with real credentials
- Use strong passwords (32+ characters)
- Rotate JWT secrets regularly
- Configure firewall rules for production

## License
Proprietary - All rights reserved

## Support
For issues or questions, please refer to the documentation or contact the development team.