# Livepeer BYOC Payment System with Enhanced Orchestrator Management

## Overview
This PR implements a comprehensive Bring Your Own Container (BYOC) payment distribution system integrated with Livepeer's orchestrator network. The system enables sophisticated payment logic based on service uptime, with automatic orchestrator discovery, monitoring, and progressive delay/punishment mechanisms.

## Key Features

### 1. Enhanced Payment Distributor with BYOC Integration
- **BYOC Job Submission**: Sends monitoring jobs through Livepeer Gateway at `/process/request/agent-net`
- **Uptime-Based Payment Tiers**:
  - EXCELLENT (>95% uptime): 1.2x payment multiplier, no delay
  - GOOD (80-95%): Standard payment (1.0x)
  - WARNING (60-80%): 0.7x payment, 30s delay
  - POOR (40-60%): 0.3x payment, 120s delay  
  - CRITICAL (<40%): 0.1x payment, 300s delay
  - OFFLINE: No payment, 600s delay
- **Progressive Punishment**: Exponential backoff for consecutive failures
- **USD to Wei Conversion**: Accurate ETH/USD rate conversion (configurable, default $2000/ETH)

### 2. Multi-Orchestrator Management System
- **Automatic Discovery**: Finds and registers orchestrators with connectivity proofs
- **Connectivity Monitoring**: Real-time uptime tracking across all services
- **Payment Processing**: Distributed payments based on performance metrics
- **Container Integration**: Seamless communication between manager, worker, gateway, and orchestrator

### 3. Service Monitoring & Health Checks
- **Comprehensive Health Metrics**:
  - Worker service uptime
  - Orchestrator availability  
  - Gateway connectivity
  - Overall system health
- **Service Discovery**: Automatic detection of VTuber services (NeuroSync, AutoGen, SCB)
- **Real-time Monitoring**: Continuous health checks with configurable intervals

### 4. Testing & Validation Utilities
- **Continuous BYOC Tester**: Stress testing with configurable rates
- **Multi-Orchestrator Tester**: Load distribution across multiple orchestrators
- **Payment Flow Visualizer**: Real-time payment tracking and visualization
- **Registration Scripts**: Automated orchestrator registration and updates

## Technical Implementation

### Architecture Components

```
┌──────────────────────────────────────────────────────────┐
│                   Central Manager                          │
│  - Orchestrator Registry                                  │
│  - Payment Processing API                                 │
│  - Authentication & Authorization                         │
└──────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Gateway    │   │ Orchestrator │   │   Worker     │
│              │◄──│   Monitor    │──►│              │
│ BYOC Request │   │              │   │ Service      │
│  Processing  │   │  Registration│   │ Monitoring   │
└──────────────┘   └──────────────┘   └──────────────┘
        │                                       │
        └───────────────────────────────────────┘
                    BYOC Job Flow
```

### Core Files Added/Modified

#### New Services (`/scripts/services/`)
- `enhanced_payment_distributor.py` - BYOC-aware payment distribution with sophisticated logic
- `payment_distributor.py` - Base payment distribution implementation
- `stream_generator.py` - Real-time data streaming for monitoring

#### Testing Utilities (`/scripts/`)
- `continuous_byoc_test.py` - Automated BYOC job testing
- `multi_orchestrator_tester_with_pricing.py` - Price-aware orchestrator testing
- `list_orchestrators.py` - Orchestrator discovery and listing
- `register_real_orchestrator.py` - Automated registration
- `send_byoc_calls.py` - Direct BYOC job submission
- `show_payment_flow.py` - Payment visualization
- `update_orchestrator_endpoint.py` - Endpoint management
- `verify_complete_flow.py` - End-to-end validation

#### API Enhancements (`/app/`)
- `api/livepeer.py` - Livepeer integration endpoints
- `core/orchestration/connectivity_monitor.py` - Real-time connectivity tracking
- `main.py` - Enhanced API routes for orchestrator management

#### Infrastructure (`/`)
- `docker-compose.manager.yml` - Manager cluster configuration
- `Dockerfile` - Custom worker container
- `server/` - BYOC worker implementation

### Configuration & Environment

```yaml
# Payment Configuration
PAYMENT_INTERVAL_SECONDS: 60
BASE_PAYMENT_USD: 10.0
ETH_TO_USD: 2000.0
MAX_CONSECUTIVE_FAILURES: 5
PUNISHMENT_MULTIPLIER: 2.0

# Livepeer Configuration  
CAPABILITY_NAME: agent-net
CAPABILITY_PRICE_PER_UNIT: 0  # Set to 0 for testing
ORCHESTRATOR_SECRET: orch-secret
PROOF_INTERVAL: 60
HEARTBEAT_TIMEOUT: 30
```

## Testing & Validation

### Unit Tests
- Payment calculation logic
- USD to Wei conversion
- Uptime status determination
- BYOC job creation

### Integration Tests
- End-to-end payment flow
- Orchestrator registration
- BYOC job processing
- Service health monitoring

### Performance Testing
- Concurrent orchestrator handling
- High-frequency BYOC job submission
- Payment processing throughput
- Network resilience

## Usage Examples

### Start the System
```bash
# Start manager cluster
docker-compose -f docker-compose.manager.yml up -d

# Start autonomy cluster
cd autonomy && docker-compose up -d
```

### Register Orchestrators
```bash
# Automatic registration
python scripts/register_real_orchestrator.py

# Manual registration with monitoring
python scripts/list_orchestrators.py
```

### Monitor Payment Flow
```bash
# Real-time payment visualization
python scripts/show_payment_flow.py

# Continuous BYOC testing
python scripts/continuous_byoc_test.py --rate 10 --duration 3600
```

### Verify System Health
```bash
# Complete flow verification
python scripts/verify_complete_flow.py

# Check orchestrator status
curl http://localhost:8010/api/v1/livepeer/orchestrators
```

## Benefits

1. **Automated Payment Distribution**: No manual intervention required
2. **Performance-Based Incentives**: Rewards reliable orchestrators
3. **Fault Tolerance**: Handles failures gracefully with progressive delays
4. **Scalability**: Supports unlimited orchestrators
5. **Real-time Monitoring**: Instant visibility into system health
6. **Cost Efficiency**: Optimizes payments based on actual service delivery

## Security Considerations

- JWT authentication for API access
- Secure orchestrator registration with proofs
- Rate limiting on BYOC job submission
- Encrypted communication between services
- Audit logging for all payments

## Future Enhancements

- [ ] Dynamic pricing based on network congestion
- [ ] Machine learning for uptime prediction
- [ ] Multi-chain payment support
- [ ] Advanced analytics dashboard
- [ ] Automated orchestrator onboarding
- [ ] SLA management system

## Breaking Changes

None - fully backward compatible with existing Livepeer infrastructure.

## Migration Guide

For existing deployments:
1. Update environment variables with payment configuration
2. Deploy enhanced payment distributor
3. Register existing orchestrators
4. Monitor initial payment cycles
5. Adjust thresholds based on network performance

## Documentation

- [BYOC Payment System Architecture](docs/byoc-payment-system.md)
- [API Documentation](docs/api-reference.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

## Contributors

- System architecture and BYOC integration
- Payment logic implementation
- Testing utilities and monitoring
- Documentation and examples

## License

Same as parent repository