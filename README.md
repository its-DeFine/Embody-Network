
# Agent-Net: GPU Check Pipeline with BYOC Capability

This is an implementation of a BYOC (Bring Your Own Container) pipeline that provides GPU check functionality to callers. It deploys an Ollama container and includes a custom capability for GPU monitoring that returns GPU state and model info  from ollama. 

## Overview

The pipeline enables:
- Deployment of custom Ollama containers with GPU support
- Real-time GPU health checks and vRAM monitoring
- Querying of deployed models on the Ollama server

### Prerequisites

- docker installed and running

- access to an a GPU supported by Ollama.

### Instructions for Orchestrators

To launch the container with GPU check capability:

1. **Navigate to Project Root**
   ```bash
   cd /path/to/agent-net
   ```

2. **Build the Container**
   ```bash
   docker compose build --no-cache
   ```

3. **Launch the Services**
   ```bash
   docker compose up
   ```

4. **Wait for Model Download**
   The Ollama model will be automatically downloaded on first launch. Monitor the logs to ensure the model is ready before accepting requests.

### GPU Check Capability

The custom GPU check capability provides:

- **vRAM Usage Monitoring**: Real-time tracking of GPU memory utilization
- **Model Status**: Lists all currently deployed models on the Ollama server
- **Resource Availability**: Checks GPU availability for new model deployments
- **Safeguard Functionality**: Prevents overloading by monitoring resource constraints

This capability queries the Ollama server and returns structured data about GPU state

  
### Future Integration

This GPU check pipeline serves as a safeguard component that will be integrated into larger agent-net app we develop seperately. 