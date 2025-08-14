# VTuber Autonomy Platform
*Enhanced Embodied Multi-Agent System*

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/its-DeFine/agent-net/releases)
[![License](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)

## Overview
A comprehensive platform for managing virtual embodied agents (VTubers) with advanced AI capabilities, real-time streaming, and dynamic character management.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Redis 6.0+ (optional if using Docker Redis)
- 8GB RAM minimum

### Installation
```bash
# Clone the repository with submodules
git clone --recurse-submodules https://github.com/its-DeFine/agent-net.git
cd agent-net

# Initialize submodules if you already cloned without --recurse-submodules
git submodule update --init --recursive

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration
```

### Launch Options

#### Option 1: Central Manager with Dashboard
```bash
# Launch manager with integrated dashboard UI
docker-compose -f docker-compose.manager.yml up -d

# Access Dashboard at: http://localhost:8081
# API available at: http://localhost:8010
```

#### Option 2: Full VTuber Autonomy System
```bash
# Launch all VTuber services (orchestrator)
cd autonomy
docker-compose up -d

# Services:
# - NeuroSync: http://localhost:5001
# - AutoGen: http://localhost:8200
# - RTMP Stream: rtmp://localhost:1935/live
```

## Project Structure
```
operation/
├── app/                      # Central manager application
│   ├── api/                  # API endpoints
│   └── core/                 # Core business logic
├── autonomy/                 # VTuber autonomy system
│   ├── docker-compose.yml    # Full VTuber services
│   └── docker-vtuber/        # VTuber implementation
├── docker/                   # Docker configurations
│   └── ui/                   # Dashboard UI files
├── scripts/                  # Utility scripts
│   └── utilities/            # Agent management tools
├── docs/                     # Documentation
└── docker-compose.manager.yml # Manager with UI
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
- ✅ Automatic semantic versioning with CI/CD
- ✅ Version tracking and release automation

## Documentation
- [Production Setup Guide](docs/PRODUCTION_SETUP.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Documentation](docs/API_REFERENCE.md)
- [Changelog](CHANGELOG.md)

## Security Notes
- Never commit `.env` files with real credentials
- Use strong passwords (32+ characters)
- Rotate JWT secrets regularly
- Configure firewall rules for production

## License
Proprietary - All rights reserved

## Version Information

The platform uses semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking API changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

Current version is available at `/api/v1/version` endpoint or in the dashboard.

## Support
For issues or questions, please refer to the documentation or contact the development team.