#!/bin/bash

echo "=== AutoGen Platform Live Demo ==="
echo

# Check running services
echo "1. Checking running services..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "NAME|control-board|api-gateway|rabbitmq|redis|trading"
echo

# Test API health
echo "2. Testing API Gateway health..."
curl -s http://localhost:8000/health | jq .
echo

# Check RabbitMQ
echo "3. RabbitMQ Management Interface:"
echo "   URL: http://localhost:15672"
echo "   Username: guest"
echo "   Password: guest"
echo

# Check control board
echo "4. Control Board UI:"
echo "   URL: http://localhost:3001"
echo "   Username: admin"
echo "   Password: admin123"
echo

# Check Redis
echo "5. Testing Redis connection..."
docker exec redis redis-cli ping
echo

# Show API documentation
echo "6. API Documentation:"
echo "   Swagger UI: http://localhost:8000/docs"
echo "   ReDoc: http://localhost:8000/redoc"
echo

# Show available endpoints
echo "7. Available API endpoints:"
curl -s http://localhost:8000/openapi.json | jq '.paths | keys' 2>/dev/null || echo "Failed to fetch endpoints"
echo

echo "=== Demo Complete ==="
echo
echo "To stop all services: docker-compose down"
echo "To view logs: docker-compose logs -f [service-name]"
echo
echo "Note: Some features require additional configuration:"
echo "- Agent deployment requires Docker socket access"
echo "- GPU features require GPU orchestrator stack"
echo "- Trading features require exchange API keys"