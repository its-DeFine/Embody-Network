#!/bin/bash
# Multi-Host Deployment Script for Distributed Container System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env.multi-host"

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}🚀 Multi-Host Deployment Script${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_requirements() {
    print_info "Checking requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is required but not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is required but not installed"
        exit 1
    fi
    
    # Check environment file
    if [ ! -f "$ENV_FILE" ]; then
        print_warning "Environment file not found: $ENV_FILE"
        print_info "Creating from example..."
        cp "$PROJECT_DIR/.env.multi-host.example" "$ENV_FILE"
        print_warning "Please edit $ENV_FILE with your network configuration"
        exit 1
    fi
    
    print_success "Requirements check passed"
}

build_images() {
    print_info "Building Docker images..."
    
    cd "$PROJECT_DIR"
    
    # Build main application image
    print_info "Building main application image..."
    docker build -t autogen-platform:latest -f Dockerfile .
    
    # Build agent image
    print_info "Building agent container image..."
    docker build -t autogen-agent:latest -f Dockerfile.agent .
    
    print_success "Images built successfully"
}

deploy_method_1_external_ip() {
    print_info "Deploying using Method 1: External IP Configuration"
    
    cd "$PROJECT_DIR"
    
    # Source environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    print_info "Deployment instructions:"
    echo
    echo "1. Deploy Redis and Central Manager on main control machine:"
    echo "   docker-compose -f docker-compose.multi-host.yml up -d redis central-manager"
    echo
    echo "2. On each agent machine, create agent-specific compose file and deploy:"
    echo "   # Agent Machine 1 (${AGENT_1_IP:-10.0.1.201}):"
    echo "   docker-compose -f docker-compose.agent-node-1.yml up -d"
    echo
    echo "   # Agent Machine 2 (${AGENT_2_IP:-10.0.1.202}):"
    echo "   docker-compose -f docker-compose.agent-node-2.yml up -d"
    echo
    echo "3. Monitor deployment:"
    echo "   docker logs -f autogen-central-manager"
    echo "   curl http://${CENTRAL_MANAGER_IP:-10.0.1.200}:8000/api/v1/cluster/status"
    echo
}

deploy_method_2_swarm() {
    print_info "Deploying using Method 2: Docker Swarm"
    
    cd "$PROJECT_DIR"
    
    print_info "Docker Swarm deployment instructions:"
    echo
    echo "1. Initialize Swarm on manager node:"
    echo "   docker swarm init --advertise-addr <MANAGER_IP>"
    echo
    echo "2. Join worker nodes to swarm:"
    echo "   # Run this on each worker machine:"
    echo "   docker swarm join --token <TOKEN> <MANAGER_IP>:2377"
    echo
    echo "3. Label nodes for placement:"
    echo "   docker node update --label-add role=redis <REDIS_NODE>"
    echo "   docker node update --label-add agent-type=trading <TRADING_NODE>"
    echo "   docker node update --label-add agent-type=analysis <ANALYSIS_NODE>"
    echo
    echo "4. Deploy stack:"
    echo "   docker stack deploy -c docker-compose.swarm.yml autogen"
    echo
    echo "5. Monitor deployment:"
    echo "   docker stack services autogen"
    echo "   docker service logs autogen_central-manager"
    echo
}

create_agent_compose_files() {
    print_info "Creating individual agent compose files..."
    
    # Source environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    # Agent Node 1
    cat > "$PROJECT_DIR/docker-compose.agent-node-1.yml" << EOF
version: '3.8'

services:
  agent-container-1:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: autogen-agent-01
    environment:
      - AGENT_ID=agent-container-01
      - AGENT_TYPE=trading
      - AGENT_PORT=8001
      - REDIS_URL=redis://${REDIS_HOST}:6379
      - CENTRAL_MANAGER_URL=http://${CENTRAL_MANAGER_IP}:8000
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - CONTAINER_NAME=trading-node-01
      - EXTERNAL_IP=${AGENT_1_IP}
      - AGENT_CONFIG={"capabilities":["trading","market_analysis"],"max_agents":5,"external_endpoint":"http://${AGENT_1_IP}:8001"}
      - DISCOVERY_ENABLED=true
      - AUTO_REGISTER=true
      - HEARTBEAT_INTERVAL=30
    ports:
      - "8001:8001"
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  default:
    name: autogen-agent-1
EOF

    # Agent Node 2
    cat > "$PROJECT_DIR/docker-compose.agent-node-2.yml" << EOF
version: '3.8'

services:
  agent-container-2:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: autogen-agent-02
    environment:
      - AGENT_ID=agent-container-02
      - AGENT_TYPE=analysis
      - AGENT_PORT=8001
      - REDIS_URL=redis://${REDIS_HOST}:6379
      - CENTRAL_MANAGER_URL=http://${CENTRAL_MANAGER_IP}:8000
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - CONTAINER_NAME=analysis-node-01
      - EXTERNAL_IP=${AGENT_2_IP}
      - AGENT_CONFIG={"capabilities":["analysis","gpu_compute"],"max_agents":3,"external_endpoint":"http://${AGENT_2_IP}:8001"}
      - DISCOVERY_ENABLED=true
      - AUTO_REGISTER=true
      - HEARTBEAT_INTERVAL=30
    ports:
      - "8001:8001"
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  default:
    name: autogen-agent-2
EOF

    # Agent Node 3
    cat > "$PROJECT_DIR/docker-compose.agent-node-3.yml" << EOF
version: '3.8'

services:
  agent-container-3:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: autogen-agent-03
    environment:
      - AGENT_ID=agent-container-03
      - AGENT_TYPE=risk
      - AGENT_PORT=8001
      - REDIS_URL=redis://${REDIS_HOST}:6379
      - CENTRAL_MANAGER_URL=http://${CENTRAL_MANAGER_IP}:8000
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - CONTAINER_NAME=risk-node-01
      - EXTERNAL_IP=${AGENT_3_IP}
      - AGENT_CONFIG={"capabilities":["risk_analysis","compliance"],"max_agents":2,"external_endpoint":"http://${AGENT_3_IP}:8001"}
      - DISCOVERY_ENABLED=true
      - AUTO_REGISTER=true
      - HEARTBEAT_INTERVAL=30
    ports:
      - "8001:8001"
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  default:
    name: autogen-agent-3
EOF

    print_success "Agent compose files created"
}

test_connectivity() {
    print_info "Testing network connectivity..."
    
    # Source environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    # Test Redis connectivity
    if command -v telnet &> /dev/null; then
        print_info "Testing Redis connectivity..."
        if timeout 5 telnet "${REDIS_HOST}" 6379 </dev/null; then
            print_success "Redis is accessible"
        else
            print_warning "Redis connectivity test failed"
        fi
    fi
    
    # Test Central Manager API
    if command -v curl &> /dev/null; then
        print_info "Testing Central Manager API..."
        if curl -s --connect-timeout 5 "http://${CENTRAL_MANAGER_IP}:8000/health" > /dev/null; then
            print_success "Central Manager API is accessible"
        else
            print_warning "Central Manager API connectivity test failed"
        fi
    fi
}

show_firewall_rules() {
    print_info "Required firewall rules:"
    echo
    echo "Ubuntu/Debian (ufw):"
    echo "  sudo ufw allow from 10.0.1.0/24 to any port 6379  # Redis"
    echo "  sudo ufw allow from 10.0.1.0/24 to any port 8000  # Central Manager"
    echo "  sudo ufw allow from 10.0.1.0/24 to any port 8001  # Agent Containers"
    echo
    echo "CentOS/RHEL (firewalld):"
    echo "  sudo firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"10.0.1.0/24\" port protocol=\"tcp\" port=\"6379\" accept'"
    echo "  sudo firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"10.0.1.0/24\" port protocol=\"tcp\" port=\"8000\" accept'"
    echo "  sudo firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"10.0.1.0/24\" port protocol=\"tcp\" port=\"8001\" accept'"
    echo "  sudo firewall-cmd --reload"
    echo
}

main() {
    print_header
    
    case "${1:-help}" in
        "check")
            check_requirements
            ;;
        "build")
            check_requirements
            build_images
            ;;
        "external-ip")
            check_requirements
            build_images
            create_agent_compose_files
            deploy_method_1_external_ip
            ;;
        "swarm")
            check_requirements
            build_images
            deploy_method_2_swarm
            ;;
        "test")
            test_connectivity
            ;;
        "firewall")
            show_firewall_rules
            ;;
        "help"|*)
            echo "Usage: $0 [command]"
            echo
            echo "Commands:"
            echo "  check        Check requirements and environment"
            echo "  build        Build Docker images"
            echo "  external-ip  Deploy using external IP method"
            echo "  swarm        Deploy using Docker Swarm method"
            echo "  test         Test network connectivity"
            echo "  firewall     Show required firewall rules"
            echo "  help         Show this help message"
            echo
            echo "Environment:"
            echo "  Edit .env.multi-host with your network configuration"
            echo
            ;;
    esac
}

# Run main function with all arguments
main "$@"