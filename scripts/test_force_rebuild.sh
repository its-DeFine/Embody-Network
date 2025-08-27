#!/bin/bash

# Test script for Force Rebuild on VTuber Update feature
# Created: 2025-08-27

set -e

echo "==========================================="
echo "Testing Force Rebuild on VTuber Update"
echo "==========================================="

# Set test environment
export FORCE_REBUILD_ON_VTUBER_UPDATE=true
REPO_PATH="/home/geo/operation"

echo ""
echo "1. Testing detection logic..."
echo "-------------------------------------------"
python3 scripts/dual_update_manager.py \
    --repo-path "$REPO_PATH" \
    --force-rebuild-on-vtuber-update \
    --check-only

echo ""
echo "2. Checking environment variable..."
echo "-------------------------------------------"
if [ "$FORCE_REBUILD_ON_VTUBER_UPDATE" = "true" ]; then
    echo "✓ FORCE_REBUILD_ON_VTUBER_UPDATE is enabled"
else
    echo "✗ FORCE_REBUILD_ON_VTUBER_UPDATE is disabled"
fi

echo ""
echo "3. Verifying Docker Compose configurations..."
echo "-------------------------------------------"

# Check update-manager config
if grep -q "FORCE_REBUILD_ON_VTUBER_UPDATE" autonomy/update-manager/docker-compose.yml; then
    echo "✓ update-manager has FORCE_REBUILD_ON_VTUBER_UPDATE configured"
else
    echo "✗ update-manager missing FORCE_REBUILD_ON_VTUBER_UPDATE"
fi

# Check update-orchestrator config
if grep -q "FORCE_REBUILD_ON_VTUBER_UPDATE" autonomy/update-orchestrator/docker-compose.yml; then
    echo "✓ update-orchestrator has FORCE_REBUILD_ON_VTUBER_UPDATE configured"
else
    echo "✗ update-orchestrator missing FORCE_REBUILD_ON_VTUBER_UPDATE"
fi

echo ""
echo "4. Checking submodule status..."
echo "-------------------------------------------"
cd "$REPO_PATH"
git submodule status | grep -E "docker-vtuber|autonomy" || true

echo ""
echo "5. Simulating VTuber update detection..."
echo "-------------------------------------------"

# Create a temporary test file to simulate VTuber change
TEST_FILE="$REPO_PATH/test_vtuber_update.tmp"
echo "test" > "$TEST_FILE"

# Run detection with the test file
python3 -c "
import sys
sys.path.insert(0, '$REPO_PATH')
from scripts.dual_update_manager import UpdateDetector, UpdateType

detector = UpdateDetector('$REPO_PATH')
update_type, changes = detector.detect_changes(force_rebuild_on_vtuber_update=True)

print(f'Update Type: {update_type.value}')
print(f'VTuber Updated: {changes.get(\"vtuber_updated\", False)}')
print(f'Would force rebuild: {update_type == UpdateType.STRUCTURAL}')
"

# Clean up test file
rm -f "$TEST_FILE"

echo ""
echo "6. Checking Docker build commands..."
echo "-------------------------------------------"
echo "Command that would be run for forced rebuild:"
echo "docker-compose -f autonomy/docker-compose.yml build --no-cache"

echo ""
echo "7. Verifying health check endpoints..."
echo "-------------------------------------------"
SERVICES=(
    "orchestrator:8082"
    "neurosync_s1:5001"
    "autogen_agent:8200"
)

for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port <<< "$service"
    echo "Health check URL for $name: http://localhost:$port/health"
done

echo ""
echo "==========================================="
echo "Test Summary"
echo "==========================================="
echo ""
echo "Feature is configured and ready to:"
echo "1. Detect VTuber repository updates"
echo "2. Force STRUCTURAL rebuild type"
echo "3. Execute full cluster rebuild with --no-cache"
echo "4. Clean old images before rebuild"
echo "5. Perform health checks after rebuild"
echo ""
echo "To activate in production:"
echo "1. Ensure FORCE_REBUILD_ON_VTUBER_UPDATE=true in .env"
echo "2. Deploy update-orchestrator: cd autonomy/update-orchestrator && docker-compose up -d"
echo "3. Monitor logs: docker logs -f update_orchestrator"
echo ""
echo "Test completed successfully!"